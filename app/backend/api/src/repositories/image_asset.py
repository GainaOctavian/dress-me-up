from pymongo.synchronous.database import Database

from app.backend.common.db import models


def insert_asset(db: Database, asset: models.ImageAsset):
    collection = db.get_collection(models.ImageAsset.COLLECTION_NAME)
    return collection.insert_one(asset.model_dump(by_alias=True))


def find_asset_by_id(db: Database, asset_id: str):
    collection = db.get_collection(models.ImageAsset.COLLECTION_NAME)
    return collection.find_one({"_id": asset_id})


def find_assets_by_ids(db: Database, asset_ids: list):
    collection = db.get_collection(models.ImageAsset.COLLECTION_NAME)
    return collection.find({"_id": {"$in": asset_ids}}).to_list()


def update_asset_by_id(db: Database, asset_id: str, update_data: dict):
    collection = db.get_collection(models.ImageAsset.COLLECTION_NAME)
    return collection.update_one({"_id": asset_id}, {"$set": update_data})


def delete_asset_by_id(db: Database, asset_id: str):
    collection = db.get_collection(models.ImageAsset.COLLECTION_NAME)
    return collection.delete_one({"_id": asset_id})
