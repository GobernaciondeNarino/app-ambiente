"""Operaciones comunes sobre capas: slugs, serialización, archivos y bitácora."""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AuditLog, Category, Layer
from ..schemas import CategoryOut, LayerOut
from .geolibre import geolibre_open_url, layer_urls

CHUNK = 1024 * 1024


def slugify(text: str, max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return (slug or "capa")[:max_length].strip("-")


def unique_slug(session: Session, model: type, text: str, exclude_id: int | None = None) -> str:
    base = slugify(text)
    slug, n = base, 2
    while True:
        query = select(model.id).where(model.slug == slug)
        if exclude_id is not None:
            query = query.where(model.id != exclude_id)
        if session.scalar(query) is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


def safe_filename(name: str) -> str:
    name = Path(name or "archivo").name
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    clean = slugify(stem, 100) or "archivo"
    return f"{clean}.{ext.lower()}" if ext else clean


async def save_upload(upload: UploadFile, dest: Path, max_bytes: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as fh:
        while chunk := await upload.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"El archivo supera el máximo permitido ({max_bytes // 1024**2} MB).",
                )
            fh.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "El archivo está vacío.")
    return size


def category_out(session: Session, cat: Category, published_only: bool = False) -> CategoryOut:
    query = select(func.count(Layer.id)).where(Layer.category_id == cat.id)
    if published_only:
        query = query.where(Layer.published.is_(True))
    out = CategoryOut.model_validate(cat)
    out.layer_count = int(session.scalar(query) or 0)
    return out


def layer_out(layer: Layer, settings: Settings) -> LayerOut:
    out = LayerOut.model_validate(layer)
    if layer.category is not None:
        out.category = CategoryOut.model_validate(layer.category)
    out.urls = layer_urls(settings, layer)
    out.geolibre_url = geolibre_open_url(settings, out.urls["proyecto"])
    return out


def public_layer_dict(layer: Layer, settings: Settings) -> dict:
    """Versión pública: sin rutas internas ni datos de usuarios."""
    data = layer_out(layer, settings).model_dump(mode="json")
    for key in ("created_by", "updated_by", "original_filename", "published"):
        data.pop(key, None)
    return data


def layer_dirs(settings: Settings, layer_id: int) -> tuple[Path, Path]:
    return settings.originals_dir / str(layer_id), settings.processed_dir / str(layer_id)


def remove_layer_files(settings: Settings, layer_id: int) -> None:
    for folder in layer_dirs(settings, layer_id):
        shutil.rmtree(folder, ignore_errors=True)


def audit(session: Session, username: str, action: str, target: str = "", detail: str = "") -> None:
    session.add(AuditLog(username=username, action=action, target=target[:200], detail=detail[:4000]))


def get_layer_or_404(session: Session, layer_id: int) -> Layer:
    layer = session.get(Layer, layer_id)
    if layer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capa no encontrada.")
    return layer
