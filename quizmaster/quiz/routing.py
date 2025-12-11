from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/quiz/<str:quiz_id>/', consumers.QuizConsumer.as_asgi()),
]