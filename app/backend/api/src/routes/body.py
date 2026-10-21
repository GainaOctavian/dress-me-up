from starlette import status
from fastapi import APIRouter

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import body as service
from app.backend.api.src.dto.output import body as dto_out

router = APIRouter(prefix="/api/v1/bodies", tags=["bodies"])


@router.get("/",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetAllBodies)
async def get_bodies(db: DB, token: AUTH):
    """Built-in mannequins plus my own bodies, with presigned pose images"""
    current_user_id = auth_token.get_user_id_from_token(token)
    bodies = service.get_bodies(db, current_user_id)
    return dto_out.GetAllBodies(bodies=[service.to_out(b) for b in bodies])


@router.get("/{body_id}",
            status_code=status.HTTP_200_OK,
            response_model=dto_out.GetBody)
async def get_body(db: DB, token: AUTH, body_id: str):
    current_user_id = auth_token.get_user_id_from_token(token)
    return dto_out.GetBody(body=service.to_out(service.get_body(db, body_id, current_user_id)))
