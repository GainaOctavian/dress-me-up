import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, TypeAlias

import certifi
from fastapi import Depends
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.synchronous.database import Database
from dotenv import load_dotenv

# app/.env, resolved from this file so it works from any CWD.
# In Docker the vars come from compose's env_file and this is a no-op.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "dress-me-up")


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """One client per process: MongoClient is thread-safe and pools
    connections, so creating one per request only adds latency."""
    options = {"server_api": ServerApi("1")}
    if MONGODB_URI.startswith("mongodb+srv://"):  # Atlas needs a CA bundle
        options["tlsCAFile"] = certifi.where()
    return MongoClient(MONGODB_URI, **options)


def get_db() -> Database:
    """Dependency that provides the MongoDB database"""
    return get_client().get_database(DB_NAME)


DB: TypeAlias = Annotated[Database, Depends(get_db)]
