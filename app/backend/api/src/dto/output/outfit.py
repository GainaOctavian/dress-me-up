from typing import Dict, List, Optional

from pydantic import BaseModel

from app.backend.common.db import models


class OutfitItemRef(BaseModel):
    """What a client needs to draw an outfit item without fetching it"""
    name: str
    categories: List[models.ItemCategory] = []
    image_url: Optional[str] = None


class OutfitOut(models.Outfit):
    preview_url: Optional[str] = None
    # item_id -> summary; items deleted since are simply missing
    item_refs: Dict[str, OutfitItemRef] = {}


class GetOutfit(BaseModel):
    """
    DTO for retrieving an outfit
    """
    outfit: OutfitOut


class GetAllOutfits(BaseModel):
    """
    DTO for retrieving a list of outfits
    """
    outfits: List[OutfitOut]
