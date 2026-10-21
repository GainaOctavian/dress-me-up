from pymongo.synchronous.database import Database

from app.backend.common.db import models


def find_item_by_id(db: Database, item_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.find_one({"_id": item_id})


def find_items_by_ids(db: Database, item_ids: list):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.find({"_id": {"$in": item_ids}}).to_list()


def find_items_by_owner(db: Database, owner_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.find({"owner_id": owner_id}).to_list()


def find_items_by_wardrobe(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.find({"wardrobe_ids": wardrobe_id}).to_list()


def count_items_in_wardrobe(db: Database, wardrobe_id: str) -> int:
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.count_documents({"wardrobe_ids": wardrobe_id})


def insert_item(db: Database, item: models.Item):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.insert_one(item.model_dump(by_alias=True))


def update_item_by_id(db: Database, item_id: str, update_data: dict):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.update_one({"_id": item_id}, {"$set": update_data})


def add_item_to_wardrobe(db: Database, item_id: str, wardrobe_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.update_one(
        {"_id": item_id}, {"$addToSet": {"wardrobe_ids": wardrobe_id}}
    )


def remove_item_from_wardrobe(db: Database, item_id: str, wardrobe_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.update_one(
        {"_id": item_id}, {"$pull": {"wardrobe_ids": wardrobe_id}}
    )


def pull_wardrobe_from_items(db: Database, wardrobe_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.update_many(
        {"wardrobe_ids": wardrobe_id}, {"$pull": {"wardrobe_ids": wardrobe_id}}
    )


def delete_item_by_id(db: Database, item_id: str):
    collection = db.get_collection(models.Item.COLLECTION_NAME)
    return collection.delete_one({"_id": item_id})
