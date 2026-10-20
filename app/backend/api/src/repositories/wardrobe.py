from typing import Optional

from pymongo.synchronous.database import Database

from app.backend.common.db import models


def find_wardrobe_by_id(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.find_one({"_id": wardrobe_id})


def find_wardrobes_by_user_id(db: Database, user_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.find({"user_id": user_id}).to_list()


def find_wardrobes_by_user(
        db: Database,
        user_id: str,
        role: Optional[str] = None
):
    """
    If role is None -> return wardrobes where roles.<user_id> exists.
    If role is provided -> return wardrobes where roles.<user_id> == role.
    """
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    key = f"roles.{user_id}"
    query = {key: role} if role is not None else {key: {"$exists": True}}
    return collection.find(query).to_list()


def count_wardrobes_with_member(db: Database, wardrobe_ids: list, user_id: str):
    """How many of wardrobe_ids the user has any role in"""
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.count_documents(
        {"_id": {"$in": wardrobe_ids}, f"roles.{user_id}": {"$exists": True}}
    )


def insert_wardrobe(db: Database, wardrobe: models.Wardrobe):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    data = wardrobe.model_dump(by_alias=True)
    return collection.insert_one(data)


def update_wardrobe_by_id(db: Database, wardrobe_id: str, update_data: dict):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.update_one({"_id": wardrobe_id}, {"$set": update_data})


def unset_wardrobe_role(db: Database, wardrobe_id: str, user_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.update_one(
        {"_id": wardrobe_id}, {"$unset": {f"roles.{user_id}": ""}}
    )


def delete_wardrobe_by_id(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.delete_one({"_id": wardrobe_id})
