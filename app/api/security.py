"""Password and JWT authentication for HTTP and WebSocket clients."""

import time

import bcrypt
import jwt

from app.bootstrap.settings import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 60 * 60

_ADMIN_PASSWORD_HASH = bcrypt.hashpw(
    settings.admin_password.encode(),
    bcrypt.gensalt(),
)


def verify_credentials(username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    return bcrypt.checkpw(password.encode(), _ADMIN_PASSWORD_HASH)


def create_access_token(subject: str) -> str:
    payload = {
        "sub": subject,
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.PyJWTError as error:
        raise ValueError("Token is invalid or expired.") from error
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token is invalid or expired.")
    return subject
