from datetime import datetime
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
            "quiz_id": str(quiz["_id"]),
            "title": quiz.get("title"),
            "topic": quiz.get("topic"),
            "difficulty": quiz.get("difficulty"),
            "status": session.get("status"),
            "host_id": session.get("host_id"),
            "created_at": session.get("created_at"),
            "max_participants": quiz.get("max_participants"),
            # Participants is now a list of objects {id, name, score}
            "participants": participants, 
            "participant_count": len(participants),
            "question_count": len(quiz.get("questions", []))
        }

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
            'created_at': datetime.now()
        }
        session_result = sessions_collection.insert_one(session_data)
        session_data['_id'] = session_result.inserted_id

        return QuizService._build_response_dto(session_data, quiz_data)

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
    def join_session(session_id: str, user_id: str, user_name: str) -> dict:
        """
        Adds user {user_id, name, score} to the participants list.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
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
                "score": 0
            }
            
            sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
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
            
        start_time = datetime.now()
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "active", "actual_start_time": start_time}}
        )
        return {"session_id": session_id, "status": "active", "start_time": start_time}

    @staticmethod
    def get_question_paper(session_id: str, user_id: str) -> dict:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise ValueError(SESSION_NOT_FOUND)

        # Check enrollment inside the array of objects
        is_enrolled = any(p["user_id"] == user_id for p in session.get("participants", []))
        if not is_enrolled and session["host_id"] != user_id:
             raise PermissionError("You are not enrolled.")

        quiz = quizzes_collection.find_one({"_id": ObjectId(session["quiz_id"])})
        return {
            "questions": quiz.get("questions", []),
            "duration": quiz.get("duration"),
            "start_time": session.get("actual_start_time")
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
                {
                    "_id": ObjectId(session_id), 
                    PARTICIPANTS_USER_ID: user_id 
                },
                {
                    "$inc": {"participants.$.score": points}
                }
            )

        return {"is_correct": is_correct, "points": points}
        
    @staticmethod
    def get_user_progress(session_id: str, user_id: str) -> dict:
        # Get history indices
        cursor = submissions_collection.find(
            {"session_id": session_id, "user_id": user_id},
            {"question_index": 1, "_id": 0} 
        )
        attempted_indices = [doc["question_index"] for doc in cursor]
        
        # Get Current Score from Object
        session = sessions_collection.find_one(
            {"_id": ObjectId(session_id), PARTICIPANTS_USER_ID: user_id},
            {"participants.$": 1}
        )
        
        current_score = 0
        if session and session.get("participants"):
            current_score = session["participants"][0].get("score", 0)

        return {
            "attempted_indices": attempted_indices,
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
        if session["host_id"] != host_id:
             raise PermissionError(UNAUTHORIZED)

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
    def end_quiz(session_id: str, host_id: str) -> dict:
        """
        Host manually stops the quiz. No more submissions allowed.
        """
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if session["host_id"] != host_id:
            raise PermissionError(UNAUTHORIZED)
            
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "completed"}}
        )
        return {"session_id": session_id, "status": "completed"}