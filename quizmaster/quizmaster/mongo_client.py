
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://girdharkumawat20:girdhar.mongodb@cluster0.jg1ia.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
print("MongoDB connected")
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.quizmaster
users_collection = db.users
quizzes_collection = db.quizzes
sessions_collection = db.sessions