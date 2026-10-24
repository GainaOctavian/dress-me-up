from typing import Dict, List, Optional

from pydantic import BaseModel

from app.backend.common.db import models


class BodyPoseOut(models.BodyPose):
    image_url: str  # presigned, 24h


class BodyOut(BaseModel):
    id: str
    kind: models.BodyKind
    gender: str
    format: int
    poses: Dict[str, BodyPoseOut]
    measurements_cm: Dict[str, float]
    # user bodies (plan 16): what they typed, and the build's state
    input_cm: Dict[str, float] = {}
    status: str = "ready"  # building | ready | failed
    error: Optional[str] = None


class GetBody(BaseModel):
    body: BodyOut


class GetAllBodies(BaseModel):
    bodies: List[BodyOut]
