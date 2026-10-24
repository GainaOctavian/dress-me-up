from typing import List, Optional

from pydantic import BaseModel, Field

from app.backend.common.db import models


class CreateOutfit(BaseModel):
    """DTO for creating an outfit. wardrobe_id=None makes it personal."""
    name: str = Field(min_length=1)
    wardrobe_id: Optional[str] = None
    items: List[models.OutfitItem] = Field(min_length=1)
    body_id: Optional[str] = None   # dressed on this body (plan 12/13)
    pose_id: Optional[str] = None
    shared: bool = False  # in my friends' feed (plan 08)


class UpdateOutfit(BaseModel):
    """DTO for updating an outfit. `items` replaces the whole list
    (the editor always saves the full canvas)."""
    name: Optional[str] = Field(default=None, min_length=1)
    items: Optional[List[models.OutfitItem]] = Field(default=None, min_length=1)
    body_id: Optional[str] = None
    pose_id: Optional[str] = None
    shared: Optional[bool] = None  # owner only
