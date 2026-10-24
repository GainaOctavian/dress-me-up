from typing import List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.storage import s3
from app.backend.api.src.dto.input import body as dto_in
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
        input_cm=body.input_cm,
        status=body.status,
        error=body.error,
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


def save_my_body(db: Database, user_id: str, request: dto_in.SaveMyBody) -> models.Body:
    """Plan 16a: (re)build the user's body from their measurements. The
    renderer fits Anny to them and renders every pose (`body_build`, ~1.5
    min); until then the body is `building` and keeps its old poses."""
    data = _db("Error retrieving body", bodies_repo.find_user_body, db, user_id)
    old = models.Body(**data) if data else None
    body = models.Body(
        id=old.id if old else models.generate_id(), owner_id=user_id, kind=models.BodyKind.USER,
        gender=request.gender, poses=old.poses if old else {},
        measurements_cm=old.measurements_cm if old else {}, phenotype=old.phenotype if old else {},
        input_cm=request.model_dump(exclude={"gender"}, exclude_none=True), status="building",
    )
    _db("Error saving body", bodies_repo.replace_body, db, body)
    try:
        queue.publish(queue.BODY_QUEUE, {"body_id": body.id})
    except Exception:  # RabbitMQ down: saving again re-queues it
        pass
    return body


def delete_my_body(db: Database, user_id: str) -> None:
    """Removes the doc and every object right away. Outfits dressed on it go
    back to the mannequin of the same gender (and re-render)."""
    from app.backend.api.src.services import outfit as outfit_service  # it imports us
    data = _db("Error retrieving body", bodies_repo.find_user_body, db, user_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You have no body model")
    body = models.Body(**data)
    _db("Error deleting body", bodies_repo.delete_body_by_id, db, body.id)
    for pose in body.poses.values():
        for key in (pose.image_key, pose.params_key):
            if key:
                try:
                    s3.delete(key)
                except Exception:
                    pass  # best effort, like image_service.delete_asset
    outfit_service.move_off_body(db, body.id, f"mannequin_{body.gender}")
