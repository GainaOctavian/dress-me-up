from starlette import status
from fastapi import APIRouter

from app.backend.common import layering

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/layering", status_code=status.HTTP_200_OK)
async def get_layering():
    """Garment types (subcategories) with their body slot, layer role and
    draw-order band. Static; clients cache it by `format`."""
    return layering.as_json()
