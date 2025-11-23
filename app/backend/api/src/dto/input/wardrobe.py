from pydantic import BaseModel
from typing import Optional, Dict
from app.backend.common.db import models


class CreateWardrobe(BaseModel):
    """DTO for creating a new wardrobe"""
    name: str
    description: Optional[str] = None


class UpdateWardrobe(BaseModel):
    """DTO for updating wardrobe information"""
    name: Optional[str] = None
    description: Optional[str] = None
    roles: Optional[Dict[str, models.WardrobeRole]] = None
