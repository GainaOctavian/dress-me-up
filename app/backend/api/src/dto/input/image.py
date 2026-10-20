from typing import Literal

from pydantic import BaseModel


class RequestUpload(BaseModel):
    """DTO for asking where to upload a new image"""
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
