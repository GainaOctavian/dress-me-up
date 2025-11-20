from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.services import user as service
from app.backend.api.src.dto.input import user as dto_in
from app.backend.api.src.dto.output import user as dto_out

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllUsers)
async def get_users(db: DB):
    """Get all users"""
    users = service.get_users(db)
    return dto_out.GetAllUsers(users=users)


@router.get("/{user_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetUser)
async def get_user_by_id(db: DB, user_id: str):
    """Get user by ID"""
    user = service.get_user_by_id(db, user_id)
    return dto_out.GetUser(user=user)


@router.post("/",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.GetUser)
async def create_user(db: DB, request: dto_in.CreateUser):
    """Create a new user"""
    user = service.create_user(db, request)
    return dto_out.GetUser(user=user)


@router.put("/{user_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetUser)
async def update_user(db: DB, user_id: str, request: dto_in.UpdateUser):
    """Update current user"""
    user = service.update_user(db, user_id, request)
    return dto_out.GetUser(user=user)


@router.delete("/{user_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: DB, user_id: str,):
    """Delete current user"""
    service.delete_user(db, user_id)
