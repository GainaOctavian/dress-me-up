from pymongo.synchronous.database import Database

from app.backend.common.db import models


def _col(db: Database):
    return db.get_collection(models.Outfit.COLLECTION_NAME)


def find_outfit_by_id(db: Database, outfit_id: str):
    return _col(db).find_one({"_id": outfit_id})


def find_visible_outfits(db: Database, owner_id: str, wardrobe_ids: list):
    """The user's own outfits plus every outfit in wardrobes they belong to"""
    return _col(db).find(
        {"$or": [{"owner_id": owner_id}, {"wardrobe_id": {"$in": wardrobe_ids}}]}
    ).sort("created_at", -1).to_list()


def find_shared_by(db: Database, owner_ids: list, before, limit: int):
    """Shared outfits of these owners, newest first, older than `before`"""
    query = {"owner_id": {"$in": owner_ids}, "shared": True}
    if before:
        query["created_at"] = {"$lt": before}
    return _col(db).find(query).sort("created_at", -1).limit(limit).to_list()


def find_outfits_by_body(db: Database, body_id: str):
    return _col(db).find({"body_id": body_id}).to_list()


def find_outfits_by_wardrobe(db: Database, wardrobe_id: str):
    return _col(db).find({"wardrobe_id": wardrobe_id}).sort("created_at", -1).to_list()


def insert_outfit(db: Database, outfit: models.Outfit):
    return _col(db).insert_one(outfit.model_dump(by_alias=True))


def update_outfit_by_id(db: Database, outfit_id: str, update_data: dict):
    return _col(db).update_one({"_id": outfit_id}, {"$set": update_data})


def delete_outfit_by_id(db: Database, outfit_id: str):
    return _col(db).delete_one({"_id": outfit_id})


def pull_item_from_outfits(db: Database, item_id: str, wardrobe_id: str = None):
    """Drop an item from outfits (only that wardrobe's, if given)"""
    query = {"items.item_id": item_id}
    if wardrobe_id:
        query["wardrobe_id"] = wardrobe_id
    return _col(db).update_many(query, {"$pull": {"items": {"item_id": item_id}}})


def detach_outfits_from_wardrobe(db: Database, wardrobe_id: str):
    """Wardrobe deleted: its outfits become personal outfits of their owners"""
    return _col(db).update_many(
        {"wardrobe_id": wardrobe_id}, {"$set": {"wardrobe_id": None}}
    )
