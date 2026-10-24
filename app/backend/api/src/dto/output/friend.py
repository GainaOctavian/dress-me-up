from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.backend.common.db import models


class PublicUser(BaseModel):
    """What one user may see of another (services/friend.public_user):
    email only for themselves, friends and wardrobe co-members; a private
    profile shows nothing else to strangers."""
    id: str = Field(alias="_id")
    name: Optional[str] = None
    email: Optional[str] = None

    class Config:
        populate_by_name = True


class FriendRequestOut(BaseModel):
    id: str = Field(alias="_id")
    status: models.FriendRequestStatus
    created_at: datetime
    user: PublicUser  # the other side of the request

    class Config:
        populate_by_name = True


class GetFriendRequests(BaseModel):
    incoming: List[FriendRequestOut]
    outgoing: List[FriendRequestOut]


class GetFriendRequest(BaseModel):
    request: FriendRequestOut


class GetFriends(BaseModel):
    friends: List[PublicUser]
