from typing import Literal, Optional

from pydantic import BaseModel, Field


class SaveMyBody(BaseModel):
    """Plan 16a: the user's measurements; the renderer fits Anny to them.
    Height and weight are enough; girths make the shape closer."""
    gender: Literal["male", "female"]
    height_cm: float = Field(ge=130, le=205)  # the body images' frame fits up to ~2.03 m
    weight_kg: float = Field(ge=35, le=200)
    chest_cm: Optional[float] = Field(default=None, ge=60, le=170)
    waist_cm: Optional[float] = Field(default=None, ge=45, le=170)
    hips_cm: Optional[float] = Field(default=None, ge=60, le=180)
