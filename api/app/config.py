"""Configuración del servicio, leída de variables de entorno."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    # Rutas
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("GEOPORTAL_DATA_DIR", "./data")).resolve())
    database_url: str = field(default_factory=lambda: os.getenv("GEOPORTAL_DATABASE_URL", ""))

    # Seguridad
    secret_key: str = field(default_factory=lambda: os.getenv("GEOPORTAL_SECRET_KEY", ""))
    token_hours: int = field(default_factory=lambda: int(os.getenv("GEOPORTAL_TOKEN_HOURS", "8")))
    admin_user: str = field(default_factory=lambda: os.getenv("GEOPORTAL_ADMIN_USER", "admin"))
    admin_password: str = field(default_factory=lambda: os.getenv("GEOPORTAL_ADMIN_PASSWORD", ""))
    admin_email: str = field(default_factory=lambda: os.getenv("GEOPORTAL_ADMIN_EMAIL", ""))

    # URLs públicas
    public_base_url: str = field(
        default_factory=lambda: os.getenv("GEOPORTAL_PUBLIC_URL", "http://localhost:8080").rstrip("/")
    )
    geolibre_url: str = field(
        default_factory=lambda: os.getenv("GEOLIBRE_PUBLIC_URL", "http://localhost:8081").rstrip("/")
    )
    cors_origins: list[str] = field(default_factory=lambda: _env_list("GEOPORTAL_CORS_ORIGINS"))

    # Límites de carga
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("GEOPORTAL_MAX_UPLOAD_MB", "500")))
    # Por encima de este tamaño la capa no se embebe en el proyecto GeoLibre;
    # se referencia por URL y GeoLibre la descarga al abrir.
    inline_max_mb: float = field(default_factory=lambda: float(os.getenv("GEOPORTAL_INLINE_MAX_MB", "15")))
    coordinate_precision: int = field(default_factory=lambda: int(os.getenv("GEOPORTAL_COORD_PRECISION", "6")))

    # Proyecto GeoLibre
    project_name: str = field(
        default_factory=lambda: os.getenv(
            "GEOPORTAL_PROJECT_NAME", "Geoportal Ambiental — Gobernación de Nariño"
        )
    )
    map_center: tuple[float, float] = (-77.8, 1.45)
    map_zoom: float = 7.4
    basemap_url: str = field(
        default_factory=lambda: os.getenv("GEOPORTAL_BASEMAP_URL", "https://tiles.openfreemap.org/styles/liberty")
    )

    docs_enabled: bool = field(default_factory=lambda: _env_bool("GEOPORTAL_API_DOCS", True))

    def __post_init__(self) -> None:
        if not self.database_url:
            self.database_url = f"sqlite:///{self.data_dir / 'geoportal.db'}"
        if not self.secret_key:
            # Clave efímera: los tokens se invalidan al reiniciar. En producción
            # se debe definir GEOPORTAL_SECRET_KEY.
            self.secret_key = secrets.token_urlsafe(48)

    # Subcarpetas de almacenamiento
    @property
    def originals_dir(self) -> Path:
        return self.data_dir / "originales"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "procesados"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.originals_dir, self.processed_dir, self.tmp_dir):
            path.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings


def reset_settings() -> None:
    """Solo para pruebas: fuerza a releer el entorno."""
    global _settings
    _settings = None
