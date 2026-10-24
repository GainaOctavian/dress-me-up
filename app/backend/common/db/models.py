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


class FriendRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class FriendRequest(BaseModel):
    """Plan 08: a pending friendship. Accepting adds each user to the
    other's `friend_ids` (the read path)."""
    id: str = Field(default_factory=generate_id, alias="_id")
    from_user_id: str
    to_user_id: str
    status: FriendRequestStatus = FriendRequestStatus.PENDING
    created_at: UtcDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    COLLECTION_NAME: ClassVar[str] = "friend_requests"

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


class FitAdjust(BaseModel):
    """The user's tweak on top of the auto-fit (plan 13). Offsets are in body
    heights, so the tweak carries over when the outfit switches body."""
    dx: float = 0.0
    dy: float = 0.0
    scale: float = Field(1.0, gt=0.1, le=5.0)
    rotation: float = 0.0  # degrees


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
    fit_adjust: Optional[FitAdjust] = None  # dressed outfits only (plan 13)


class Outfit(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: str
    wardrobe_id: Optional[str] = None
    name: str
    items: List[OutfitItem] = Field(default_factory=list)
    image_asset_id: Optional[str] = None  # preview image
    shared: bool = False  # only shared outfits appear in friends' feed
    # plan 12/13: dressed on this body/pose; None = free-canvas outfit
    body_id: Optional[str] = None
    pose_id: Optional[str] = None
    render: Optional["OutfitRender"] = None  # 3D render (plan 19), dressed only

    created_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "outfits"

    class Config:
        populate_by_name = True


class OutfitRender(BaseModel):
    """The server's 3D render of a dressed outfit (plan 19). Every save bumps
    `version`; the renderer only stores a result for the current version."""
    status: str = "queued"  # queued | done | failed
    version: int = 0
    image_key: Optional[str] = None  # renders/<outfit>/<pose>-<sha10>.webp
    model_key: Optional[str] = None  # same, .glb: the dressed scene for the 3D viewer
    error: Optional[str] = None


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
    plain_s3_key: Optional[str] = None  # cutout without glow, same canvas (plan 13)
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


class BodyKind(str, Enum):
    MANNEQUIN = "mannequin"
    USER = "user"


class BodyPose(BaseModel):
    """One rendered pose: transparent PNG + named keypoints, normalized 0..1
    in the image (x right, y down). left/right = the body's own left/right."""
    image_key: str
    size: List[int]  # [width, height] in px
    keypoints: Dict[str, List[float]]
    # user bodies (plan 16): Anny pose params (.npy) the 3D renderer re-poses
    # with; mannequins keep theirs in the renderer image
    params_key: Optional[str] = None


class Body(BaseModel):
    """A body garments are fitted onto (plan 12): built-in mannequins
    (owner_id None, fixed ids) and the user's own body (plan 16a: one per
    user, built by the renderer from the measurements they typed)."""
    id: str = Field(default_factory=generate_id, alias="_id")
    owner_id: Optional[str] = None
    kind: BodyKind = BodyKind.MANNEQUIN
    gender: str  # male | female
    format: int = 1
    poses: Dict[str, BodyPose]
    measurements_cm: Dict[str, float] = Field(default_factory=dict)  # measured on the built body
    # user bodies: what they typed (height_cm, weight_kg, chest/waist/hips_cm),
    # the build's state and the Anny phenotype fitted to it
    input_cm: Dict[str, float] = Field(default_factory=dict)
    status: str = "ready"  # building | ready | failed
    error: Optional[str] = None
    phenotype: Dict[str, float] = Field(default_factory=dict)
    created_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    COLLECTION_NAME: ClassVar[str] = "bodies"

    class Config:
        populate_by_name = True


# Outfit refers to OutfitRender, defined after it
Outfit.model_rebuild()
