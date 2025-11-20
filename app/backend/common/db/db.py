import os
from typing import Annotated, TypeAlias

import certifi
from fastapi import Depends
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.synchronous.database import Database


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "dress-me-up")


def get_db():
    """Dependency that provides a MongoDB database connection"""
    client = MongoClient(
        MONGODB_URI,
        server_api=ServerApi("1"),
        tlsCAFile=certifi.where()
    )
    db = client.get_database(DB_NAME)
    try:
        yield db
    finally:
        client.close()


DB: TypeAlias = Annotated[Database, Depends(get_db)]
