from django.urls import path
from .views import (
    QuizView,
    QuestionGenerationView,
    HostActionsView,
    ParticipantActionsView,
    QuestionPaperView,
    ReviewAnswersView,
    TruncateCollectionsView
) 

urlpatterns = [
    
    path('', QuizView.as_view(), name='quiz-list-create'),
    path('generate-questions/', QuestionGenerationView.as_view(), name='generate-questions'),
    
    path('<str:session_id>/', QuizView.as_view(), name='quiz-detail'),
    
    path('<str:session_id>/start/', HostActionsView.as_view(), {'action': 'start'}, name='quiz-start'),
    path('<str:session_id>/end/', HostActionsView.as_view(), {'action': 'end'}, name='quiz-end'),
    
    path('join/<str:join_code>/', ParticipantActionsView.as_view(), {'action': 'join'}, name='quiz-join'),
    path('<str:session_id>/begin/', ParticipantActionsView.as_view(), {'action': 'start'}, name='participant-start'),
    path('<str:session_id>/complete/', ParticipantActionsView.as_view(), {'action': 'mark_completed'}, name='participant-complete'),
    
    path('<str:session_id>/questions/', QuestionPaperView.as_view(), name='question-paper'),
    path('<str:session_id>/submit/', QuestionPaperView.as_view(), name='submit-answer'),
    
    path('<str:session_id>/review/', ReviewAnswersView.as_view(), name='review-answers'),

    path('dev/truncate/', TruncateCollectionsView.as_view(), name='truncate'),
]