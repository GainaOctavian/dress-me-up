from pymongo.synchronous.database import Database

from app.backend.common.db import models


def find_all_wardrobes(db: Database):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.find({}).to_list()


def find_wardrobe_by_id(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.find_one({"_id": wardrobe_id})


def find_wardrobes_by_user_id(db: Database, user_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.find({"user_id": user_id}).to_list()


def find_wardrobes_by_user_role(db: Database, user_id: str, role: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    query = {f"roles.{user_id}": role}
    return collection.find(query).to_list()


def insert_wardrobe(db: Database, wardrobe: models.Wardrobe):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    data = wardrobe.model_dump(by_alias=True)
    return collection.insert_one(data)


def update_wardrobe_by_id(db: Database, wardrobe_id: str, update_data: dict):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.update_one({"_id": wardrobe_id}, {"$set": update_data})


def delete_wardrobe_by_id(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return collection.delete_one({"_id": wardrobe_id})


