from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import item as service
from app.backend.api.src.dto.input import item as dto_in
from app.backend.api.src.dto.output import item as dto_out

router = APIRouter(prefix="/api/v1/items", tags=["items"])


@router.get("/me",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllItems)
async def get_my_items(db: DB, token: AUTH):
    """Get items owned by the currently authenticated user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    items = service.get_items_by_owner(db, current_user_id)
    return dto_out.GetAllItems(items=service.to_out(db, items))


@router.get("/{item_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetItem)
async def get_item(db: DB, token: AUTH, item_id: str):
    """Get item by ID (owner or member of one of its wardrobes)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    item = service.get_item(db, item_id, current_user_id)
    return dto_out.GetItem(item=service.to_out(db, [item])[0])


@router.post("/",
             status_code=status.HTTP_201_CREATED,
             response_model=dto_out.GetItem)
async def create_item(db: DB, token: AUTH, request: dto_in.CreateItem):
    """Create a new item"""
    current_user_id = auth_token.get_user_id_from_token(token)
    item = service.create_item(db, current_user_id, request)
    return dto_out.GetItem(item=service.to_out(db, [item])[0])


@router.put("/{item_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetItem)
async def update_item(
        db: DB,
        token: AUTH,
        item_id: str,
        request: dto_in.UpdateItem
):
    """Update item"""
    current_user_id = auth_token.get_user_id_from_token(token)
    item = service.update_item(db, item_id, current_user_id, request)
    return dto_out.GetItem(item=service.to_out(db, [item])[0])


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(db: DB, token: AUTH, item_id: str):
    """Delete item"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.delete_item(db, item_id, current_user_id)
    return None
