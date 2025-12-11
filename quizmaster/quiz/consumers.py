# quiz/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from quizmaster.mongo_client import sessions_collection


class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.quiz_id = self.scope['url_route']['kwargs']['quiz_id']
        self.room_group_name = f'quiz_{self.quiz_id}'
        self.user = self.scope.get('user')
        
        # Check if user is authenticated
        if not self.user or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=4001)
            return
        
        # Store user_id for later use
        self.user_id = getattr(self.user, 'id', None) or str(self.user.get('_id', ''))
        
        # Check if user is host or participant
        session = await self.get_session()
        if session:
            self.is_host = (session.get('host_id') == self.user_id)
        else:
            self.is_host = False

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def get_session(self):
        """Fetch quiz session from MongoDB."""
        return sessions_collection.find_one({"quiz_id": self.quiz_id})

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'start_quiz':
            # Verify host permission (not is_staff)
            if self.is_host:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_game_start',
                        'duration': data.get('duration', 600)
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Only the host can start the quiz'
                }))

    # Handler: Start Quiz (Server -> Client)
    async def broadcast_game_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_start',
            'duration': event['duration']
        }))

    # Handler: Leaderboard Update (Server -> Client)
    async def broadcast_leaderboard(self, event):
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'top_players': event['data']
        }))

    # Handler: Participant Joined (Server -> Client)
    async def broadcast_participant_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user_id': event['user_id'],
            'username': event['username']
        }))
        