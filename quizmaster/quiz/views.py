from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import QuizCreateSerializer,  QuizSessionSerializer,JoinQuizSerializer,PlayerQuestionSerializer
from .services import QuizService
from accounts.authentication import CookieJWTAuthentication
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime

# Quiz Views 
class QuizView(APIView):
    """url: /api/quizess/ or /api/quizess/<session_id>/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
    # 1. Validate Input  
        input_serializer = QuizCreateSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Service Logic
        user_id = request.user.get("_id")
        created_quiz_data = QuizService.create_quiz(
            user_id=user_id, 
            quiz_data=input_serializer.validated_data
        )
        
        # 3. Prepare Response
        response_serializer = QuizSessionSerializer(created_quiz_data)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, session_id=None):
        """
        GET /quizzes/ - Returns all quizzes created by and enrolled by user.
        GET /quizzes/<session_id>/ - Returns detailed information about a specific quiz session.
        """
        try:
            if session_id:
                # Get specific quiz details
                quiz_data = QuizService.get_quiz_details(session_id)
                response_data = QuizSessionSerializer(quiz_data).data
            else:
                # Get all quizzes created by user and enrolled by user
                user_id = request.user.get("_id")
                hosted_data = QuizService.get_hosted_sessions(user_id)
                enrolled_data = QuizService.get_enrolled_sessions(user_id)
                response_data = {
                    "hosted_quizzes": QuizSessionSerializer(hosted_data, many=True).data,
                    "enrolled_quizzes": QuizSessionSerializer(enrolled_data, many=True).data
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)



class HostActionsView(APIView):
    """ 
    Host actions for quiz management.
    POST /quizzes/<session_id>/start/ - Start the quiz
    POST /quizzes/<session_id>/end/ - End the quiz
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id, action):
        host_id = request.user.get("_id")
        channel_layer = get_channel_layer()
        
        try:
            if action == "start":
                result = QuizService.start_quiz(session_id, host_id)
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {'type': 'quiz_started'}
                )
                return Response(result, status=status.HTTP_200_OK)
            
            elif action == "end":
                result = QuizService.end_quiz(session_id, host_id)
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {'type': 'quiz_ended', 'session_id': session_id}
                )
                return Response(result, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        
        except (PermissionError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                

class ParticipantActionsView(APIView):
    """
    Participant actions for quiz gameplay.
    POST /quizzes/<session_id>/join/ - Join the quiz session
    POST /quizzes/<session_id>/begin/ - Start quiz timer for participant
    POST /quizzes/<session_id>/complete/ - Mark participant as completed
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id, action):
        user_id = request.user.get("_id")
        username = request.user.get("username")
        channel_layer = get_channel_layer()
        
        try:
            if action == "join":
                joined_session_data = QuizService.join_session(session_id, user_id, username)
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {
                        'type': 'participant_joined',
                        'user_id': user_id,
                        'name': username,
                        'score': 0,
                        'status': 'lobby',
                        'start_time': None
                    }
                )
                return Response(QuizSessionSerializer(joined_session_data).data, status=status.HTTP_200_OK)
            
            elif action == "start":
                start_time = datetime.now()
                result = QuizService.start_quiz_for_participant(session_id, user_id, start_time)
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {
                        'type': 'update_participant_status',
                        'user_id': user_id,
                        'status': 'active',
                        'quiz_start_time': start_time
                    }
                )
                return Response(result, status=status.HTTP_200_OK)
            
            elif action == "mark_completed":
                result = QuizService.mark_participant_completed(session_id, user_id)
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {
                        'type': 'update_participant_status',
                        'user_id': user_id,
                        'status': 'completed'
                    }
                )
                return Response(result, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    

class QuestionPaperView(APIView):
    """
    Question paper and answer submission.
    GET /quizzes/<session_id>/questions/ - Get quiz questions (answers stripped)
    POST /quizzes/<session_id>/submit/ - Submit an answer
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Get question paper for participant (answers stripped for security)"""
        user_id = request.user.get("_id")
        try:
            data = QuizService.get_question_paper(session_id, user_id)
            safe_questions = PlayerQuestionSerializer(data["questions"], many=True).data
            return Response({
                "questions": safe_questions,
                "current_question_index": data["current_question_index"],
                "start_time": data["start_time"]
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request, session_id):
        """Submit an answer for a question"""
        user_id = request.user.get("_id")
        question_index = request.data.get("question_index")
        selected_option = request.data.get("selected_option")

        try:
            result = QuizService.submit_answer(
                user_id, session_id, int(question_index), selected_option
            )
            
            # SOCKET TRIGGER: Only if score changed
            if result['points'] > 0:
                progress = QuizService.get_user_progress(session_id, user_id)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {
                        'type': 'update_participant_score',
                        'user_id': user_id,
                        'score': progress['current_score']
                    }
                )

            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


 
  
 
 

# a temparoary view to tunckate the sessions collection and quiz collection
class TruncateCollectionsView(APIView):
    
    def delete(self, request):
        
        try:
            QuizService.truncate_collections()
            return Response({"message": "Collections truncated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
