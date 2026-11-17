"""Esquemas de entrada/salida de la API."""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
ISO_DATE = re.compile(r"([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?")
# Correo: parte local «dot-atom» y dominio con al menos un punto. Misma expresión que correo_valido() de la
# edición PHP; acepta lo mismo que FILTER_VALIDATE_EMAIL salvo los dominios entre corchetes.
EMAIL = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)
FECHA_FORMATO = "Use el formato AAAA, AAAA-MM o AAAA-MM-DD."
FECHA_INEXISTENTE = "La fecha no existe (mes de 01 a 12 y un día válido para ese mes)."
CORREO_NO_VALIDO = "Correo electrónico no válido (p. ej. nombre@entidad.gov.co)."
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


def correo_opcional(v: str | None) -> str | None:
    """Vacío o un correo válido (sin espacios extremos)."""
    if v is None:
        return v
    v = v.strip()
    if v and not EMAIL.fullmatch(v):
        raise ValueError(CORREO_NO_VALIDO)
    return v


def fecha_opcional(v: str | None) -> str | None:
    """Vacío, AAAA, AAAA-MM o AAAA-MM-DD con un mes y un día que existan en el calendario."""
    if v is None:
        return v
    v = v.strip()
    if not v:
        return v
    m = ISO_DATE.fullmatch(v)
    if not m:
        raise ValueError(FECHA_FORMATO)
    try:
        date(int(m[1]), int(m[2] or 1), int(m[3] or 1))
    except ValueError:
        raise ValueError(FECHA_INEXISTENTE) from None
    return v


