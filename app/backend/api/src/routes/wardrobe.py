from starlette import status
from fastapi import APIRouter

from app.backend.common.db import models
from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import wardrobe as service
from app.backend.api.src.services import item as item_service
from app.backend.api.src.services import outfit as outfit_service
from app.backend.api.src.dto.input import wardrobe as dto_in
from app.backend.api.src.dto.output import wardrobe as dto_out
from app.backend.api.src.dto.output import item as item_dto_out
from app.backend.api.src.dto.output import outfit as outfit_dto_out

router = APIRouter(prefix="/api/v1/wardrobes", tags=["wardrobes"])


def _list_response(db, wardrobes) -> dto_out.GetAllWardrobesByUser:
    return dto_out.GetAllWardrobesByUser(
        wardrobes=wardrobes,
        item_counts=service.get_item_counts(db, wardrobes),
    )


@router.get("/user/me",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobesByUser)
async def get_owned_wardrobes_by_current_user(db: DB, token: AUTH):
    """Get wardrobes owned by the currently authenticated user"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobes = service.get_wardrobes_by_user(
        db, current_user_id, models.WardrobeRole.OWNER
    )
    return _list_response(db, wardrobes)


@router.get("/{wardrobe_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetWardrobe)
async def get_wardrobe_by_id(db: DB, token: AUTH, wardrobe_id: str):
    """Get wardrobe by ID (members only)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.get_wardrobe_for_member(db, wardrobe_id, current_user_id)
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.get("/user/me/roles/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobesByUser)
async def get_wardrobes_by_current_user(db: DB, token: AUTH):
    """Get wardrobes for the currently authenticated user by any role"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobes = service.get_wardrobes_by_user(db, current_user_id)
    return _list_response(db, wardrobes)


@router.get("/user/me/roles/{role}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllWardrobesByUser)
async def get_wardrobes_by_current_user_role(
        db: DB,
        token: AUTH,
        role: models.WardrobeRole
):
    """Get wardrobes for the currently authenticated user by role"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobes = service.get_wardrobes_by_user(db, current_user_id, role)
    return _list_response(db, wardrobes)


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
async def update_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        request: dto_in.UpdateWardrobe
):
    """Update wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.update_wardrobe(
        db, wardrobe_id, current_user_id, request
    )
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.put("/{wardrobe_id}/roles/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetWardrobe)
async def add_user_role_to_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        request: dto_in.AddUserToWardrobe
):
    """Add user to wardrobe with specific role"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.add_user_to_wardrobe(
        db, wardrobe_id, current_user_id, request
    )
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.put("/{wardrobe_id}/roles/by-email/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetWardrobe)
async def add_user_by_email_role_to_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        request: dto_in.AddUserByEmailToWardrobe
):
    """Add user to wardrobe by email with specific role"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.add_user_by_email_to_wardrobe(
        db, wardrobe_id, current_user_id, request
    )
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.delete("/{wardrobe_id}/roles/{member_id}",
               status_code=status.HTTP_200_OK,
               response_model=dto_out.GetWardrobe)
async def remove_user_role_from_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        member_id: str
):
    """Remove user from wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    wardrobe = service.remove_user_from_wardrobe(
        db, wardrobe_id, current_user_id, member_id
    )
    return dto_out.GetWardrobe(wardrobe=wardrobe)


@router.get("/{wardrobe_id}/items",
            status_code=status.HTTP_200_OK,
            response_model=item_dto_out.GetAllItems)
async def get_wardrobe_items(db: DB, token: AUTH, wardrobe_id: str):
    """Get items in a wardrobe (members only)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    items = item_service.get_wardrobe_items(db, wardrobe_id, current_user_id)
    return item_dto_out.GetAllItems(items=item_service.to_out(db, items))


@router.get("/{wardrobe_id}/outfits",
            status_code=status.HTTP_200_OK,
            response_model=outfit_dto_out.GetAllOutfits)
async def get_wardrobe_outfits(db: DB, token: AUTH, wardrobe_id: str):
    """Get outfits in a wardrobe (members only)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfits = outfit_service.get_wardrobe_outfits(db, wardrobe_id, current_user_id)
    return outfit_dto_out.GetAllOutfits(
        outfits=outfit_service.to_out(db, outfits)
    )


@router.put("/{wardrobe_id}/items/{item_id}",
            status_code=status.HTTP_200_OK,
            response_model=item_dto_out.GetItem)
async def add_item_to_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        item_id: str
):
    """Add one of your items to a wardrobe (editor or owner)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    item = item_service.add_item_to_wardrobe(
        db, wardrobe_id, item_id, current_user_id
    )
    return item_dto_out.GetItem(item=item_service.to_out(db, [item])[0])


@router.delete("/{wardrobe_id}/items/{item_id}",
               status_code=status.HTTP_200_OK,
               response_model=item_dto_out.GetItem)
async def remove_item_from_wardrobe(
        db: DB,
        token: AUTH,
        wardrobe_id: str,
        item_id: str
):
    """Remove an item from a wardrobe; the item itself is kept"""
    current_user_id = auth_token.get_user_id_from_token(token)
    item = item_service.remove_item_from_wardrobe(
        db, wardrobe_id, item_id, current_user_id
    )
    return item_dto_out.GetItem(item=item_service.to_out(db, [item])[0])


@router.post("/{wardrobe_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_wardrobe(db: DB, token: AUTH, wardrobe_id: str):
    """Leave a wardrobe (remove your own role)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.leave_wardrobe(db, wardrobe_id, current_user_id)
    return None


@router.delete("/{wardrobe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wardrobe(db: DB, token: AUTH, wardrobe_id: str):
    """Delete wardrobe"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.delete_wardrobe(db, wardrobe_id, current_user_id)
    return None
