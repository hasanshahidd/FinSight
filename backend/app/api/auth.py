"""Mock auth endpoint — issues a JWT for the demo user."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.security import create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = "demo@finsight.ai"
    password: str = "demo"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    # Mock — accept anything, always return the demo user.
    user_id = "user_1"
    return TokenResponse(access_token=create_access_token(user_id), user_id=user_id)
