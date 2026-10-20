from typing import Dict, List
from pydantic import BaseModel
from app.backend.common.db import models


class GetAllWardrobesByUser(BaseModel):
    """
    DTO for retrieving all wardrobes by a specific user
    """
    wardrobes: List[models.Wardrobe]
    item_counts: Dict[str, int] = {}  # wardrobe_id -> number of items


class GetWardrobe(BaseModel):
    """
    DTO for retrieving a wardrobe
    """
    wardrobe: models.Wardrobe
