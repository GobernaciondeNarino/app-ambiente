"""Aplicación FastAPI del Geoportal Ambiental de la Gobernación de Nariño."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import errores
from .config import VERSION, get_settings, origin_of
from .db import Base, get_engine, session_scope
from .models import Category, User
from .routers import admin, public
from .security import hash_password

log = logging.getLogger("geoportal")


class CORSGeoLibre(CORSMiddleware):
    """CORS para la instancia externa de GeoLibre, que el administrador puede cambiar en caliente.

    El Estudio SIG integrado comparte origen con el geoportal y no necesita CORS; la instancia
    externa (respaldo si el Estudio no está instalado) descarga el proyecto y los datos desde
    otro origen. CORS compara orígenes (esquema + dominio + puerto), nunca rutas.
    """

    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        from .services import estudio

        s = get_settings()
        return bool(origin) and origin in {origin_of(estudio.url_externa(s)), origin_of(s.public_base_url)}

# Categorías temáticas iniciales de la Secretaría de Ambiente y Desarrollo Sostenible
DEFAULT_CATEGORIES = [
    ("Recurso hídrico", "Cuencas, drenajes, cuerpos de agua y POMCA.", "#0E7FC0", "agua"),
    ("Áreas protegidas y ecosistemas estratégicos", "SINAP, páramos, humedales, manglares y bosque seco.", "#10A13B", "hoja"),
    ("Biodiversidad", "Especies, coberturas y conectividad ecológica.", "#2E7D32", "especie"),
    ("Cambio climático y gestión del riesgo", "Amenazas, vulnerabilidad y adaptación.", "#F2A900", "clima"),
    ("Ordenamiento territorial ambiental", "Determinantes ambientales, zonificación y usos del suelo.", "#6D8B1E", "mapa"),
    ("Coberturas de la tierra y deforestación", "Corine Land Cover, cambio de cobertura y alertas.", "#8D6E63", "bosque"),
    ("Límites y cartografía base", "División político-administrativa y referencia.", "#4D4D4D", "limites"),
]


def init_db() -> None:
    settings = get_settings()
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        if session.scalar(select(User.id).limit(1)) is None:
            password = settings.admin_password
            if not password:
                import secrets

                password = secrets.token_urlsafe(12)
                log.warning(
                    "GEOPORTAL_ADMIN_PASSWORD no está definido. Contraseña temporal del usuario '%s': %s",
                    settings.admin_user,
                    password,
                )
            session.add(
                User(
                    username=settings.admin_user,
                    full_name="Administrador del geoportal",
                    email=settings.admin_email,
                    role="administrador",
                    password_hash=hash_password(password),
                )
            )
        if session.scalar(select(Category.id).limit(1)) is None:
            from .services.layers import slugify

            for i, (name, desc, color, icon) in enumerate(DEFAULT_CATEGORIES):
                session.add(Category(slug=slugify(name), name=name, description=desc, color=color, icon=icon, position=i))
        session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Geoportal Ambiental — Gobernación de Nariño",
        description="API de catálogo, consulta y administración de geodatos de la Secretaría de Ambiente y Desarrollo Sostenible.",
        version=VERSION,
        lifespan=lifespan,
        docs_url=None,  # se sirve abajo con una URL relativa (funciona en subdirectorios)
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    )
    if settings.docs_enabled:
        from fastapi.openapi.docs import get_swagger_ui_html

        @app.get("/api/docs", include_in_schema=False)
        def docs():
            # «openapi.json» relativo a /…/api/docs: vale en la raíz y en cualquier subdirectorio
            return get_swagger_ui_html(openapi_url="openapi.json", title="API · Geoportal Ambiental")

    # Orígenes fijos (GEOPORTAL_CORS_ORIGINS); la instancia externa de GeoLibre se evalúa en cada petición
    app.add_middleware(
        CORSGeoLibre,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "HEAD", "OPTIONS"] if not settings.cors_origins else ["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
    )
    # Errores en JSON y en español, con la misma forma que la edición PHP
    errores.instalar(app)
    # La compresión gzip la hace nginx (no aplica a respuestas parciales 206 de las COG)
    app.include_router(public.router)
    app.include_router(admin.auth_router)
    app.include_router(admin.router)

    # Desarrollo sin nginx: GEOPORTAL_PORTAL_DIR=../portal sirve el sitio estático
    portal_dir = os.getenv("GEOPORTAL_PORTAL_DIR")
    if portal_dir:
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=portal_dir, html=True), name="portal")
    return app


app = create_app()
