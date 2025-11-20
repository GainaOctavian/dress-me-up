from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from fastapi import APIRouter, Depends

from app.backend.common.db.db import DB
from app.backend.api.src.services import auth as service
from app.backend.api.src.dto.output import auth as dto_out


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token", status_code=status.HTTP_200_OK, response_model=dto_out.Token)
async def get_login_token(db: DB, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return access token"""
    token = service.get_login_token(db, form_data.username, form_data.password)
    return dto_out.Token(access_token=token)
