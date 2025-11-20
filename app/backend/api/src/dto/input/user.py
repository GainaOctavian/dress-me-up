from pydantic import BaseModel, EmailStr, SecretStr
from typing import Optional, List


class CreateUser(BaseModel):
    """DTO for creating a new user"""
    email: EmailStr
    password: SecretStr
    name: Optional[str] = None
    private_profile: bool = True


class UpdateUser(BaseModel):
    """DTO for updating user information"""
    email: Optional[EmailStr] = None
    password: Optional[SecretStr] = None
    name: Optional[str] = None
    private_profile: Optional[bool] = None
    friend_ids: Optional[List[str]] = None
