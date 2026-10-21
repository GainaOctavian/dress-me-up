import logging
from typing import Dict, List, Optional

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.storage import s3
from app.backend.api.src.repositories import image_asset as assets_repo

logger = logging.getLogger(__name__)

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


def _get_own_asset(db: Database, asset_id: str, user_id: str) -> models.ImageAsset:
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
    return asset


def enqueue_processing(asset_id: str) -> None:
    """Ask the worker to cut out the image and suggest colors/tags.
    Never fails the request: if RabbitMQ is down the worker's sweeper
    re-queues `ready` assets later."""
    try:
        queue.publish(queue.IMAGE_QUEUE, {"image_asset_id": asset_id})
    except Exception as e:
        logger.warning("Could not queue image %s: %s", asset_id, e)


def _mark_ready(db: Database, asset: models.ImageAsset) -> None:
    """pending_upload -> ready (+ queued), after checking the object exists"""
    if asset.status != models.ImageAssetStatus.PENDING_UPLOAD:
        return
    if not _db("Error checking upload", s3.head, asset.s3_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image hasn't been uploaded yet"
        )
    _db(
        "Error updating image asset",
        assets_repo.update_asset_by_id, db, asset.id,
        {"status": models.ImageAssetStatus.READY}
    )
    asset.status = models.ImageAssetStatus.READY
    enqueue_processing(asset.id)


def mark_uploaded(db: Database, asset_id: str, user_id: str) -> models.ImageAsset:
    """Client finished the S3 upload: start processing right away, so the
    cutout and suggestions are ready while the user fills in the form."""
    asset = _get_own_asset(db, asset_id, user_id)
    _mark_ready(db, asset)
    return asset


def get_own_asset(db: Database, asset_id: str, user_id: str) -> models.ImageAsset:
    return _get_own_asset(db, asset_id, user_id)


def preview_url(asset: models.ImageAsset) -> str:
    return s3.presigned_get(asset.processed_s3_key or asset.s3_key)


def claim_uploaded_asset(
        db: Database,
        asset_id: str,
        user_id: str
) -> models.ImageAsset:
    """Validate an asset the user wants to attach to an item and mark it
    used. Only the uploader can use it, once, after the upload landed."""
    asset = _get_own_asset(db, asset_id, user_id)
    if asset.attached:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This image is already attached to an item"
        )
    _mark_ready(db, asset)  # clients that skipped /uploaded
    _db(
        "Error updating image asset",
        assets_repo.update_asset_by_id, db, asset_id, {"attached": True}
    )
    asset.attached = True
    return asset


def image_statuses(db: Database, asset_ids: List[str]) -> Dict[str, str]:
    """asset_id -> status, for showing "processing" on items"""
    if not asset_ids:
        return {}
    data = _db(
        "Error retrieving images",
        assets_repo.find_assets_by_ids, db, asset_ids
    )
    return {a["_id"]: a.get("status") for a in data}


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
