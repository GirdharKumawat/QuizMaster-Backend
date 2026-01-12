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

    # Event 1: Participant Joined
    async def participant_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user_id': event['user_id'],
            'name': event['name'],
            'score': event['score'],
            'status': event['status'],
            'start_time': event['start_time']
        }))
        

    # Event 2: Quiz Started
    async def quiz_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_started',
        }))

    # Event 3: participant Score Updated
    async def update_participant_score(self, event):
        await self.send(text_data=json.dumps({
            'type': 'update_participant_score',
            'user_id': event['user_id'],
            'score': event['score']
        }))   
    
    
    # Event 4: participant Status Updated    
    async def update_participant_status(self, event):
        start_time = event.get('quiz_start_time')
        
        start_time_str = start_time.isoformat() if start_time else None
        
        if event['status'] == 'active':
            await self.send(text_data=json.dumps({
                'type': 'update_participant_status',
                'user_id': event['user_id'],
                'status': event['status'],
                'quiz_start_time': start_time_str
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'update_participant_status',
                'user_id': event['user_id'],
                'status': event['status'],
            }))
    
    # Event 5: Quiz Ended
    async def quiz_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_ended',
        }))

  