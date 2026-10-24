from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import friend as service
from app.backend.api.src.dto.input import friend as dto_in
from app.backend.api.src.dto.output import friend as dto_out

router = APIRouter(prefix="/api/v1/friends", tags=["friends"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=dto_out.GetFriends)
async def get_friends(db: DB, token: AUTH):
    """My friends, by name"""
    current_user_id = auth_token.get_user_id_from_token(token)
    return dto_out.GetFriends(friends=service.list_friends(db, current_user_id))


@router.get("/requests", status_code=status.HTTP_200_OK, response_model=dto_out.GetFriendRequests)
async def get_requests(db: DB, token: AUTH):
    """Pending requests: incoming (to answer) and outgoing (sent)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    return service.list_requests(db, current_user_id)


@router.post("/requests", status_code=status.HTTP_201_CREATED, response_model=dto_out.GetFriendRequest)
async def send_request(db: DB, token: AUTH, request: dto_in.SendFriendRequest):
    """Ask someone by exact email (accepts their request if they already asked)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    return dto_out.GetFriendRequest(request=service.send_request(db, current_user_id, str(request.email)))


@router.post("/requests/{request_id}/accept", status_code=status.HTTP_200_OK,
             response_model=dto_out.GetFriendRequest)
async def accept_request(db: DB, token: AUTH, request_id: str):
    current_user_id = auth_token.get_user_id_from_token(token)
    return dto_out.GetFriendRequest(request=service.respond(db, current_user_id, request_id, accept=True))


@router.post("/requests/{request_id}/decline", status_code=status.HTTP_200_OK,
             response_model=dto_out.GetFriendRequest)
async def decline_request(db: DB, token: AUTH, request_id: str):
    current_user_id = auth_token.get_user_id_from_token(token)
    return dto_out.GetFriendRequest(request=service.respond(db, current_user_id, request_id, accept=False))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfriend(db: DB, token: AUTH, user_id: str):
    """Remove a friend (both sides)"""
    current_user_id = auth_token.get_user_id_from_token(token)
    service.unfriend(db, current_user_id, user_id)
    return None
