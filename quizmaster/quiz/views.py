# quizzes/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .serializers import QuizCreateSerializer
from .utils import is_valid_object_id
from accounts.authentication import CookieJWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from quizmaster.mongo_client import quizzes_collection, sessions_collection
from bson import ObjectId
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
 


 
@csrf_exempt
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_quiz(request):
     
    user = request.user 
    user_id = user["_id"]
    serializer = QuizCreateSerializer(data=request.data, context={"user": user_id})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    quiz_data = serializer.save()
    quiz_result = quizzes_collection.insert_one(quiz_data)
    
    curr_quiz_session = {
        "quiz_id": str(quiz_result.inserted_id),
        "host_id": user_id,
        "status": "waiting",
        "participants": [],
        "created_at": datetime.utcnow(),
    }

    quiz_session_result = sessions_collection.insert_one(curr_quiz_session)

    return Response({
        "message": "Quiz created",
        "quiz_id": str(quiz_result.inserted_id),
        "quiz_session_id": str(quiz_session_result.inserted_id)
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_created_quiz_list(request):
    """Retrieve all quizzes for the logged-in user and include session info."""
    user_id = request.user["_id"]

    # Fetch quizzes created by this user
    quizzes = list(quizzes_collection.find({"created_by": user_id}))
    # Fetch sessions hosted by this user
    sessions = list(sessions_collection.find({"host_id": user_id}))

    data = []

    for quiz in quizzes:
        quiz_id = str(quiz["_id"])

        # Find matching session (if exists)
        session = next((s for s in sessions if str(s.get("quiz_id")) == quiz_id), None)

        # Build response object
        quiz_obj = {
            "_id": quiz_id,
            "title": quiz.get("title"),
            "description": quiz.get("description"),
            "topic": quiz.get("topic"),
            "difficulty": quiz.get("difficulty"),
            "duration": quiz.get("duration"),
            "start_time": quiz.get("start_time"),
            "max_participants": quiz.get("max_participants"),
            "pointsPerCorrect": quiz.get("pointsPerCorrect"),
            "questionCount": len(quiz.get("questions", [])),
            "host_id": str(quiz.get("created_by")),
            "status": session.get("status") if session else None,
            "participants": session.get("participants", []) if session else [],
            "created_at": quiz.get("created_at"),
        }

        data.append(quiz_obj)

    return Response({"quizzes": data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_enrolled_quiz_list(request):
    """Retrieve all quizzes the user has joined as a participant."""
    user_id = request.user["_id"]

    # Fetch sessions where the user is a participant
    sessions = list(sessions_collection.find({"participants.user_id": user_id}))

    data = []

    for session in sessions:
        quiz_id = session.get("quiz_id")
        quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})

        if not quiz:
            continue
 
        # Build response object
        quiz_obj = {
            "_id": str(quiz["_id"]),
            "title": quiz.get("title"),
            "description": quiz.get("description"),
            "topic": quiz.get("topic"),
            "difficulty": quiz.get("difficulty"),
            "duration": quiz.get("duration"),
            "start_time": quiz.get("start_time"),
            "max_participants": quiz.get("max_participants"),
            "pointsPerCorrect": quiz.get("pointsPerCorrect"),
            "questionCount": len(quiz.get("questions", [])),
            "host_id": str(quiz.get("created_by")),
            "status": session.get("status"),
            "participants": session.get("participants", []),
            "created_at": quiz.get("created_at"),
        }

        data.append(quiz_obj)

    return Response({"quizzes": data}, status=status.HTTP_200_OK)

@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_sessions(request, quiz_id):
    """Retrieve a quiz by ObjectId string and return a JSON-serializable document."""
  
    session = sessions_collection.find_one({"quiz_id": quiz_id})
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not session:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    session["_id"] = str(session["_id"])
    quiz["_id"] = str(quiz["_id"])
    
    response = {
        "quiz": quiz,
        "session": session
    }
    return Response(response, status=status.HTTP_200_OK)
 

@csrf_exempt
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def join_quiz(request, quiz_id):
    
    print("Joining quiz:", quiz_id)
    user = request.user 
    user_id = user["_id"]
    username = user.get("username")
 
    # First check if quiz exists
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
    
    max_participants = quiz.get("max_participants", 0)

    new_participant = {
        "user_id": user_id,
        "username": username,
        "score": 0,
        "currentQuestionIndex": 0,
        "answers": [],
        "joinedAt": datetime.utcnow()
    }

    # Atomic update: Only add participant if:
    # 1. Session exists and status is "waiting"
    # 2. User hasn't already joined
    # 3. Room is not full (participants count < max_participants)
    result = sessions_collection.find_one_and_update(
        {
            "quiz_id": quiz_id,
            "status": "waiting",
            "participants.user_id": {"$ne": user_id},  # User not already in list
            "$expr": {"$lt": [{"$size": "$participants"}, max_participants]}  # Room not full
        },
        {"$push": {"participants": new_participant}},
        return_document=False  # Return original doc (before update)
    )

    if result is None:
        # Update failed - determine why
        session = sessions_collection.find_one({"quiz_id": quiz_id})
        if not session:
            return Response({"detail": "Quiz session not found."}, status=status.HTTP_404_NOT_FOUND)
        if session["status"] != "waiting":
            return Response({"detail": "Cannot join. Quiz already started."}, status=status.HTTP_400_BAD_REQUEST)
        if any(p["user_id"] == user_id for p in session.get("participants", [])):
            return Response({"detail": "User already joined the quiz."}, status=status.HTTP_400_BAD_REQUEST)
        if len(session.get("participants", [])) >= max_participants:
            return Response({"detail": "Quiz is full."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Could not join quiz."}, status=status.HTTP_400_BAD_REQUEST)

    # Notify other participants via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"quiz_{quiz_id}",
        {
            "type": "broadcast_participant_joined",
            "user_id": user_id,
            "username": username
        }
    )

    return Response({"message": "Joined the quiz successfully."}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def start_quiz(request, quiz_id):
    user = request.user 
    user_id = user["_id"]
 
    quiz_session = sessions_collection.find_one({"quiz_id": quiz_id})
    
    if not quiz_session:
        return Response({"detail": "Quiz session not found."}, status=status.HTTP_404_NOT_FOUND)
    
    if quiz_session["host_id"] != user_id:
        return Response({"detail": "Only the host can start the quiz."}, status=status.HTTP_403_FORBIDDEN)
    
    sessions_collection.update_one(
        {"quiz_id": quiz_id},
        {"$set": {"status": "in_progress", "startedAt": datetime.utcnow()}}
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"quiz_{quiz_id}",  # Group Name
        {
            "type": "broadcast_game_start", # Function to call in consumer
            "duration": 60 # You might want to fetch actual duration from the quiz object
        }
    )

    return Response({"message": "Quiz started successfully."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_current_question(request, quiz_id):
    """Return the participant's current question (without the correct answer).

    Response contains: question_index, question, options, total_questions.
    """
    user = request.user
    user_id = user["_id"]

    # session must exist
    quiz_session = sessions_collection.find_one({"quiz_id": quiz_id})
    if not quiz_session:
        return Response({"detail": "Quiz session not found."}, status=status.HTTP_404_NOT_FOUND)

    # find participant
    participants = quiz_session.get("participants", [])
    participant = next((p for p in participants if p["user_id"] == user_id), None)
    if not participant:
        return Response({"detail": "User not a participant in this quiz."}, status=status.HTTP_403_FORBIDDEN)

    # validate quiz existence and id
    if not is_valid_object_id(quiz_id):
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    quiz = quizzes_collection.find_one({"_id": ObjectId(str(quiz_id))})
    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    current_index = participant.get("currentQuestionIndex", 0)
    if current_index is None:
        current_index = 0

    questions = quiz.get("questions", [])
    total = len(questions)

    if current_index >= total:
        return Response({"detail": "No more questions left."}, status=status.HTTP_400_BAD_REQUEST)

    q = questions[current_index]
    # Do not expose correct_answer
    question_payload = {
        "question_index": current_index,
        "question": q.get("question"),
        "options": q.get("options", []),
        "total_questions": total,
    }
    return Response(question_payload, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def submit_answer(request, quiz_id):
    """
    Evaluates answer, pushes to history, increments score/index atomically.
    Prevents race conditions using optimistic locking.
    """
    user = request.user
    user_id = user["_id"] # Ensure this matches your DB format (str vs ObjectId)

    selected_answer = request.data.get("answer")
    if selected_answer is None:
        return Response({"detail": "selected_answer is required."}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Validate Quiz ID and Fetch Quiz (Questions)
    if not is_valid_object_id(quiz_id):
        return Response({"detail": "Invalid Quiz ID."}, status=status.HTTP_400_BAD_REQUEST)
        
    quiz = quizzes_collection.find_one({"_id": ObjectId(str(quiz_id))})
    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    # 2. Fetch ONLY the specific participant from the session
    # We filter by quiz_id AND user_id immediately
    quiz_session = sessions_collection.find_one(
        {"quiz_id": quiz_id, "participants.user_id": user_id},
        {"status": 1, "participants.$": 1} # Projection: Fetch only the matching participant
    )

    if not quiz_session:
        return Response({"detail": "Session not found or user not a participant."}, status=status.HTTP_404_NOT_FOUND)
        
    if quiz_session.get("status") != "in_progress":
        return Response({"detail": "Quiz is not in progress."}, status=status.HTTP_400_BAD_REQUEST)

    # Extract participant data (Projection ensures list has exactly 1 item)
    participant = quiz_session["participants"][0]
    current_index = participant.get("currentQuestionIndex", 0)

    questions = quiz.get("questions", [])
    
    # 3. Check if quiz is finished
    if current_index >= len(questions):
        return Response({"detail": "No more questions left."}, status=status.HTTP_400_BAD_REQUEST)

    # 4. Evaluate Answer
    current_question = questions[current_index]
    correct_answer = current_question.get("correct_answer")
    is_correct = (selected_answer == correct_answer)

    answer_record = {
        "question_index": current_index,
        "selectedOption": selected_answer,
        "isCorrect": is_correct,
    }

    # 5. Atomic Update with Optimistic Locking
    # We define what we want to change
    update_ops = {
        "$push": {"participants.$.answers": answer_record}, # Append efficiently
        "$inc": {"participants.$.currentQuestionIndex": 1}  # Increment atomically
    }

    # If correct, we also increment the score atomically
    if is_correct:
        update_ops["$inc"]["participants.$.score"] = 1

    # EXECUTE UPDATE
    # The filter includes 'participants.currentQuestionIndex': current_index
    # This prevents race conditions. If the index changed while we were calculating,
    # this update will fail (match count 0), preventing double submission.
    result = sessions_collection.update_one(
        {
            "quiz_id": quiz_id, 
            "participants.user_id": user_id,
            "participants.currentQuestionIndex": current_index 
        },
        update_ops
    )

    if result.matched_count == 0:
        # This happens if the user double-clicked and the index already moved forward
        return Response({"detail": "Answer already submitted for this question."}, status=status.HTTP_409_CONFLICT)

    return Response({
        "is_correct": is_correct, 
        "correct_answer": correct_answer, # Optional: return correct answer to user
        "next_question_index": current_index + 1
    }, status=status.HTTP_200_OK)