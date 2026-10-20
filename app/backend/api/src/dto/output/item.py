from typing import List, Optional

from pydantic import BaseModel

from app.backend.common.db import models


class ItemOut(models.Item):
    """Item plus a short-lived presigned URL for its image"""
    image_url: Optional[str] = None


class GetItem(BaseModel):
    """
    DTO for retrieving an item
    """
    item: ItemOut


class GetAllItems(BaseModel):
    """
    DTO for retrieving a list of items
    """
    items: List[ItemOut]
