import json
from channels.generic.websocket import AsyncWebsocketConsumer

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles the WebSocket connection.
        """
        # 1. Get Session ID from the URL route (ws/quiz/<session_id>/)
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'quiz_{self.session_id}'
        self.user = self.scope.get('user')

        # 2. Security Check: Reject if user is not authenticated
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # 3. Join the Redis Group (Room)
        # This subscribes this specific WebSocket connection to the session's channel
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnection.
        """
        # Leave the Redis Group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # ----------------------------------------------------
    # EVENT HANDLERS
    # These functions are triggered by your Views (via Redis)
    # ----------------------------------------------------

    # 1. Triggered when Host calls /quiz/start/
    async def quiz_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_started',
            'session_id': event['session_id'],
            'start_time': event['start_time']
        }))

    # 2. Triggered when a Student calls /quiz/submit/
    async def leaderboard_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'user_id': event['user_id'],
            'name': event['name'],
            'score_added': event['score_added'],
            'total_score': event['total_score']
        }))

    # 3. Triggered when a Student calls /quiz/join/
    async def participant_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user_id': event['user_id'],
            'name': event['name'],
            'participant_count': event['participant_count']
        }))
    
    # Event 4: Quiz Ended
    async def quiz_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_ended',
            'session_id': event['session_id']
        }))