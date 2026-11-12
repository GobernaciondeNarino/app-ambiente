"""Esquemas de entrada/salida de la API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
ISO_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
ALLOWED_STYLE_KEYS = {
    "fillColor",
    "strokeColor",
    "strokeWidth",
    "fillOpacity",
    "circleRadius",
    "colorRamp",
    "rasterMin",
    "rasterMax",
    "rasterMode",
    "band",
}


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str
    role: str
    active: bool
    created_at: datetime
    last_login: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=160)
    password: str = Field(min_length=1, max_length=200)
    role: str = Field(default="editor", pattern="^(administrador|editor)$")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=160)
    password: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, pattern="^(administrador|editor)$")
    active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    color: str = "#10A13B"
    icon: str = Field(default="capas", max_length=40)
    position: int = 0

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not HEX_COLOR.match(v):
            raise ValueError("Color hexadecimal no válido (use #RRGGBB).")
        return v


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    color: str
    icon: str
    position: int
    layer_count: int = 0


class LayerMetaIn(BaseModel):
    """Metadatos editables de una capa (todos opcionales para edición parcial)."""

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    category_id: int | None = None
    source: str | None = Field(default=None, max_length=255)
    author: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=160)
    license: str | None = Field(default=None, max_length=120)
    data_date: str | None = Field(default=None, max_length=20)
    scale: str | None = Field(default=None, max_length=40)
    keywords: list[str] | None = None
    lineage: str | None = Field(default=None, max_length=5000)
    update_frequency: str | None = Field(default=None, max_length=40)
    style: dict[str, Any] | None = None
    popup_fields: list[str] | None = None
    label_field: str | None = Field(default=None, max_length=120)
    downloadable: bool | None = None
    visible_by_default: bool | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    position: int | None = None
    published: bool | None = None

    @field_validator("data_date")
    @classmethod
    def _date(cls, v: str | None) -> str | None:
        if v and not ISO_DATE.match(v):
            raise ValueError("Use el formato AAAA, AAAA-MM o AAAA-MM-DD.")
        return v

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        seen: list[str] = []
        for k in v:
            k = k.strip()
            if k and k.lower() not in {s.lower() for s in seen}:
                seen.append(k[:60])
        return seen[:30]

    @field_validator("style")
    @classmethod
    def _style(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        clean: dict[str, Any] = {}
        for key, value in v.items():
            if key not in ALLOWED_STYLE_KEYS or value is None or value == "":
                continue
            if key in ("fillColor", "strokeColor"):
                if not isinstance(value, str) or not HEX_COLOR.match(value):
                    raise ValueError(f"{key}: color hexadecimal no válido.")
                clean[key] = value
            elif key in ("colorRamp", "rasterMode"):
                clean[key] = str(value)[:20]
            elif key == "band":
                clean[key] = max(1, int(value))
            else:
                number = float(value)
                if key == "fillOpacity":
                    number = min(max(number, 0), 1)
                if key in ("strokeWidth", "circleRadius"):
                    number = min(max(number, 0), 50)
                clean[key] = number
        return clean


class LayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str
    category_id: int | None
    category: CategoryOut | None = None
    kind: str
    source_format: str
    original_filename: str
    file_size: int
    geometry_type: str
    feature_count: int
    bbox: list[float] | None
    source_crs: str
    attributes: list[dict[str, Any]]
    raster_info: dict[str, Any] | None
    style: dict[str, Any]
    popup_fields: list[str]
    label_field: str
    source: str
    author: str
    contact_email: str
    license: str
    data_date: str
    scale: str
    keywords: list[str]
    lineage: str
    update_frequency: str
    published: bool
    downloadable: bool
    visible_by_default: bool
    opacity: float
    position: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    urls: dict[str, str] = {}
    geolibre_url: str = ""
    geolibre_id: str = ""


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    at: datetime
    username: str
    action: str
    target: str
    detail: str
