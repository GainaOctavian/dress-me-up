from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.backend.common.db import models


class ItemOut(models.Item):
    """Item plus a short-lived presigned URL for its image"""
    image_url: Optional[str] = None
    # pending_upload/ready/processing/processed/failed; None without image
    image_status: Optional[str] = None
    image_size: Optional[List[int]] = None  # [w, h] of the processed image
    fit: Optional[Dict[str, Any]] = None  # garment anchors (worker, plan 13)
    plain_url: Optional[str] = None  # cutout without glow, for the mannequin


class GetItem(BaseModel):
    """
    DTO for retrieving an item
    """
    item: ItemOut


class GetAllItems(BaseModel):
    """
    DTO for retrieving a list of items
    """
    items: List[ItemOut]
