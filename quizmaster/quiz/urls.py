from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_quiz_list, name='get_quiz_list'),
    path('create/', views.create_quiz, name='create_quiz'),
    path('<str:quiz_id>/', views.get_sessions, name='get_sessions'),
    path('<str:quiz_id>/join/', views.join_quiz, name='join_quiz'),  # Placeholder for join quiz view
    path('<str:quiz_id>/start/', views.start_quiz, name='start_quiz'),  # Placeholder for join quiz view
    path('<str:quiz_id>/check/<str:selected_answer>/', views.check_answer, name='check_answer'),  # Placeholder for join quiz view
    
]
     