from pydantic import BaseModel

from app.backend.common.db import models
from app.backend.api.src.dto.output.friend import PublicUser


class GetPublicUser(BaseModel):
    """Someone else's profile, as much as the caller may see"""
    user: PublicUser


class GetUser(BaseModel):
    """
    DTO for retrieving an user
    """
    user: models.User
