from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import user as service
from app.backend.api.src.services import friend as friend_service
from app.backend.api.src.dto.input import user as dto_in
from app.backend.api.src.dto.output import user as dto_out

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", status_code=status.HTTP_200_OK, response_model=dto_out.GetUser)
async def get_current_user(db: DB, token: AUTH):
    """Get the currently authenticated user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    user = service.get_user_by_id(db, current_user_id)
    return dto_out.GetUser(user=user)


@router.get("/{user_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetPublicUser)
async def get_user_by_id(db: DB, token: AUTH, user_id: str):
    """Someone's public profile (email only for friends and wardrobe co-members)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    user = service.get_user_by_id(db, user_id)
    return dto_out.GetPublicUser(user=friend_service.public_user(db, current_user_id, user))


@router.post("/",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.GetUser)
async def create_user(db: DB, request: dto_in.CreateUser):
    """Create a new user"""
    user = service.create_user(db, request)
    return dto_out.GetUser(user=user)


@router.put("/me",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetUser)
async def update_current_user(db: DB, token: AUTH, request: dto_in.UpdateUser):
    """Update current user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    user = service.update_user(db, current_user_id, request)
    return dto_out.GetUser(user=user)


@router.delete("/me",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(db: DB, token: AUTH):
    """Delete current user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.delete_user(db, current_user_id)
