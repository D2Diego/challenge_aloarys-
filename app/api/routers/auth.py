"""Access token endpoint."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.errors import http_error
from app.api.security import create_access_token, verify_credentials

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not verify_credentials(form_data.username, form_data.password):
        raise http_error(
            401,
            "INVALID_CREDENTIALS",
            "Username or password is incorrect.",
        )
    return {
        "access_token": create_access_token(form_data.username),
        "token_type": "bearer",
    }
