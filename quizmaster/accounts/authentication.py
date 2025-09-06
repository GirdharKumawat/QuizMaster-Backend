from bson import ObjectId

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from quizmaster.mongo_client import users_collection

class DictUser(dict):
    @property
    def is_authenticated(self):
        return True

class CookieJWTAuthentication(JWTAuthentication):
    
    def authenticate(self, request):
        token = request.COOKIES.get("access_token")
        if not token:
            return None  # No token means no authentication attempted

        try:
            validated_token = self.get_validated_token(token)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(f"Token validation failed: {str(e)}")
 
         
        try:
            user_doc = users_collection.find_one({"_id": ObjectId(validated_token.get("user_id"))}, {"password": 0})
        except Exception:
            raise AuthenticationFailed("Invalid user id in token")
        
        if not user_doc:
            raise AuthenticationFailed("User not found")
        
        user_doc["_id"] = str(user_doc["_id"])
        
         
        return (DictUser(user_doc), validated_token)