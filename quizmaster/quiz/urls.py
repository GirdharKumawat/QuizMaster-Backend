from django.urls import path
from . import views

urlpatterns = [
    # --- LOBBY & MANAGEMENT ---
    path('create/', views.CreateQuizView.as_view(), name='create_quiz'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
  
    path('join/', views.JoinQuizView.as_view(), name='join_quiz'),
    path('enrolled/', views.EnrolledQuizListView.as_view(), name='enrolled_quizzes'),

    # --- GAMEPLAY (HOST) ---
    path('start/', views.StartQuizView.as_view(), name='start_quiz'),

    # --- GAMEPLAY (STUDENT) ---
    # Fetch questions securely (no answers included)
    path('paper/<str:session_id>/', views.GetQuestionPaperView.as_view(), name='get_question_paper'),
    
    # Submit a single answer
    path('submit/', views.SubmitAnswerView.as_view(), name='submit_answer'),
    
    # Check status (For handling page refreshes)
    path('status/<str:session_id>/', views.QuizStatusView.as_view(), name='quiz_status'),
    path('leaderboard/<str:session_id>/', views.GetLeaderboardView.as_view(), name='get_leaderboard'),
    path('end/', views.EndQuizView.as_view(), name='end_quiz'),
]