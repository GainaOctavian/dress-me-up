from datetime import datetime
from typing import Optional

from starlette import status
from fastapi import APIRouter, Query

from app.backend.common.db.db import DB
from app.backend.api.src.auth import auth_token
from app.backend.api.src.auth.auth_token import AUTH
from app.backend.api.src.services import outfit as service
from app.backend.api.src.services import friend as friend_service
from app.backend.api.src.dto.output import outfit as dto_out

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=dto_out.GetFeed)
async def get_feed(db: DB, token: AUTH, before: Optional[datetime] = None,
                   limit: int = Query(20, ge=1, le=50)):
    """Outfits my friends shared, newest first. Next page: `before` = the
    last outfit's `created_at`."""
    current_user_id = auth_token.get_user_id_from_token(token)
    outfits = service.get_feed(db, current_user_id, before, limit)
    owners = friend_service.public_users(db, current_user_id, [o.owner_id for o in outfits])
    return dto_out.GetFeed(outfits=service.to_out(db, outfits), owners=owners)
