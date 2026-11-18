from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADMIN_PASSWORD = "Clave-Segura-2026"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOPORTAL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("GEOPORTAL_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("GEOPORTAL_SECRET_KEY", "prueba-" + "x" * 40)
    monkeypatch.setenv("GEOPORTAL_PUBLIC_URL", "http://portal.test")
    monkeypatch.setenv("GEOLIBRE_PUBLIC_URL", "http://visor.test")
    monkeypatch.setenv("GEOPORTAL_DATABASE_URL", "")
    # Nunca escribir en una copia real de GeoLibre (portal/geolibre/) durante las pruebas
    monkeypatch.setenv("GEOPORTAL_GEOLIBRE_DIR", str(tmp_path / "geolibre-sin-instalar"))
    monkeypatch.delenv("GEOPORTAL_PORTAL_DIR", raising=False)

    from app import config, db

    config.reset_settings()
    db.reset_engine()
    import importlib

    import app.main as main

    importlib.reload(main)
    from fastapi.testclient import TestClient

    with TestClient(main.create_app()) as c:
        yield c
    db.reset_engine()
    config.reset_settings()


@pytest.fixture()
def token(client) -> str:
    r = client.post("/api/auth/ingresar", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def auth(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def geojson_file(tmp_path) -> Path:
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"nombre": f"Humedal {i}", "area_ha": 10.5 * i},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-77.3 + i * 0.01, 1.2], [-77.29 + i * 0.01, 1.2], [-77.29 + i * 0.01, 1.21], [-77.3 + i * 0.01, 1.2]]],
                },
            }
            for i in range(1, 6)
        ],
    }
    path = tmp_path / "humedales.geojson"
    path.write_text(json.dumps(fc), encoding="utf-8")
    return path


@pytest.fixture()
def shapefile_zip(tmp_path) -> Path:
    """Shapefile en MAGNA-SIRGAS Origen Nacional (EPSG:9377), comprimido."""
    import geopandas as gpd
    from shapely.geometry import LineString

    gdf = gpd.GeoDataFrame(
        {"NOMBRE_GEO": ["Río Guáitara", "Río Pasto"], "ORDEN": [3, 2]},
        geometry=[
            LineString([(4590000, 1700000), (4600000, 1710000)]),
            LineString([(4610000, 1720000), (4615000, 1730000)]),
        ],
        crs="EPSG:9377",
    )
    folder = tmp_path / "shp"
    folder.mkdir()
    gdf.to_file(folder / "drenajes.shp")
    out = tmp_path / "drenajes.zip"
    with zipfile.ZipFile(out, "w") as zf:
        for f in folder.iterdir():
            zf.write(f, f.name)
    return out


@pytest.fixture()
def csv_file(tmp_path) -> Path:
    path = tmp_path / "estaciones.csv"
    path.write_text(
        "codigo;nombre;latitud;longitud\nE1;Estación Galeras;1,2208;-77,3594\nE2;Estación Tumaco;1,8;-78,76\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def raster_file(tmp_path) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    data = np.linspace(500, 4200, 120 * 100, dtype="float32").reshape(100, 120)
    data[:5, :5] = -9999
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=120,
        height=100,
        count=1,
        dtype="float32",
        crs="EPSG:9377",
        transform=from_origin(4590000, 1730000, 100, 100),
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)
    return path
