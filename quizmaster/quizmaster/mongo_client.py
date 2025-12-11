
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get MongoDB URI from environment
uri = os.getenv('MONGO_URI')

# Create a new client and connect to the server
print("MongoDB connected")
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.quizmaster
users_collection = db.users
quizzes_collection = db.quizzes
sessions_collection = db.sessions