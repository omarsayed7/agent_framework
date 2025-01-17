from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient

import os

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")


class MongoDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DATABASE_NAME]


mongodb = MongoDB()
