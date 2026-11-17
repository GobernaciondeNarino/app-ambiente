"""Modelo de datos del geoportal."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ROLES = ("administrador", "editor")


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="editor")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Category(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(9), default="#10A13B")
    icon: Mapped[str] = mapped_column(String(40), default="capas")
    position: Mapped[int] = mapped_column(Integer, default=0)

    layers: Mapped[list[Layer]] = relationship(back_populates="category")


class Layer(Base):
    __tablename__ = "capas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)

    # Datos técnicos (se calculan en la ingesta)
    kind: Mapped[str] = mapped_column(String(10), default="vector")  # vector | raster
    source_format: Mapped[str] = mapped_column(String(40), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    original_path: Mapped[str] = mapped_column(String(500), default="")
    processed_path: Mapped[str] = mapped_column(String(500), default="")
    preview_path: Mapped[str] = mapped_column(String(500), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    geometry_type: Mapped[str] = mapped_column(String(40), default="")
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    source_crs: Mapped[str] = mapped_column(String(120), default="")
    attributes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    raster_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Simbología
    style: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    popup_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    label_field: Mapped[str] = mapped_column(String(120), default="")

    # Metadatos descriptivos (perfil básico ISO 19115 / NTC 4611)
    source: Mapped[str] = mapped_column(String(255), default="")  # entidad productora
    author: Mapped[str] = mapped_column(String(160), default="")
    contact_email: Mapped[str] = mapped_column(String(160), default="")
    license: Mapped[str] = mapped_column(String(120), default="CC-BY-4.0")
    data_date: Mapped[str] = mapped_column(String(20), default="")  # fecha de la información (AAAA-MM-DD)
    scale: Mapped[str] = mapped_column(String(40), default="")
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    lineage: Mapped[str] = mapped_column(Text, default="")
    update_frequency: Mapped[str] = mapped_column(String(40), default="")

    # Publicación
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    downloadable: Mapped[bool] = mapped_column(Boolean, default=True)
    visible_by_default: Mapped[bool] = mapped_column(Boolean, default=False)
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    position: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_by: Mapped[str] = mapped_column(String(80), default="")
    updated_by: Mapped[str] = mapped_column(String(80), default="")

    category: Mapped[Category | None] = relationship(back_populates="layers")


class AuditLog(Base):
    __tablename__ = "bitacora"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    username: Mapped[str] = mapped_column(String(80), default="")
    action: Mapped[str] = mapped_column(String(40))
    target: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------- servicio de compartir de GeoLibre
# Mismas tablas y columnas que la edición PHP (esquema.php). El documento puede ocupar varios MB:
# LONGTEXT en MySQL (TEXT se queda en 64 KB); en SQLite y PostgreSQL basta TEXT.
TEXTO_LARGO = Text().with_variant(LONGTEXT(), "mysql", "mariadb")


class ShareToken(Base):
    """Token personal para el servicio de compartir. Solo se guarda su SHA-256 y un prefijo reconocible."""

    __tablename__ = "compartir_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    prefix: Mapped[str] = mapped_column(String(16), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()


class SharedProject(Base):
    __tablename__ = "compartir_proyectos"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_usuario_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID: no se pueden enumerar
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(12), default="private", index=True)  # public | unlisted | private
    views: Mapped[int] = mapped_column(Integer, default=0)
    last_version: Mapped[int] = mapped_column(Integer, default=1)  # número de la versión vigente
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()


class SharedProjectVersion(Base):
    __tablename__ = "compartir_versiones"

    project_id: Mapped[str] = mapped_column(ForeignKey("compartir_proyectos.id", ondelete="CASCADE"), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(TEXTO_LARGO)
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
