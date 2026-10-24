from pymongo.synchronous.database import Database

from app.backend.common.db import models


def _requests(db: Database):
    return db.get_collection(models.FriendRequest.COLLECTION_NAME)


def _users(db: Database):
    return db.get_collection(models.User.COLLECTION_NAME)


def insert_request(db: Database, request: models.FriendRequest):
    return _requests(db).insert_one(request.model_dump(by_alias=True))


def find_request_by_id(db: Database, request_id: str):
    return _requests(db).find_one({"_id": request_id})


def find_pending_between(db: Database, from_user_id: str, to_user_id: str):
    return _requests(db).find_one(
        {"from_user_id": from_user_id, "to_user_id": to_user_id, "status": "pending"}
    )


def find_pending_for(db: Database, user_id: str):
    """Pending requests sent to or by the user, newest first"""
    return _requests(db).find(
        {"status": "pending", "$or": [{"to_user_id": user_id}, {"from_user_id": user_id}]}
    ).sort("created_at", -1).to_list()


def set_request_status(db: Database, request_id: str, status: str):
    return _requests(db).update_one(
        {"_id": request_id, "status": "pending"}, {"$set": {"status": status}}
    )


def add_friends(db: Database, a: str, b: str):
    # ponytail: two updates, no transaction; a crash between them leaves a
    # one-sided friendship (use a Mongo transaction if it ever shows up)
    _users(db).update_one({"_id": a}, {"$addToSet": {"friend_ids": b}})
    _users(db).update_one({"_id": b}, {"$addToSet": {"friend_ids": a}})


def remove_friends(db: Database, a: str, b: str):
    _users(db).update_one({"_id": a}, {"$pull": {"friend_ids": b}})
    _users(db).update_one({"_id": b}, {"$pull": {"friend_ids": a}})


def forget_user(db: Database, user_id: str):
    """A deleted account leaves no friendships or requests behind"""
    _users(db).update_many({"friend_ids": user_id}, {"$pull": {"friend_ids": user_id}})
    _requests(db).delete_many({"$or": [{"from_user_id": user_id}, {"to_user_id": user_id}]})


def find_users(db: Database, user_ids: list):
    return _users(db).find({"_id": {"$in": user_ids}}).to_list()


def share_a_wardrobe(db: Database, a: str, b: str) -> bool:
    col = db.get_collection(models.Wardrobe.COLLECTION_NAME)
    return col.find_one({f"roles.{a}": {"$exists": True}, f"roles.{b}": {"$exists": True}},
                        {"_id": 1}) is not None
