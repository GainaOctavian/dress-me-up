from pydantic import BaseModel


class Token(BaseModel):
    """
    DTO for authentication token
    """
    access_token: str
    token_type: str = "Bearer"
