from typing import Dict, List, Optional

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.common.storage import s3
from app.backend.api.src.repositories import image_asset as assets_repo

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _db(error: str, fn, *args):
    """Run a repository/storage call, mapping failures to 424"""
    try:
        return fn(*args)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"{error}: {str(e)}"
        )


def request_upload(db: Database, user_id: str, mime_type: str) -> dict:
    """Create a pending ImageAsset and a presigned POST to upload it to"""
    asset = models.ImageAsset(owner_id=user_id, s3_key="", mime_type=mime_type)
    asset.s3_key = f"originals/{user_id}/{asset.id}.{EXTENSIONS[mime_type]}"
    _db("Error creating image asset", assets_repo.insert_asset, db, asset)
    target = _db(
        "Error signing upload URL",
        s3.presigned_post, asset.s3_key, mime_type, MAX_UPLOAD_BYTES
    )
    return {
        "image_asset_id": asset.id,
        "url": target["url"],
        "fields": target["fields"],
        "max_bytes": MAX_UPLOAD_BYTES,
    }


def claim_uploaded_asset(
        db: Database,
        asset_id: str,
        user_id: str
) -> models.ImageAsset:
    """Validate an asset the user wants to attach to an item, and mark it
    ready. Only the uploader can use it, once, after the upload landed."""
    data = _db(
        "Error retrieving image asset",
        assets_repo.find_asset_by_id, db, asset_id
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {asset_id} not found"
        )
    asset = models.ImageAsset(**data)
    if asset.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only use images you uploaded"
        )
    if asset.status != models.ImageAssetStatus.PENDING_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This image is already attached to an item"
        )
    if not _db("Error checking upload", s3.head, asset.s3_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image hasn't been uploaded yet"
        )
    _db(
        "Error updating image asset",
        assets_repo.update_asset_by_id, db, asset_id,
        {"status": models.ImageAssetStatus.READY}
    )
    asset.status = models.ImageAssetStatus.READY
    return asset


def image_urls(db: Database, asset_ids: List[str]) -> Dict[str, str]:
    """asset_id -> presigned GET (processed image when there is one)"""
    if not asset_ids:
        return {}
    data = _db(
        "Error retrieving images",
        assets_repo.find_assets_by_ids, db, asset_ids
    )
    urls = {}
    for a in data:
        key = a.get("processed_s3_key") or a["s3_key"]
        urls[a["_id"]] = s3.presigned_get(key)
    return urls


def delete_asset(db: Database, asset_id: Optional[str]) -> None:
    """Best effort: drop an image nobody uses anymore (S3 objects + doc).
    A failure leaves an orphan, never blocks the caller."""
    if not asset_id:
        return
    try:
        data = assets_repo.find_asset_by_id(db, asset_id)
        if data:
            for key in (data.get("s3_key"), data.get("processed_s3_key")):
                if key:
                    s3.delete(key)
        assets_repo.delete_asset_by_id(db, asset_id)
    except Exception:
        pass  # ponytail: orphans get swept by the worker cleanup (plan 04)
