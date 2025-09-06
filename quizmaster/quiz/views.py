# quizzes/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .serializers import QuizCreateSerializer
from accounts.authentication import CookieJWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from quizmaster.mongo_client import quizzes_collection, sessions_collection
from bson import ObjectId
from datetime import datetime
 

 

 
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
 
    session = sessions_collection.find_one({"quiz_id": quiz_id})
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    
    if not session:
        return Response({"detail": "Quiz session not found."}, status=status.HTTP_404_NOT_FOUND)

    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
    
    if session["status"] != "waiting":
        return Response({"detail": "Cannot join. Quiz already started."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    participants = session.get("participants", [])

    if len(participants) >= quiz.get("max_participants", 0):
        return Response({"detail": "Quiz is full."}, status=status.HTTP_400_BAD_REQUEST)

    if any(participant["user_id"] == ObjectId(user_id) for participant in participants):
        return Response({"detail": "User already joined the quiz."}, status=status.HTTP_400_BAD_REQUEST)

    new_participant = {
      "user_id": user_id,
      "username": username,
      "score": 0,
      "currentQuestionIndex": -1,
      "answers": [],
      "joinedAt": datetime.utcnow()
    }
    sessions_collection.update_one(
        {"quiz_id": quiz_id},
        {"$push": {"participants": new_participant}}
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

    return Response({"message": "Quiz started successfully."}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def check_answer(request, quiz_id,selected_answer):
    user = request.user 
    user_id = user["_id"]
    
    if not selected_answer:
        return Response({"detail": "Selected answer is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    quiz_session = sessions_collection.find_one({"quiz_id": quiz_id})
    if not quiz_session:
        return Response({"detail": "Quiz session not found."}, status=status.HTTP_404_NOT_FOUND)
    
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
    
    
    if quiz_session["status"] != "in_progress":
        return Response({"detail": "Quiz is not in progress."}, status=status.HTTP_400_BAD_REQUEST)
    
    participants = quiz_session.get("participants", [])
    participant = next((p for p in participants if p["user_id"] == user_id), None)
    
    if not participant:
        return Response({"detail": "User not a participant in this quiz."}, status=status.HTTP_403_FORBIDDEN)
    
   
    current_index = participant.get("currentQuestionIndex", -1) + 1
    print("Current question index:", current_index)
    
     # Check if there are more questions
    if current_index >= len(quiz["questions"]):
        return Response({"detail": "No more questions left."}, status=status.HTTP_400_BAD_REQUEST)
    
    current_question = quiz["questions"][current_index]
    print("Current question:", current_question)
    is_correct = (selected_answer == current_question["correct_answer"])
    print("Is correct:", is_correct)
    
    selected_answer = {
          "question_index": current_index,
          "selectedOption": selected_answer,
          "isCorrect":  is_correct,
        }
    print("Selected answer data:", selected_answer)
    # Update participant's data
    total_score = participant.get("score", 0)
    if is_correct:
        total_score = total_score + 1
    
    update_fields = {
        "participants.$.currentQuestionIndex": current_index,
        "participants.$.answers": participant.get("answers", []) + [selected_answer],
        "participants.$.score": total_score,
    }
    print("Update fields:", update_fields)
    sessions_collection.update_one(
        {"quiz_id": quiz_id, "participants.user_id": user_id},
        {"$set": update_fields}
    )
    
    return Response({
        "is_correct": is_correct,
    }, status=status.HTTP_200_OK)

