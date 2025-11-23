import datetime
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, ClassVar, NamedTuple

from pydantic import BaseModel, Field, EmailStr

from app.backend.common.stringproc.stringproc import generate_id


class User(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    email: EmailStr
    hashed_password: str
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


class Item(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    name: str
    wardrobe_ids: List[str] = []
    categories: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    colors: Optional[List[str]] = Field(default_factory=list)
    image_asset_id: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "items"

    class Config:
        populate_by_name = True


class Coordinates(NamedTuple):
    x: float
    y: float


class CropSettings(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Transform(BaseModel):
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
    visibility: bool = True
    opacity: float = 1.0  # 0.0 to 1.0


class Outfit(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    wardrobe_id: Optional[str] = None
    name: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "outfits"

    class Config:
        populate_by_name = True


class ImageAsset(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    s3_url: str  # URL to the stored image
    mime_type: str
    width: int
    height: int
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "image_assets"

    class Config:
        populate_by_name = True
