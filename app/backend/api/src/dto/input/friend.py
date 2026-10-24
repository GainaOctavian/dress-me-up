from pydantic import BaseModel, EmailStr


class SendFriendRequest(BaseModel):
    """Friends are found by exact email only (no user search)"""
    email: EmailStr
