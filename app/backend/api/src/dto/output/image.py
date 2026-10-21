from typing import Dict, List, Optional

from pydantic import BaseModel

from app.backend.common.db import models


class UploadTarget(BaseModel):
    """
    Where and how to upload: POST multipart to `url` with `fields`
    plus the file as the last field named "file"
    """
    image_asset_id: str
    url: str
    fields: Dict[str, str]
    max_bytes: int


class ImageStatus(BaseModel):
    """Processing state + the worker's suggestions for the item form"""
    image_asset_id: str
    status: models.ImageAssetStatus
    image_url: str  # cutout when processed, else the original
    colors: List[str] = []
    tags: List[str] = []
    category: Optional[models.ItemCategory] = None
