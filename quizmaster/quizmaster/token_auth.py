from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from quizmaster.mongo_client import users_collection
from bson import ObjectId

@database_sync_to_async
def get_user(user_id):
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
            # Create a simple object to mimic Django's User model
            class User:
                is_authenticated = True
                id = user['_id']
                username = user.get('username')
                email = user.get('email')
                is_staff = user.get('is_staff', False) # Fallback if not present
            return User()
        return None
    except Exception:
        return None

class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # 1. Get headers from scope
        headers = dict(scope['headers'])
        
        # 2. Extract Cookie header
        # Headers are byte strings in ASGI, so we decode them
        cookies_str = headers.get(b'cookie', b'').decode()
        
        access_token = None
        
        # 3. Parse cookies to find 'access_token'
        # Format: "name=value; name2=value2"
        for cookie in cookies_str.split('; '):
            if cookie.startswith('access_token='):
                access_token = cookie.split('=')[1]
                break
        
        # 4. Validate Token
        if access_token:
            try:
                # Decode the token (stateless check)
                token = AccessToken(access_token)
                user_id = token['user_id']
                
                # Fetch user from DB
                scope['user'] = await get_user(user_id)
                
            except (InvalidToken, TokenError, KeyError):
                # Token is invalid
                from django.contrib.auth.models import AnonymousUser
                scope['user'] = AnonymousUser()
        else:
            from django.contrib.auth.models import AnonymousUser
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)