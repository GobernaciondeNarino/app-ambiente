"""Autenticación: contraseñas con bcrypt y tokens JWT (HS256)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_session
from .models import User

_bearer = HTTPBearer(auto_error=False)
MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("ascii"))
    except ValueError:
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            422,
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
        )
    if password.isalpha() or password.isdigit():
        raise HTTPException(
            422,
            "La contraseña debe combinar letras y números o símbolos.",
        )


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.token_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _unauthorized(detail: str = "Sesión no válida o expirada.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Debe iniciar sesión.")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc
    user = session.scalar(select(User).where(User.username == payload.get("sub")))
    if user is None or not user.active:
        raise _unauthorized()
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Se requiere el rol de administrador.")
    return user
