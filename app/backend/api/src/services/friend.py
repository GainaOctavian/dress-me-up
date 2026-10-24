from typing import Dict, List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.api.src.dto.output import friend as dto_out
from app.backend.api.src.repositories import (
    friend as friends_repo,
    user as users_repo,
)
from app.backend.api.src.services import user as user_service


def _db(error: str, fn, *args):
    """Run a repository call, mapping driver errors to 424"""
    try:
        return fn(*args)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"{error}: {str(e)}"
        )


def public_user(db: Database, viewer_id: str, user: models.User, known: bool = False) -> dto_out.PublicUser:
    """Self, friends and wardrobe co-members see name + email (so do both
    sides of a friend request: `known`); others see the name of a public
    profile, and nothing of a private one."""
    close = (known or user.id == viewer_id or viewer_id in (user.friend_ids or [])
             or _db("Error checking wardrobes", friends_repo.share_a_wardrobe, db, viewer_id, user.id))
    if close:
        return dto_out.PublicUser(id=user.id, name=user.name, email=str(user.email))
    return dto_out.PublicUser(id=user.id, name=None if user.private_profile else user.name)


def public_users(db: Database, viewer_id: str, user_ids: List[str]) -> Dict[str, dto_out.PublicUser]:
    data = _db("Error retrieving users", friends_repo.find_users, db, list(set(user_ids)))
    return {u["_id"]: public_user(db, viewer_id, models.User(**u)) for u in data}


def _request_out(db: Database, viewer_id: str, r: models.FriendRequest) -> dto_out.FriendRequestOut:
    other = r.to_user_id if r.from_user_id == viewer_id else r.from_user_id
    return dto_out.FriendRequestOut(
        id=r.id, status=r.status, created_at=r.created_at,
        # the sender typed the email and, by asking, shows themselves
        user=public_user(db, viewer_id, user_service.get_user_by_id(db, other), known=True),
    )


def send_request(db: Database, user_id: str, email: str) -> dto_out.FriendRequestOut:
    """By exact email. If they already asked me, this accepts their request."""
    data = _db("Error retrieving user", users_repo.find_user_by_email, db, email)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user with that email")
    target = models.User(**data)
    if target.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't add yourself")
    if user_id in (target.friend_ids or []):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You're already friends")
    if _db("Error checking requests", friends_repo.find_pending_between, db, user_id, target.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already sent")
    theirs = _db("Error checking requests", friends_repo.find_pending_between, db, target.id, user_id)
    if theirs:
        return respond(db, user_id, theirs["_id"], accept=True)
    request = models.FriendRequest(from_user_id=user_id, to_user_id=target.id)
    _db("Error sending friend request", friends_repo.insert_request, db, request)
    return _request_out(db, user_id, request)


def list_requests(db: Database, user_id: str) -> dto_out.GetFriendRequests:
    data = _db("Error retrieving friend requests", friends_repo.find_pending_for, db, user_id)
    requests = [models.FriendRequest(**r) for r in data]
    return dto_out.GetFriendRequests(
        incoming=[_request_out(db, user_id, r) for r in requests if r.to_user_id == user_id],
        outgoing=[_request_out(db, user_id, r) for r in requests if r.from_user_id == user_id],
    )


def respond(db: Database, user_id: str, request_id: str, accept: bool) -> dto_out.FriendRequestOut:
    """Only the recipient answers a pending request"""
    data = _db("Error retrieving friend request", friends_repo.find_request_by_id, db, request_id)
    if not data or data["to_user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")
    request = models.FriendRequest(**data)
    if request.status != models.FriendRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already answered")
    new = models.FriendRequestStatus.ACCEPTED if accept else models.FriendRequestStatus.DECLINED
    _db("Error answering friend request", friends_repo.set_request_status, db, request_id, new.value)
    if accept:
        _db("Error adding friend", friends_repo.add_friends, db, request.from_user_id, request.to_user_id)
    request.status = new
    return _request_out(db, user_id, request)


def list_friends(db: Database, user_id: str) -> List[dto_out.PublicUser]:
    me = user_service.get_user_by_id(db, user_id)
    users = public_users(db, user_id, me.friend_ids or [])
    return sorted(users.values(), key=lambda u: (u.name or u.email or "").lower())


def unfriend(db: Database, user_id: str, friend_id: str) -> None:
    me = user_service.get_user_by_id(db, user_id)
    if friend_id not in (me.friend_ids or []):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in your friends")
    _db("Error removing friend", friends_repo.remove_friends, db, user_id, friend_id)
