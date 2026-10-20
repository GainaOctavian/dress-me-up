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
