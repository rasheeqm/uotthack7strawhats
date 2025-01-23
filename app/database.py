from motor.motor_asyncio import AsyncIOMotorClient
import os
from pymongo import errors

MONGO_URL = os.environ.get("MONGO_URL")

try:
    # Initialize MongoDB connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["strawhats"]  # Replace with your database name
    print("MongoDB connected successfully!")
except errors.ConnectionError:
    print("Error connecting to MongoDB.")
