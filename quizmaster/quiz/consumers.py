# quiz/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.quiz_id = self.scope['url_route']['kwargs']['quiz_id']
        
        self.room_group_name = f'quiz_{self.quiz_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 5. Leave the Room Group when they disconnect
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    async def receive(self, text_data):
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'start_quiz':
                # Verify Admin permission
                if self.scope['user'].is_staff:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'broadcast_game_start',
                            'duration': data.get('duration', 600)
                        }
                    )

        # 2. Handler: Start Quiz (Server -> Client)
    async def broadcast_game_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_start',
            'duration': event['duration']
        }))

    # 3. Handler: Leaderboard Update (Server -> Client)
    async def broadcast_leaderboard(self, event):
        # This will be triggered by your Django Views (REST API)
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'top_players': event['data']
        }))
        