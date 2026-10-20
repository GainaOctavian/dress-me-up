from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, ClassVar

from pydantic import BaseModel, Field, EmailStr

from app.backend.common.stringproc.stringproc import generate_id


class User(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    email: EmailStr
    # never serialized in API responses; insert_user writes it explicitly
    hashed_password: str = Field(exclude=True)
    name: Optional[str] = None
    private_profile: bool = True
    friend_ids: Optional[List[str]] = Field(default_factory=list)

    COLLECTION_NAME: ClassVar[str] = "users"

    class Config:
        populate_by_name = True


class WardrobeRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Wardrobe(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    user_id: str
    name: str
    description: Optional[str] = None
    roles: Dict[str, WardrobeRole]  # Mapping user_ids to role in the wardrobe
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "wardrobes"

    class Config:
        populate_by_name = True


class ItemCategory(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"


class Item(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    name: str
    wardrobe_ids: List[str] = Field(default_factory=list)
    categories: Optional[List[ItemCategory]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    colors: Optional[List[str]] = Field(default_factory=list)
    image_asset_id: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "items"

    class Config:
        populate_by_name = True


class Coordinates(BaseModel):
    x: float
    y: float


class CropSettings(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Transform(BaseModel):
    """Normalized to the outfit canvas: translate is the item center in 0..1
    of canvas width/height, scale is relative to a base size of 40% canvas
    width. Keeps outfits identical across screen sizes."""
    translate: Coordinates
    scale: Coordinates
    rotation: float = 0  # in degrees
    flip_horizontal: bool = False
    flip_vertical: bool = False
    crop: Optional[CropSettings] = None


class OutfitItem(BaseModel):
    item_id: str
    z_index: int  # layering order
    transform: Transform
    visible: bool = True
    opacity: float = Field(1.0, ge=0.0, le=1.0)


class Outfit(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    wardrobe_id: Optional[str] = None
    name: str
    items: List[OutfitItem] = Field(default_factory=list)
    image_asset_id: Optional[str] = None  # preview image
    shared: bool = False  # only shared outfits appear in friends' feed

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "outfits"

    class Config:
        populate_by_name = True


class ImageAssetStatus(str, Enum):
    PENDING_UPLOAD = "pending_upload"
    READY = "ready"            # original uploaded, item created
    PROCESSING = "processing"  # worker picked it up
    PROCESSED = "processed"    # background removed, processed_s3_key set
    FAILED = "failed"


class ImageAsset(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    # store S3 keys, not URLs: URLs are presigned per request and expire
    s3_key: str
    processed_s3_key: Optional[str] = None
    status: ImageAssetStatus = ImageAssetStatus.PENDING_UPLOAD
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "image_assets"

    class Config:
        populate_by_name = True
