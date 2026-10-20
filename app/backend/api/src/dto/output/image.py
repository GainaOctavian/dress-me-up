from typing import Dict

from pydantic import BaseModel


class UploadTarget(BaseModel):
    """
    Where and how to upload: POST multipart to `url` with `fields`
    plus the file as the last field named "file"
    """
    image_asset_id: str
    url: str
    fields: Dict[str, str]
    max_bytes: int
