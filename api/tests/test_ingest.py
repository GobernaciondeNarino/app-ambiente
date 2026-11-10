from __future__ import annotations

import json
import zipfile

import pytest

from app.services.ingest import IngestError, IngestOptions, ingest_file


def test_geojson(geojson_file, tmp_path):
    r = ingest_file(geojson_file, tmp_path / "out")
    assert r.kind == "vector"
    assert r.feature_count == 5
    assert r.geometry_type == "Polígono"
    assert r.source_format == "GeoJSON"
    names = [a["name"] for a in r.attributes]
    assert names == ["nombre", "area_ha"]
    assert json.loads(r.processed_path.read_text())["features"]


def test_shapefile_reprojected_from_magna(shapefile_zip, tmp_path):
    r = ingest_file(shapefile_zip, tmp_path / "out")
    assert r.source_format == "Shapefile (ZIP)"
    assert r.geometry_type == "Línea"
    assert "9377" in r.source_crs
    west, south, east, north = r.bbox
    # Debe caer en Nariño (aprox. -79.1 a -76.8 lon, 0.3 a 2.7 lat)
    assert -79.5 < west < east < -76 and 0 < south < north < 3


def test_shapefile_without_prj_requires_epsg(shapefile_zip, tmp_path):
    stripped = tmp_path / "sinprj.zip"
    with zipfile.ZipFile(shapefile_zip) as src, zipfile.ZipFile(stripped, "w") as dst:
        for item in src.infolist():
            if not item.filename.endswith(".prj"):
                dst.writestr(item, src.read(item))
    with pytest.raises(IngestError, match="EPSG"):
        ingest_file(stripped, tmp_path / "out")
    r = ingest_file(stripped, tmp_path / "out2", IngestOptions(source_epsg=9377))
    assert r.bbox[0] < -76


def test_csv_with_comma_decimals(csv_file, tmp_path):
    r = ingest_file(csv_file, tmp_path / "out")
    assert r.feature_count == 2
    assert r.geometry_type == "Punto"
    assert r.bbox[0] == pytest.approx(-78.76)


def test_raster_cog_and_preview(raster_file, tmp_path):
    r = ingest_file(raster_file, tmp_path / "out")
    assert r.kind == "raster"
    assert r.processed_path.name == "datos.tif"
    assert r.preview_path and r.preview_path.stat().st_size > 0
    assert r.raster_info["bands"] == 1
    assert r.raster_info["stats"]["max"] <= 4200
    assert len(r.raster_info["corners"]) == 4


def test_rejects_unknown_format(tmp_path):
    bad = tmp_path / "x.docx"
    bad.write_text("nada")
    with pytest.raises(IngestError, match="no admitido"):
        ingest_file(bad, tmp_path / "out")


def test_zip_slip_is_blocked(tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../../fuera.geojson", "{}")
    with pytest.raises(IngestError, match="rutas no permitidas"):
        ingest_file(evil, tmp_path / "out")
