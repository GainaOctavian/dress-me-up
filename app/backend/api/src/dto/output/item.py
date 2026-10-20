from typing import List

from pydantic import BaseModel

from app.backend.common.db import models


class GetItem(BaseModel):
    """
    DTO for retrieving an item
    """
    item: models.Item


class GetAllItems(BaseModel):
    """
    DTO for retrieving a list of items
    """
    items: List[models.Item]
