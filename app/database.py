from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL
from pymongo import errors

try:
    # Initialize MongoDB connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["strawhats"]  # Replace with your database name
    print("MongoDB connected successfully!")
except errors.ConnectionError:
    print("Error connecting to MongoDB.")
