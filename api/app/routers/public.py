"""API pública del geoportal (solo lectura, solo capas publicadas)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import String, or_, select
from sqlalchemy.orm import Session, selectinload

from ..config import VERSION, Settings, request_settings
from ..db import get_session
from ..models import Category, Layer
from ..services import estudio
from ..services.geolibre import build_project
from ..services.layers import category_out, public_layer_dict


def _settings(request: Request) -> Settings:
    return request_settings(request)


router = APIRouter(prefix="/api", tags=["público"])

GEOLIBRE_MEDIA = "application/json"
CACHE_SHORT = "public, max-age=60"


def _get(path: str, **kw):
    """GET que también atiende HEAD, como la edición PHP (los lectores de COG y GDAL piden HEAD)."""

    def decorar(fn):
        router.add_api_route(path, fn, methods=["HEAD"], **(kw | {"include_in_schema": False}))
        return router.get(path, **kw)(fn)

    return decorar


def like_literal(texto: str) -> str:
    """Patrón LIKE que busca el texto literal: «%» y «_» no actúan como comodines (escape «\\»)."""
    limpio = texto.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"


def _published(session: Session, slug: str) -> Layer:
    layer = session.scalar(
        select(Layer).options(selectinload(Layer.category)).where(Layer.slug == slug, Layer.published.is_(True))
    )
    if layer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capa no encontrada o no publicada.")
    return layer


def _file_or_404(path_str: str) -> Path:
    path = Path(path_str) if path_str else None
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El archivo de la capa no está disponible.")
    return path


@_get("/salud")
def health() -> dict:
    # Mismos campos que la edición PHP (el asistente de instalación los usa)
    return {"estado": "ok", "edicion": "docker", "version": VERSION}


@_get("/config")
def portal_config(settings: Settings = Depends(_settings)) -> dict:
    """Parámetros que el visor necesita (centro, URLs de GeoLibre)."""
    project_url = f"{settings.public_base_url}/api/proyecto.geolibre"
    cfg_estudio = estudio.config_publica(settings)
    return {
        "nombre": settings.project_name,
        "centro": list(settings.map_center),
        "zoom": settings.map_zoom,
        "geolibre_url": (cfg_estudio["url"] if cfg_estudio["activo"] else estudio.url_externa(settings)).rstrip("/"),
        "geolibre_local": cfg_estudio["activo"],
        "estudio": cfg_estudio,
        "proyecto_url": project_url,
        "geolibre_proyecto_url": estudio.url_abrir(settings, project_url),
        "geolibre_editor_url": estudio.url_abrir(settings, project_url, visor=False),
        # La edición Docker procesa los geodatos en el servidor (GDAL); la de Plesk, en el navegador
        "edicion": "docker",
        "ingesta": "servidor",
        "max_carga_mb": settings.max_upload_mb,
    }


@_get("/geolibre/deployment.json")
def geolibre_deployment(settings: Settings = Depends(_settings)) -> JSONResponse:
    a = estudio.ajustes(settings)
    from ..config import origin_of

    return JSONResponse(estudio.politica(a, origin_of(settings.public_base_url)), headers={"Cache-Control": "no-cache"})


@_get("/geolibre/ajustes.json")
def geolibre_ajustes(settings: Settings = Depends(_settings)) -> JSONResponse:
    return JSONResponse(estudio.interfaz(estudio.ajustes(settings)), headers={"Cache-Control": "no-cache"})


@_get("/categorias")
def list_categories(session: Session = Depends(get_session)) -> list[dict]:
    cats = session.scalars(select(Category).order_by(Category.position, Category.name)).all()
    out = [category_out(session, c, published_only=True).model_dump() for c in cats]
    return [c for c in out if c["layer_count"] > 0]


@_get("/capas")
def list_layers(
    q: str | None = Query(default=None, max_length=120, description="Texto a buscar"),
    categoria: str | None = Query(default=None, description="Slug de la categoría"),
    tipo: str | None = Query(default=None, pattern="^(vector|raster)$"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(_settings),
) -> list[dict]:
    query = select(Layer).options(selectinload(Layer.category)).where(Layer.published.is_(True))
    if q and q.strip():
        like = like_literal(q)
        query = query.where(
            or_(
                Layer.title.ilike(like, escape="\\"),
                Layer.description.ilike(like, escape="\\"),
                Layer.source.ilike(like, escape="\\"),
                # las palabras clave se guardan como JSON (texto en SQLite/PostgreSQL)
                Layer.keywords.cast(String).ilike(like, escape="\\"),
            )
        )
    if categoria:
        query = query.join(Category).where(Category.slug == categoria)
    if tipo:
        query = query.where(Layer.kind == tipo)
    layers = session.scalars(query.order_by(Layer.position, Layer.title)).all()
    return [public_layer_dict(layer, settings) for layer in layers]


@_get("/capas/{slug}")
def get_layer(slug: str, session: Session = Depends(get_session), settings: Settings = Depends(_settings)) -> dict:
    return public_layer_dict(_published(session, slug), settings)


@_get("/capas/{slug}/datos.geojson")
def layer_geojson(slug: str, session: Session = Depends(get_session)) -> FileResponse:
    layer = _published(session, slug)
    if layer.kind != "vector":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La capa no es vectorial.")
    path = _file_or_404(layer.processed_path)
    return FileResponse(path, media_type="application/geo+json", headers={"Cache-Control": CACHE_SHORT})


@_get("/capas/{slug}/datos.tif")
def layer_cog(slug: str, session: Session = Depends(get_session)) -> FileResponse:
    layer = _published(session, slug)
    if layer.kind != "raster":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La capa no es ráster.")
    path = _file_or_404(layer.processed_path)
    # FileResponse atiende peticiones por rangos (Range), necesarias para COG
    return FileResponse(path, media_type="image/tiff", headers={"Cache-Control": CACHE_SHORT})


@_get("/capas/{slug}/vista-previa.png")
def layer_preview(slug: str, session: Session = Depends(get_session)) -> FileResponse:
    layer = _published(session, slug)
    path = _file_or_404(layer.preview_path)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": CACHE_SHORT})


@_get("/capas/{slug}/descarga")
def layer_download(
    slug: str, original: bool = False, session: Session = Depends(get_session)
) -> FileResponse:
    layer = _published(session, slug)
    if not layer.downloadable:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La descarga de esta capa no está habilitada.")
    if original:
        path = _file_or_404(layer.original_path)
        filename = layer.original_filename or path.name
    else:
        path = _file_or_404(layer.processed_path)
        filename = f"{layer.slug}{path.suffix}"
    media = "application/octet-stream"
    return FileResponse(path, media_type=media, filename=filename)


@_get("/capas/{slug}/proyecto.geolibre")
def layer_project(
    slug: str,
    base: str | None = Query(default=None, description="Mapa base: calles, claro, oscuro, fiord o brillante"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(_settings),
) -> Response:
    layer = _published(session, slug)
    project = build_project([layer], settings, name=layer.title, categories=[layer.category] if layer.category else [], base=base)
    return _project_response(project, f"{layer.slug}.geolibre")


@_get("/proyecto.geolibre")
def full_project(
    categoria: str | None = None,
    capas: str | None = Query(default=None, description="Slugs separados por coma"),
    base: str | None = Query(default=None, description="Mapa base: calles, claro, oscuro, fiord o brillante"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(_settings),
) -> Response:
    """Proyecto GeoLibre con todas las capas publicadas (o un subconjunto)."""
    query = select(Layer).options(selectinload(Layer.category)).where(Layer.published.is_(True))
    if categoria:
        query = query.join(Category).where(Category.slug == categoria)
    slugs = [s.strip() for s in (capas or "").split(",") if s.strip()][:200]
    if slugs:  # «?capas=,,» sin ningún identificador equivale a no filtrar (como la edición PHP)
        query = query.where(Layer.slug.in_(slugs))
    layers = list(session.scalars(query.order_by(Layer.position, Layer.title)).all())
    cats = list(session.scalars(select(Category).order_by(Category.position, Category.name)).all())
    project = build_project(layers, settings, categories=cats, base=base)
    return _project_response(project, "geoportal-ambiental-narino.geolibre")


def _project_response(project: dict, filename: str) -> Response:
    body = json.dumps(project, ensure_ascii=False, separators=(",", ":"))
    return Response(
        content=body,
        media_type=GEOLIBRE_MEDIA,
        headers={
            "Cache-Control": CACHE_SHORT,
            # Las URL internas dependen del dominio/subdirectorio por el que se accede
            "Vary": "Host, X-Forwarded-Host, X-Forwarded-Proto, X-Forwarded-Prefix",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@_get("/", include_in_schema=False)
def api_root(settings: Settings = Depends(_settings)) -> JSONResponse:
    return JSONResponse(
        {
            "estado": "ok",
            "edicion": "docker",
            "servicio": "API del Geoportal Ambiental — Gobernación de Nariño",
            # URL completa: vale también cuando el geoportal vive en un subdirectorio
            "documentacion": f"{settings.public_base_url}/api/docs" if settings.docs_enabled else None,
            "version": VERSION,
        }
    )
