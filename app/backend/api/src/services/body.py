from typing import List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.common.storage import s3
from app.backend.api.src.dto.output import body as dto_out
from app.backend.api.src.repositories import body as bodies_repo


def _db(error: str, fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"{error}: {str(e)}"
        )


def to_out(body: models.Body) -> dto_out.BodyOut:
    return dto_out.BodyOut(
        id=body.id,
        kind=body.kind,
        gender=body.gender,
        format=body.format,
        poses={
            name: dto_out.BodyPoseOut(**pose.model_dump(), image_url=s3.presigned_get(pose.image_key))
            for name, pose in body.poses.items()
        },
        measurements_cm=body.measurements_cm,
    )


def get_bodies(db: Database, user_id: str) -> List[models.Body]:
    data = _db("Error retrieving bodies", bodies_repo.find_visible_bodies, db, user_id)
    return [models.Body(**b) for b in data]


def get_body(db: Database, body_id: str, user_id: str) -> models.Body:
    data = _db("Error retrieving body", bodies_repo.find_body_by_id, db, body_id)
    # someone else's personal body is reported as missing, not forbidden
    if not data or data.get("owner_id") not in (None, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Body {body_id} not found"
        )
    return models.Body(**data)
