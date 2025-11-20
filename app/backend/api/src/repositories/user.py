from pymongo.synchronous.database import Database

from app.backend.common.db import models


def find_all_users(db: Database):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    return collection.find({}).to_list()


def find_user_by_id(db: Database, user_id: str):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    return collection.find_one({"_id": user_id})


def insert_user(db: Database, user: models.User):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    # ensure hashed_password is included
    data = user.model_dump(by_alias=True)
    if user.hashed_password is not None:
        data["hashed_password"] = user.hashed_password
    return collection.insert_one(data)


def update_user_by_id(db: Database, user_id: str, update_data: dict):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    return collection.update_one({"_id": user_id}, {"$set": update_data})


def delete_user_by_id(db: Database, user_id: str):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    return collection.delete_one({"_id": user_id})


def find_user_by_email(db: Database, email: str):
    collection = db.get_collection(models.User.COLLECTION_NAME)
    return collection.find_one({"email": email})
