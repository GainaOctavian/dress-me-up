from enum import Enum
from datetime import datetime, timezone
from typing import Annotated, Any, Optional, List, Dict, ClassVar

from pydantic import AfterValidator, BaseModel, Field, EmailStr

from app.backend.common.stringproc.stringproc import generate_id
from app.backend.common.layering import Subcategory

# Mongo returns naive datetimes (UTC). Mark them UTC so the API sends an
# explicit offset; otherwise clients read them as local time.
UtcDatetime = Annotated[
    datetime,
    AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=timezone.utc)),
]


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
    created_at: UtcDatetime = Field(
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
    # precise type (t_shirt, blazer, tights, ...): drives slot + layer
    # order, see common/layering.py
    subcategory: Optional[Subcategory] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    colors: Optional[List[str]] = Field(default_factory=list)
    image_asset_id: Optional[str] = None
    created_at: UtcDatetime = Field(
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
    # layering switches (plan 11); None = the subcategory's default
    tucked: Optional[bool] = None      # tops: tucked into the trousers
    into_shoes: bool = False           # trousers tucked into boots
    open: Optional[bool] = None        # jackets/coats worn open (plan 15)
    layer_offset: int = 0              # manual reorder within the layer band


class Outfit(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    wardrobe_id: Optional[str] = None
    name: str
    items: List[OutfitItem] = Field(default_factory=list)
    image_asset_id: Optional[str] = None  # preview image
    shared: bool = False  # only shared outfits appear in friends' feed

    created_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "outfits"

    class Config:
        populate_by_name = True


class ImageAssetStatus(str, Enum):
    PENDING_UPLOAD = "pending_upload"
    READY = "ready"            # original uploaded, queued for processing
    PROCESSING = "processing"  # worker picked it up
    PROCESSED = "processed"    # cutout in processed_s3_key, suggestions in metadata
    FAILED = "failed"          # gave up; the original is still used


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
    # set by the worker: colors, tags, category (suggestions), model info,
    # processing_started_at; values aren't all strings
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    attached: bool = False  # used by an item/outfit; an asset is used once
    uploaded_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "image_assets"

    class Config:
        populate_by_name = True
