from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import wardrobe as service
from app.backend.api.src.dto.input import wardrobe as dto_in
from app.backend.api.src.dto.output import wardrobe as dto_out

router = APIRouter(prefix="/api/v1/wardrobes", tags=["wardrobes"])


@router.get("/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobes)
async def get_wardrobes(db: DB):
    """Get all wardrobes"""
    wardrobes = service.get_wardrobes(db)
    return dto_out.GetAllWardrobes(wardrobes=wardrobes)


@router.get("/user/me",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobesByUser)
async def get_wardrobes_by_current_user(db: DB, token: AUTH):
    """Get wardrobes for the currently authenticated user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobes = service.get_wardrobes_by_user_id(db, current_user_id)
    return dto_out.GetAllWardrobesByUser(wardrobes=wardrobes)


@router.get("/{wardrobe_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetWardrobe)
async def get_wardrobe_by_id(db: DB, wardrobe_id: str):
    """Get wardrobe by ID"""
    wardrobe = service.get_wardrobe_by_id(db, wardrobe_id)
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.get("/user/me/roles/{role}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobesByUser)
async def get_wardrobes_by_current_user_role(db: DB, token: AUTH, role: str):
    """Get wardrobes for the currently authenticated user by role"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobes = service.get_wardrobes_by_user_role(db, current_user_id, role)
    return dto_out.GetAllWardrobesByUser(wardrobes=wardrobes)


@router.post("/",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.GetWardrobe)
async def create_wardrobe(db: DB, token: AUTH, request: dto_in.CreateWardrobe):
    """Create a new wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.create_wardrobe(db, current_user_id, request)
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.put("/{wardrobe_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetWardrobe)
async def update_wardrobe(db: DB, token:AUTH, wardrobe_id: str, request: dto_in.UpdateWardrobe):
    """Update wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.update_wardrobe(
        db, wardrobe_id, current_user_id, request
    )
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.delete("/{wardrobe_id}",
                status_code=status.HTTP_204_NO_CONTENT)
async def delete_wardrobe(db: DB, token: AUTH, wardrobe_id: str):
    """Delete wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.delete_wardrobe(db, wardrobe_id, current_user_id)
    return None
