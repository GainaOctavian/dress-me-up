from typing import List
from pydantic import BaseModel
from app.backend.common.db import models


class GetAllWardrobesByUser(BaseModel):
    """
    DTO for retrieving all wardrobes by a specific user
    """
    wardrobes: List[models.Wardrobe]


class GetWardrobe(BaseModel):
    """
    DTO for retrieving a wardrobe
    """
    wardrobe: models.Wardrobe
