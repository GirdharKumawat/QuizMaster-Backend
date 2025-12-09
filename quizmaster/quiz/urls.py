from django.urls import path
from . import views

urlpatterns = [
    path('created/', views.get_created_quiz_list, name='get_created_quiz_list'),
    path('enrolled/', views.get_enrolled_quiz_list, name='get_enrolled_quiz_list'),
    path('create/', views.create_quiz, name='create_quiz'),
    path('<str:quiz_id>/', views.get_sessions, name='get_sessions'),
    path('<str:quiz_id>/join/', views.join_quiz, name='join_quiz'),  # Placeholder for join quiz view
    path('<str:quiz_id>/start/', views.start_quiz, name='start_quiz'),  # Placeholder for join quiz view
    path('<str:quiz_id>/question/', views.get_current_question, name='get_current_question'),
    path('<str:quiz_id>/submit/', views.submit_answer, name='submit_answer'),
    
]
     