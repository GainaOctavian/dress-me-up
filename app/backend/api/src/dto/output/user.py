from pydantic import BaseModel

from app.backend.common.db import models


class GetUser(BaseModel):
    """
    DTO for retrieving an user
    """
    user: models.User
