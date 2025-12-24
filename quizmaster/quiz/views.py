from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import QuizCreateSerializer,  QuizSessionSerializer,JoinQuizSerializer,PlayerQuestionSerializer
from .services import QuizService
from accounts.authentication import CookieJWTAuthentication
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
 


class CreateQuizView(APIView):
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

class DashboardView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
        """
        Returns a list of all quizzes created by the current user.
        """
        # 1. Get user ID
        user_id = request.user.get("_id")
        
        # 2. Get Data from Service (We need to make sure this function exists in services.py)
        dashboard_data = QuizService.get_hosted_sessions(user_id)
        
        # 3. Serialize Data
        serializer = QuizSessionSerializer(dashboard_data, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
 
class JoinQuizView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. Validate Input
        serializer = JoinQuizSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session_id = serializer.validated_data["session_id"]
        user_id = request.user.get("_id")
        username = request.user.get("username") 
        
        print("Joining user:", user_id, username)
        # Assuming you have name in user object

        try:
            # 2. Call Service
            joined_session_data = QuizService.join_session(session_id, user_id,username)
            
            # 3. Return Standard Response
            response_serializer = QuizSessionSerializer(joined_session_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            # Handle "Session full" or "Not found" errors nicely
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EnrolledQuizListView(APIView):
    authentication_classes = [CookieJWTAuthentication] 
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.get("_id")
        
        # 1. Get Enrolled Data
        enrolled_data = QuizService.get_enrolled_sessions(user_id)
        
        # 2. Use the SAME Serializer (Consistency!)
        serializer = QuizSessionSerializer(enrolled_data, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class QuizStatusView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        user_id = request.user.get("_id")
        try:
            progress = QuizService.get_user_progress(session_id, user_id)
            return Response(progress, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
# 1. START QUIZ (HOST)
class StartQuizView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        session_id = request.data.get("session_id")
        host_id = request.user.get("_id")

        try:
            # 1. DB Update (Service)
            result = QuizService.start_quiz(session_id, host_id)
            
            # 2. SOCKET TRIGGER: Notify everyone "Quiz Started!"
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'quiz_{session_id}',  # Group Name
                {
                    'type': 'quiz_started', # Matches method name in Consumer
                    'session_id': session_id,
                    'start_time': str(result['start_time'])
                }
            )
            
            return Response(result, status=200)
        except (PermissionError, ValueError) as e:
            return Response({"error": str(e)}, status=400)
        
        
# 2. GET PAPER (STUDENT)
class GetQuestionPaperView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, session_id):
        user_id = request.user.get("_id")
        try:
            data = QuizService.get_question_paper(session_id, user_id)
            
            # SECURITY: Use Serializer to strip answers
            safe_questions = PlayerQuestionSerializer(data["questions"], many=True).data
            
            return Response({
                "questions": safe_questions,
                "duration": data["duration"],
                "start_time": data["start_time"]
            }, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

# 3. SUBMIT ANSWER (STUDENT)
class SubmitAnswerView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Extract inputs
        user_id = request.user.get("_id")
        user_name = request.user.get("username") 

        session_id = request.data.get("session_id")
        question_index = request.data.get("question_index")
        selected_option = request.data.get("selected_option")

        try:
            # 1. DB Update (Service)
            result = QuizService.submit_answer(
                user_id, session_id, int(question_index), selected_option
            )
            
            # 2. SOCKET TRIGGER: Only if score changed
            if result['points'] > 0:
                
                # Fetch updated total score to show in leaderboard
                # (You might want to return this from submit_answer to save a DB call)
                progress = QuizService.get_user_progress(session_id, user_id)
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'quiz_{session_id}',
                    {
                        'type': 'leaderboard_update',
                        'user_id': user_id,
                        'name': user_name,
                        'score_added': result['points'],
                        'total_score': progress['current_score']
                    }
                )

            return Response(result, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
    
# 4. GET LEADERBOARD (HOST ONLY)
class GetLeaderboardView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, session_id):
        try:
            data = QuizService.get_leaderboard(session_id, request.user.get("_id"))
            return Response({"leaderboard": data}, status=200)
        except PermissionError:
            return Response({"error": "Unauthorized"}, status=403)
        except ValueError as e:
             return Response({"error": str(e)}, status=404)

# 5. END QUIZ (HOST ONLY)
class EndQuizView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            # 1. DB Update
            result = QuizService.end_quiz(
                request.data.get("session_id"), 
                request.user.get("_id")
            )
            
            # 2. SOCKET TRIGGER: Notify students "Quiz Ended"
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'quiz_{request.data.get("session_id")}',
                {'type': 'quiz_ended', 'session_id': result['session_id']}
            )
            return Response(result, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
