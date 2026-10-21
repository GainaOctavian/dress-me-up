from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import image as service
from app.backend.api.src.dto.input import image as dto_in
from app.backend.api.src.dto.output import image as dto_out

router = APIRouter(prefix="/api/v1/images", tags=["images"])


@router.post("/upload-url",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.UploadTarget)
async def request_upload(db: DB, token: AUTH, request: dto_in.RequestUpload):
    """Get a presigned POST to upload an image directly to storage.
    Then pass the returned image_asset_id when creating/updating an item."""
    current_user_id = auth_token.get_user_id_from_token(token)
    return service.request_upload(db, current_user_id, request.mime_type)


def _status(asset) -> dto_out.ImageStatus:
    meta = asset.metadata or {}
    return dto_out.ImageStatus(
        image_asset_id=asset.id,
        status=asset.status,
        image_url=service.preview_url(asset),
        colors=meta.get("colors", []),
        tags=meta.get("tags", []),
        category=meta.get("category"),
        subcategory=meta.get("subcategory"),
    )


@router.post("/{image_asset_id}/uploaded",
             status_code=status.HTTP_200_OK,
             response_model=dto_out.ImageStatus)
async def mark_uploaded(db: DB, token: AUTH, image_asset_id: str):
    """Call after the upload to storage: starts background removal and
    color/tag detection. Poll GET /images/{id} for the result."""
    current_user_id = auth_token.get_user_id_from_token(token)
    return _status(service.mark_uploaded(db, image_asset_id, current_user_id))


@router.get("/{image_asset_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.ImageStatus)
async def get_image_status(db: DB, token: AUTH, image_asset_id: str):
    """Processing status and suggestions (colors, tags, category)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    return _status(service.get_own_asset(db, image_asset_id, current_user_id))