def _numero_estilo(clave: str, valor: Any) -> float:
    """Número de la simbología; el mensaje de error es el mismo de la edición PHP."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = math.nan
    if isinstance(valor, bool) or not math.isfinite(numero):
        raise ValueError(f"{clave}: debe ser numérico.")
    return numero


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

    @field_validator("email")
    @classmethod
    def _correo(cls, v: str | None) -> str | None:
        return correo_opcional(v)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=160)
    password: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, pattern="^(administrador|editor)$")
    active: bool | None = None

    @field_validator("email")
    @classmethod
    def _correo(cls, v: str | None) -> str | None:
        return correo_opcional(v)


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
        return fecha_opcional(v)

    @field_validator("contact_email")
    @classmethod
    def _correo(cls, v: str | None) -> str | None:
        return correo_opcional(v)

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
                clean[key] = max(1, int(_numero_estilo(key, value)))
            else:
                number = _numero_estilo(key, value)
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


# ---------------------------------------------------------------- servicio de compartir de GeoLibre (/api/compartir)
# Validación y representación del contrato v1 de GeoLibre; las rutas están en routers/compartir.py.
# Mismos mensajes que portal/api/lib/compartir.php (edición PHP).


class ErrorCompartir(Exception):
    """Error del servicio de compartir: se responde con «error» (contrato de GeoLibre) y «detail» (resto de la API)."""

    def __init__(self, estado: int, mensaje: str, cabeceras: dict[str, str] | None = None) -> None:
        super().__init__(mensaje)
        self.estado, self.mensaje, self.cabeceras = estado, mensaje, cabeceras or {}


def _sin_constantes(valor: str):
    raise ValueError(valor)


def json_estricto(texto: str | bytes) -> Any:
    """``json.loads`` sin NaN ni Infinity, que no son JSON (la edición PHP tampoco los acepta)."""
    return json.loads(texto, parse_constant=_sin_constantes)


def utc(dt: datetime | None) -> datetime | None:
    """La hora en UTC con zona (SQLite la devuelve sin zona, aunque se guarda en UTC)."""
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def iso_utc(dt: datetime | None) -> str | None:
    """``2026-11-17T12:00:00Z``, como gp_iso() de la edición PHP."""
    d = utc(dt)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def param_booleano(nombre: str, valor: str | None, error: type = ErrorCompartir) -> bool:
    """Mismas formas que valor_booleano() de la edición PHP; sin el parámetro, falso."""
    if valor is None:
        return False
    s = valor.strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise error(422, f"{nombre}: debe ser verdadero o falso.")


def param_entero(nombre: str, valor: str, defecto: int, minimo: int, maximo: int) -> int:
    """Como param_entero() de la edición PHP: vacío o ausente, el valor por defecto."""
    if valor == "":
        return defecto
    if not re.fullmatch(r"-?\d{1,18}", valor.strip()):
        raise ErrorCompartir(422, f"{nombre}: debe ser un número entero.")
    n = int(valor)
    if n < minimo or n > maximo:
        raise ErrorCompartir(422, f"{nombre}: debe estar entre {minimo} y {maximo}.")
    return n


def error_tamano(limite: int) -> ErrorCompartir:
    texto = f"{limite // 1048576} MB" if limite >= 1048576 else f"{max(1, limite // 1024)} KB"
    return ErrorCompartir(413, f"El proyecto supera el tamaño máximo para compartir ({texto}).")


def proyecto_geolibre(contenido: Any, limite: int) -> str:
    """Valida el JSON de un proyecto de GeoLibre (texto) y devuelve su título («title» o «name»), o ''."""
    if not isinstance(contenido, str) or contenido == "":
        raise ErrorCompartir(422, "content: es obligatorio y debe ser el JSON del proyecto como texto.")
    if len(contenido.encode("utf-8", "surrogatepass")) > limite:
        raise error_tamano(limite)
    try:
        contenido.encode("utf-8")  # sustitutos sueltos («\ud800»): la edición PHP tampoco los acepta
        doc = json_estricto(contenido)
    except ValueError:
        doc = None
    if not isinstance(doc, dict):
        raise ErrorCompartir(422, "content: no es un objeto JSON válido.")
    v = doc.get("version")  # texto no vacío o número
    version_valida = (isinstance(v, str) and v.strip() != "") or (isinstance(v, (int, float)) and not isinstance(v, bool))
    if not version_valida or not isinstance(doc.get("layers"), list):
        raise ErrorCompartir(422, "content: no es un proyecto de GeoLibre (faltan «version» o la lista «layers»).")
    for campo in ("title", "name"):
        if isinstance(doc.get(campo), str) and doc[campo].strip():
            return doc[campo].strip()
    return ""


def titulo_de_archivo(nombre: Any) -> str:
    """Título de respaldo a partir de «filename». Nunca se usa como ruta: solo da el título (y de ahí el slug)."""
    if nombre is None:
        return ""
    if not isinstance(nombre, str) or len(nombre) > 255:
        raise ErrorCompartir(422, "filename: debe ser texto de hasta 255 caracteres.")
    ultimo = nombre.replace("\\", "/").split("/")[-1]
    return re.sub(r"(\.geolibre)?\.json$|\.geolibre$", "", ultimo, flags=re.I).strip()


def token_compartir_salida(t: Any, ahora: datetime) -> dict:
    """Token personal tal como lo ve el administrador (nunca el token ni su resumen)."""
    return {
        "id": t.id, "name": t.name, "prefix": t.prefix, "username": t.user.username,
        "created_at": iso_utc(t.created_at), "last_used_at": iso_utc(t.last_used_at), "expires_at": iso_utc(t.expires_at),
        "expired": t.expires_at is not None and utc(t.expires_at) <= ahora,
    }


def url_proyecto_compartido(url_publica: str, usuario: str, slug: str) -> str:
    """Página del proyecto: la portada del geoportal lo abre con ?compartido=usuario/slug."""
    return f"{url_publica}/?compartido={quote(usuario, safe='')}/{quote(slug, safe='')}#mapa"


def proyecto_compartido_salida(p: Any, url_publica: str, yo_id: int | None) -> dict:
    """Representación del contrato. «featured»: proyectos públicos de los administradores del geoportal.

    ``canEdit`` solo en respuestas autenticadas. Sin organizaciones, grupos, miniaturas ni enlaces con rol,
    caducidad o contraseña (GeoLibre avisa de que esos ajustes no se aplicaron).
    """
    usuario = p.user.username
    pagina = url_proyecto_compartido(url_publica, usuario, p.slug)
    salida = {
        "id": p.id, "username": usuario, "slug": p.slug, "title": p.title,
        "description": p.description, "visibility": p.visibility, "organization": None, "groupIds": [],
        "thumbnailUrl": None, "views": p.views, "forkCount": 0, "versionCount": p.last_version,
        "featured": p.visibility == "public" and p.user.role == "administrador",
        "role": "edit", "expiresAt": None, "hasPassword": False,
        "createdAt": iso_utc(p.created_at), "updatedAt": iso_utc(p.updated_at), "tags": [],
        "rawJsonUrl": f"{url_publica}/api/compartir/{quote(usuario, safe='')}/{quote(p.slug, safe='')}.geolibre.json",
        "projectUrl": pagina, "viewerUrl": pagina,
    }
    if yo_id is not None:
        salida["canEdit"] = yo_id == p.user_id
    return salida
