from pymongo.synchronous.database import Database

from app.backend.common.db import models


def find_visible_bodies(db: Database, user_id: str):
    """Built-in mannequins plus the user's own bodies"""
    collection = db.get_collection(models.Body.COLLECTION_NAME)
    return collection.find(
        {"$or": [{"owner_id": None}, {"owner_id": user_id}]}
    ).sort("_id", 1).to_list()


def find_body_by_id(db: Database, body_id: str):
    collection = db.get_collection(models.Body.COLLECTION_NAME)
    return collection.find_one({"_id": body_id})
