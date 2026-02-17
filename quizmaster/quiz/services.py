from datetime import datetime
import random
import string
from .constants import QuizStatus, PARTICIPANTS_USER_ID, SESSION_NOT_FOUND, UNAUTHORIZED
from quizmaster.mongo_client import quizzes_collection, sessions_collection, submissions_collection
from bson import ObjectId

class QuizService:

    
    # private methods
    
    @staticmethod
    def _build_response_dto(session: dict, quiz: dict) -> dict:
        raw_participants = session.get("participants", [])
        
        # Normalize participants: handle both old (string) and new (object) formats
        participants = []
        for p in raw_participants:
            if isinstance(p, dict):                    
                participants.append(p)
            else:
                # Legacy format: participant is just a user_id string
                participants.append({
                    "user_id": str(p),
                    "name": "Unknown",
                    "score": 0
                })
        
        return {
            "session_id": str(session["_id"]),
            "join_code": session.get("join_code"),
            "quiz_id": str(quiz["_id"]),
            "title": quiz.get("title"),
            "description": quiz.get("description"),
            "topic": quiz.get("topic"),
            "difficulty": quiz.get("difficulty"),
            "status": session.get("status"),
            "host_id": session.get("host_id"),
            "created_at": session.get("created_at"),
            "duration": quiz.get("duration"),
            "pointsPerCorrect": quiz.get("pointsPerCorrect"),
            "start_time": quiz.get("start_time"),
            "max_participants": quiz.get("max_participants"),
            "participants": participants, 
            "participant_count": len(participants),
            "question_count": len(quiz.get("questions", []))
        }

    @staticmethod
    def _generate_join_code(length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choices(alphabet, k=length))

    @staticmethod
    def _get_unique_join_code() -> str:
        for _ in range(10):
            code = QuizService._generate_join_code()
            exists = sessions_collection.find_one({"join_code": code})
            if not exists:
                return code
        raise ValueError("Unable to generate unique join code.")

    @staticmethod
    def _merge_sessions_with_quizzes(sessions: list) -> list:
        if not sessions:
            return []
        
        quiz_ids = [ObjectId(s['quiz_id']) for s in sessions]
        quizzes = list(quizzes_collection.find({"_id": {"$in": quiz_ids}}))
        quiz_map = {str(q["_id"]): q for q in quizzes}

        results = []
        for session in sessions:
            q_id = session.get("quiz_id")
            quiz = quiz_map.get(q_id)
            if quiz:
                results.append(QuizService._build_response_dto(session, quiz))
        return results

    # pubilc methods
    
    @staticmethod
    def get_session_by_quiz_id(quiz_id: str) -> dict:
        session = sessions_collection.find_one({"quiz_id": quiz_id})
        return session
    
    @staticmethod
    def create_quiz(user_id: str, quiz_data: dict) -> dict:
        quiz_data['created_by'] = user_id
        quiz_data['created_at'] = datetime.now()
        quiz_result = quizzes_collection.insert_one(quiz_data)
        quiz_data['_id'] = quiz_result.inserted_id

        session_data = {
            'quiz_id': str(quiz_result.inserted_id),
            'host_id': user_id,
            'status': QuizStatus.WAITING.value,
            'participants': [], # Will store objects
            'created_at': datetime.now(),
            'join_code': QuizService._get_unique_join_code()
        }
        session_result = sessions_collection.insert_one(session_data)
        session_data['_id'] = session_result.inserted_id

        return QuizService._build_response_dto(session_data, quiz_data)


    @staticmethod
    def get_quiz_details(session_id: str) -> dict:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        
        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})
        return QuizService._build_response_dto(session, quiz)
     


    @staticmethod
    def get_hosted_sessions(user_id: str) -> list:
        sessions = list(sessions_collection.find({"host_id": user_id}))
        return QuizService._merge_sessions_with_quizzes(sessions)
    
    @staticmethod
    def get_enrolled_sessions(user_id: str) -> list:
        # Query inside the array of objects for the specific 'user_id' key
        sessions = list(sessions_collection.find({PARTICIPANTS_USER_ID: user_id}))
        return QuizService._merge_sessions_with_quizzes(sessions)

    @staticmethod
    def join_session(join_code: str, user_id: str, user_name: str) -> dict:
        """
        Adds user {user_id, name, score} to the participants list.
        """
        normalized_code = (join_code or "").strip().upper()
        if len(normalized_code) != 6:
            raise ValueError("Invalid join code.")

        session = sessions_collection.find_one({"join_code": normalized_code})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        if session["status"] != QuizStatus.WAITING.value:
            raise ValueError("Quiz is not open for joining.")

        participants = session.get("participants", [])
        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})

        # Check if user already exists
        existing = next((p for p in participants if p["user_id"] == user_id), None)

        if not existing:
            if len(participants) >= quiz.get("max_participants", 100):
                raise ValueError("Session is full.")
            
            # THE NEW OBJECT STRUCTURE
            new_participant = {
                "user_id": user_id,
                "name": user_name,
                "score": 0,
                "status": "lobby", # lobby -> active -> completed
                "quiz_start_time": None
            }
            
            sessions_collection.update_one(
                {"_id": ObjectId(session["_id"])},
                {"$push": {"participants": new_participant}}
            )
            # Update local list for response
            participants.append(new_participant)
            session["participants"] = participants

        return QuizService._build_response_dto(session, quiz)

    @staticmethod
    def start_quiz(session_id: str, host_id: str) -> dict:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        if session["host_id"] != host_id:
            raise PermissionError(UNAUTHORIZED)
        
        # update status to active only if it waiting
        if session["status"] != QuizStatus.WAITING.value:
            raise ValueError("Quiz has already been started or ended.")
            
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "active"}}
        )
        return {"session_id": session_id, "status": "active"}

    @staticmethod
    def start_quiz_for_participant(session_id: str, user_id: str,start_time) -> dict:

        """
        Sets the quiz_start_time for an individual participant when they start taking the quiz.
        Also updates their status to 'active'.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        
        # Check if quiz has been started by host
        if session["status"] != "active":
            raise ValueError("Quiz has not been started by the host yet.")
        
        # Check if user is enrolled
        participant = next(
            (p for p in session.get("participants", []) if p["user_id"] == user_id), 
            None
        )
        if not participant:
            raise ValueError("You are not enrolled in this session.")
        
        # Check if already started
        if participant.get("quiz_start_time") is not None:
            return {
                "session_id": session_id,
                "user_id": user_id,
                "quiz_start_time": participant["quiz_start_time"],
                "status": participant.get("status"),
                "message": "Quiz already started for this participant."
            }
         
        
        # Update participant's quiz_start_time and status to 'active'
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "participants.$[participant].quiz_start_time": start_time,
                    "participants.$[participant].status": "active"
                }
            },
            array_filters=[{"participant.user_id": user_id}]
        )
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "quiz_start_time": start_time,
            "status": "active"
        }

    @staticmethod # get all questions for participant with current question index
    def get_question_paper(session_id: str, user_id: str) -> dict:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)

        # Check enrollment inside the array of objects
        is_enrolled = any(p["user_id"] == user_id for p in session.get("participants", []))
        if not is_enrolled and session["host_id"] != user_id:
             raise PermissionError("You are not enrolled.")

        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})
        
        # Get participant's individual quiz_start_time
        participant = next(
            (p for p in session.get("participants", []) if p["user_id"] == user_id), 
            None
        )
        participant_start_time = participant.get("quiz_start_time") if participant else None
        
        # geting current question index from submissions
        attempted_questions = submissions_collection.find(
            {"session_id": session_id, "user_id": user_id},
            {"question_index": 1, "_id": 0} 
        )
        attempted_indices = {doc["question_index"] for doc in attempted_questions}
        current_question_index = len(attempted_indices)
        
        return {
            "questions": quiz.get("questions", []),
            "current_question_index": current_question_index,
            "start_time": participant_start_time
        }

    @staticmethod
    def submit_answer(user_id, session_id, question_index, selected_option):
        # 1. Fetch
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session: raise ValueError("Session not found")
        
        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})
        questions = quiz.get("questions", [])
        
        if question_index < 0 or question_index >= len(questions):
            raise ValueError("Invalid index.")

        # 2. Check Logic
        current_q = questions[question_index]
        is_correct = (selected_option == current_q.get("correct_answer"))
        points = quiz.get("pointsPerCorrect", 1) if is_correct else 0

        # 3. Save to History
        submissions_collection.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "question_index": question_index,
            "selected_option": selected_option,
            "is_correct": is_correct,
            "timestamp": datetime.now()
        })

        # 4. UPDATE SCORE IN PARTICIPANT OBJECT
        if points > 0:
            sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$inc": {"participants.$[participant].score": points}},
                array_filters=[{"participant.user_id": user_id}]
            )

        return {"is_correct": is_correct, "points": points}
        
    @staticmethod
    def get_user_progress(session_id: str, user_id: str) -> dict:
        # Get history with question indices and selected answers
        cursor = submissions_collection.find(
            {"session_id": session_id, "user_id": user_id},
            {"question_index": 1, "selected_option": 1, "_id": 0} 
        )
        
        # Build list of attempted questions with their selected answers
        attempted_questions = [
            {
                "question_index": doc["question_index"],
                "selected_option": doc["selected_option"]
            } 
            for doc in cursor
        ]
        
        # Get Current Score from Object
        session = sessions_collection.find_one(
            {"_id": ObjectId(session_id), PARTICIPANTS_USER_ID: user_id},
            {"participants.$": 1}
        )
        
        current_score = 0
        if session and session.get("participants"):
            current_score = session["participants"][0].get("score", 0)

        return {
            "attempted_questions": attempted_questions,
            "current_score": current_score
        }
        
        
    @staticmethod
    def get_leaderboard(session_id: str, host_id: str) -> list:
        """
        Returns the sorted list of participants with scores.
        Only the Host should be able to see the full list during the game.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        
        # Security: Only host can fetch full detailed leaderboard
        # if session["host_id"] != host_id:
            #  raise PermissionError(UNAUTHORIZED)

        participants = session.get("participants", [])
        
        # Sort by Score (Highest First)
        # Handle cases where participants might be missing 'score' key if old data
        sorted_participants = sorted(
            participants, 
            key=lambda x: x.get('score', 0), 
            reverse=True
        )
        return sorted_participants

    @staticmethod
    def mark_participant_completed(session_id: str, user_id: str) -> dict:
        """
        Marks a participant's status as 'completed' when they finish the quiz.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        
        # Check if user is enrolled
        is_enrolled = any(p["user_id"] == user_id for p in session.get("participants", []))
        if not is_enrolled:
            raise ValueError("You are not enrolled in this session.")
        
        # Update participant status to 'completed'
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"participants.$[participant].status": "completed"}},
            array_filters=[{"participant.user_id": user_id}]
        )
        return {"session_id": session_id, "user_id": user_id, "status": "completed"}

    @staticmethod
    def end_quiz(session_id: str, host_id: str) -> dict:
        """
        Host manually stops the quiz. No more submissions allowed.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if session["host_id"] != host_id:
            raise PermissionError(UNAUTHORIZED)
            
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": "completed",
                    "participants.$[].status": "completed"
                }
            }
        )
        
        print(f"Quiz {session_id} has been marked as completed by host {host_id}.")
    
        return {"session_id": session_id, "status": "completed"}
    
    
    @staticmethod
    def get_review_answers(session_id: str, user_id: str) -> list:
 
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)
        
        # send only if quiz is completed
        if session["status"] != "completed":
            raise ValueError("Quiz is not yet completed.")

        # Check enrollment inside the array of objects
        is_enrolled = any(p["user_id"] == user_id for p in session.get("participants", []))
        if not is_enrolled and session["host_id"] != user_id:
             raise PermissionError("You are not enrolled.")

        
        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})

        questions = quiz.get("questions", [])
        
        # Fetch user's submissions for this session
        submissions_cursor = submissions_collection.find(
            {"session_id": session_id, "user_id": user_id}
        )
        # Map submissions by question_index for easy lookup
        # like a dictionary for example {0: {...}, 1: {...}}
        # 
        submissions_map = {
            sub["question_index"]: sub for sub in submissions_cursor
        }

        review_list = []
        for idx, question in enumerate(questions):
            submission = submissions_map.get(idx)
            selected_option = submission["selected_option"] if submission else None
            is_correct = submission["is_correct"] if submission else False

            review_list.append({
                "question": question.get("question"),
                "options": question.get("options"),
                "correct_answer": question.get("correct_answer"),
                "selected_option": selected_option,
                "is_correct": is_correct,
                "explanation": question.get("explanation", "")
            })
        
        return review_list
    

    @staticmethod
    def truncate_collections():
        quizzes_collection.delete_many({})
        sessions_collection.delete_many({})
        submissions_collection.delete_many({})
        return True