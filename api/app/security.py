"""Autenticación: contraseñas con bcrypt y tokens JWT (HS256)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_session
from .models import AuditLog, User

_bearer = HTTPBearer(auto_error=False)
MIN_PASSWORD_LENGTH = 10

# Límite de intentos de ingreso: mismos valores y mensaje que la edición PHP (autenticacion.php)
VENTANA_INGRESO_S = 15 * 60  # ventana en la que cuentan los fallos
MAX_FALLOS_USUARIO_IP = 5  # fallos de un usuario desde una IP
MAX_FALLOS_IP = 20  # fallos desde una IP con cualquier usuario (rociado de usuarios)
MENSAJE_BLOQUEO = "Demasiados intentos fallidos. Espere unos minutos e inténtelo de nuevo."


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


def ip_cliente(request) -> str:
    """IP del cliente según el servidor ASGI. Detrás de nginx, uvicorn la toma de X-Forwarded-For
    (--proxy-headers): debe confiar solo en el proxy (--forwarded-allow-ips) o el cliente podría falsearla."""
    return request.client.host if request.client and request.client.host else "desconocida"


def segundos_bloqueo_ingreso(session: Session, usuario: str, ip: str) -> int:
    """0 si se puede intentar el ingreso; si no, segundos hasta que caduque el fallo que mantiene el bloqueo.

    Cuenta las entradas «ingreso_fallido» de la bitácora (su «detail» es la IP) de la ventana: por usuario + IP
    y por IP sola. Nunca por usuario solo: así nadie puede dejar fuera al administrador desde otra IP.
    """
    ahora = datetime.now(timezone.utc)
    ventana = timedelta(seconds=VENTANA_INGRESO_S)
    fallos = (
        select(AuditLog.at)
        .where(AuditLog.action == "ingreso_fallido", AuditLog.detail == ip, AuditLog.at >= ahora - ventana)
        .order_by(AuditLog.at, AuditLog.id)
    )
    espera = 0
    for consulta, maximo in ((fallos.where(AuditLog.username == usuario), MAX_FALLOS_USUARIO_IP), (fallos, MAX_FALLOS_IP)):
        fechas = session.scalars(consulta).all()
        if len(fechas) >= maximo:
            # Al caducar este fallo (el más antiguo de la ventana) el recuento baja del umbral
            clave = fechas[len(fechas) - maximo]
            if clave.tzinfo is None:  # SQLite devuelve la hora sin zona (se guarda en UTC)
                clave = clave.replace(tzinfo=timezone.utc)
            espera = max(espera, math.ceil((clave + ventana - ahora).total_seconds()), 1)
    return espera


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
