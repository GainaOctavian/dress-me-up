from typing import List, Optional

from pydantic import BaseModel, Field

from app.backend.common.db import models


class CreateItem(BaseModel):
    """DTO for creating a new item"""
    name: str = Field(min_length=1)
    wardrobe_ids: List[str] = Field(default_factory=list)
    categories: List[models.ItemCategory] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    image_asset_id: Optional[str] = None  # from POST /images/upload-url


class UpdateItem(BaseModel):
    """DTO for updating an item. Wardrobe membership has its own endpoints."""
    name: Optional[str] = Field(default=None, min_length=1)
    categories: Optional[List[models.ItemCategory]] = None
    tags: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    image_asset_id: Optional[str] = None  # replaces the current image
