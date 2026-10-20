from pydantic import BaseModel, EmailStr
from typing import Optional
from app.backend.common.db import models


class CreateWardrobe(BaseModel):
    """DTO for creating a new wardrobe"""
    name: str
    description: Optional[str] = None


class UpdateWardrobe(BaseModel):
    """DTO for updating wardrobe information"""
    name: Optional[str] = None
    description: Optional[str] = None


class AddUserToWardrobe(BaseModel):
    """DTO for adding a user to a wardrobe with a specific role"""
    user_id: str
    role: models.WardrobeRole


class AddUserByEmailToWardrobe(BaseModel):
    """DTO for adding a user to a wardrobe by email with a specific role"""
    email: EmailStr
    role: models.WardrobeRole
