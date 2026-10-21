from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import outfit as service
from app.backend.api.src.dto.input import outfit as dto_in
from app.backend.api.src.dto.output import outfit as dto_out

router = APIRouter(prefix="/api/v1/outfits", tags=["outfits"])


@router.get("/me",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllOutfits)
async def get_my_outfits(db: DB, token: AUTH):
    """My outfits plus all outfits of wardrobes I'm a member of, newest first"""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfits = service.get_visible_outfits(db, current_user_id)
    return dto_out.GetAllOutfits(outfits=service.to_out(db, outfits))


@router.get("/{outfit_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetOutfit)
async def get_outfit(db: DB, token: AUTH, outfit_id: str):
    """Get outfit by ID (owner or member of its wardrobe)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfit = service.get_outfit(db, outfit_id, current_user_id)
    return dto_out.GetOutfit(outfit=service.to_out(db, [outfit])[0])


@router.post("/",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.GetOutfit)
async def create_outfit(db: DB, token: AUTH, request: dto_in.CreateOutfit):
    """Create an outfit (in a wardrobe you can edit, or personal)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfit = service.create_outfit(db, current_user_id, request)
    return dto_out.GetOutfit(outfit=service.to_out(db, [outfit])[0])


@router.put("/{outfit_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetOutfit)
async def update_outfit(
        db: DB,
        token: AUTH,
        outfit_id: str,
        request: dto_in.UpdateOutfit
):
    """Update outfit name and/or replace its items"""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfit = service.update_outfit(db, outfit_id, current_user_id, request)
    return dto_out.GetOutfit(outfit=service.to_out(db, [outfit])[0])


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(db: DB, token: AUTH, outfit_id: str):
    """Delete outfit"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.delete_outfit(db, outfit_id, current_user_id)
    return None
