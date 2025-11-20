from typing import List

from pydantic import BaseModel

from app.backend.common.db import models


class GetAllUsers(BaseModel):
    """
    DTO for retrieving all users
    """
    users: List[models.User]


class GetUser(BaseModel):
    """
    DTO for retrieving an user
    """
    user: models.User
