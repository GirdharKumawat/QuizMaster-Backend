from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from accounts.authentication import CookieJWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from .util import hash_password, verify_password
from bson import ObjectId
from .serializers import SignupSerializer, LoginSerializer
from quizmaster.mongo_client import users_collection

 
COOKIE_SECURE = False
SAME_SITE = 'Lax'   


# Signup View
@api_view(["POST"])
def signup(request):
    
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Prevent duplicate emails early with a clear 400 error.
    if users_collection.find_one({"email": data["email"]}):
        return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

    user_data = {
        "username": data["username"],
        "email": data["email"],
        "password": hash_password(data["password"]),
    }
    try:
        users_collection.insert_one(user_data)
    except Exception as e:
        return Response({"error": "Failed to create user."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user = users_collection.find_one({"email": data["email"]})
    access_token, refresh_token = create_tokens_for_user(user)

    response = Response({
        "message": "User created successfully",
        "username": user["username"],
        "email": user["email"]
    }, status=status.HTTP_201_CREATED)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    
    return response

@api_view(["POST"])
def login(request):
    """Authenticate a user and set auth cookies.

    Expected input: {"email": str, "password": str}
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user = users_collection.find_one({"email": data["email"]})
    if not user or not verify_password(user["password"], data["password"]):
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    access_token, refresh_token = create_tokens_for_user(user)

    response = Response({
        "username": user["username"],
        "email": user["email"]
    }, status=status.HTTP_200_OK)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    
    return response

@api_view(['GET'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def isAuthenticated(request):
    """Check if the user is authenticated based on the access token in cookies."""
    user = request.user
    if user:
        return Response({"isAuthenticated": True}, status=status.HTTP_200_OK)
    else:
        return Response({"isAuthenticated": False}, status=status.HTTP_401_UNAUTHORIZED)
    

@api_view(['POST'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    """Clear auth cookies to log the user out."""
    response = Response({'msg': 'Logout successfully'}, status=status.HTTP_205_RESET_CONTENT)
    # Clear cookies by setting empty value and expired date.
    response.set_cookie('access_token', value='', expires='Thu, 01 Jan 1970 00:00:00 GMT', httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    response.set_cookie('refresh_token', value='', expires='Thu, 01 Jan 1970 00:00:00 GMT', httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
    return response

@api_view(['POST'])
def cookieTokenRefresh(request):  
    """Issue a new access token using the refresh token stored in cookies."""
    refresh_token = request.COOKIES.get("refresh_token")
    if not refresh_token:
        return Response({"error": "No refresh token provided."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        access_token = str(token.access_token)
        response = Response({'msg': 'Token refreshed successfully'})
        response.set_cookie(key='access_token', value=access_token, httponly=True, secure=COOKIE_SECURE, samesite=SAME_SITE)
        return response
    except Exception as e:
        return Response({"error": "Failed to refresh token."}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):
    access_token = request.COOKIES.get("access_token")
    if not access_token:
        return Response({"error": "No access token provided."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = AccessToken(access_token)
        user_id = token['user_id']
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0}) 
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        user['_id'] = str(user['_id'])  # Convert ObjectId to string for JSON serialization
        return Response(user, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Invalid or expired access token."}, status=status.HTTP_400_BAD_REQUEST)


# --- Helper utilities used by views -------------------------------------------------
def create_tokens_for_user(user: dict) -> tuple:
    refresh = RefreshToken()
    refresh["user_id"] = str(user["_id"])
    refresh["email"] = user["email"]
    return str(refresh.access_token), str(refresh)

 