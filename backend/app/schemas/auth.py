import uuid
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    employee_id: uuid.UUID | None = None
    store_id: uuid.UUID | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class APIResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict | list | str | None = None
    request_id: str | None = None
