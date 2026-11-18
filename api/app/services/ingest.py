"""Ingesta de geodatos.

Convierte lo que sube el administrador en dos productos normalizados:

* **Vector** → GeoJSON RFC 7946 en EPSG:4326 (lo leen tanto el visor del
  geoportal como GeoLibre).
* **Ráster** → Cloud Optimized GeoTIFF en EPSG:3857 (lo abre GeoLibre) y una
  vista previa PNG georreferenciada para el visor del geoportal.

Formatos de entrada admitidos: GeoJSON, Shapefile comprimido (.zip),
GeoPackage, KML/KMZ, GML, FlatGeobuf, GeoParquet, CSV con coordenadas o WKT,
GeoTIFF/COG, ERDAS IMG, ASCII Grid y JPEG2000.
"""

from __future__ import annotations

import json
import math
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

VECTOR_EXTENSIONS = {".geojson", ".json", ".gpkg", ".kml", ".gml", ".fgb", ".parquet", ".geoparquet", ".csv", ".shp"}
RASTER_EXTENSIONS = {".tif", ".tiff", ".img", ".asc", ".jp2", ".vrt"}
ARCHIVE_EXTENSIONS = {".zip", ".kmz"}
ACCEPTED_EXTENSIONS = VECTOR_EXTENSIONS | RASTER_EXTENSIONS | ARCHIVE_EXTENSIONS

# Protección contra archivos comprimidos maliciosos
MAX_ZIP_MEMBERS = 2000
MAX_UNZIPPED_BYTES = 4 * 1024**3

LON_NAMES = ("lon", "long", "longitud", "longitude", "lng", "x", "este", "coord_x", "x_coord")
LAT_NAMES = ("lat", "latitud", "latitude", "y", "norte", "coord_y", "y_coord")
WKT_NAMES = ("wkt", "geometry", "geometria", "geom", "the_geom")


class IngestError(ValueError):
    """Error comprensible para el usuario del administrador."""


@dataclass
class IngestOptions:
    source_epsg: int | None = None  # se usa solo si el archivo no declara CRS
    layer_name: str | None = None  # capa dentro de un GeoPackage/KML multi-capa
    csv_lon: str | None = None
    csv_lat: str | None = None
    coordinate_precision: int = 6


@dataclass
class IngestResult:
    kind: str  # vector | raster
    source_format: str
    processed_path: Path
    preview_path: Path | None = None
    geometry_type: str = ""
    feature_count: int = 0
    bbox: list[float] | None = None
    source_crs: str = ""
    attributes: list[dict[str, Any]] = field(default_factory=list)
    raster_info: dict[str, Any] | None = None
    sublayers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------


def _safe_extract(archive: Path, dest: Path) -> None:
    """Extrae un ZIP evitando *zip-slip* y bombas de descompresión."""
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if len(members) > MAX_ZIP_MEMBERS:
            raise IngestError("El archivo comprimido contiene demasiados archivos.")
        total = sum(m.file_size for m in members)
        if total > MAX_UNZIPPED_BYTES:
            raise IngestError("El archivo comprimido es demasiado grande al descomprimirse.")
        root = dest.resolve()
        for member in members:
            target = (dest / member.filename).resolve()
            if target != root and not target.is_relative_to(root):
                raise IngestError("El archivo comprimido contiene rutas no permitidas.")
        zf.extractall(dest)


def _find_dataset(folder: Path) -> Path:
    """Elige el conjunto de datos principal dentro de una carpeta extraída."""
    candidates: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or "__MACOSX" in path.parts:
            continue
        candidates.append(path)
    priority = [".shp", ".gpkg", ".geojson", ".json", ".kml", ".gml", ".fgb", ".parquet", ".tif", ".tiff", ".img", ".jp2", ".asc", ".csv"]
    for ext in priority:
        found = [p for p in candidates if p.suffix.lower() == ext]
        if found:
            if ext == ".shp" and len(found) > 1:
                raise IngestError(
                    "El ZIP contiene varios Shapefile ("
                    + ", ".join(p.name for p in found[:6])
                    + "). Cargue un Shapefile por archivo."
                )
            return found[0]
    raise IngestError("No se encontró un geodato reconocible dentro del archivo comprimido.")


def _crs_label(crs: Any) -> str:
    if crs is None:
        return ""
    try:
        auth = crs.to_authority()
        if auth:
            return f"{auth[0]}:{auth[1]} — {crs.name}"
        return crs.name
    except Exception:  # pragma: no cover - defensivo
        return str(crs)[:120]


def _geometry_family(types: list[str]) -> str:
    families = set()
    for t in types:
        if not t:
            continue
        if "Point" in t:
            families.add("Punto")
        elif "Line" in t:
            families.add("Línea")
        elif "Polygon" in t:
            families.add("Polígono")
        else:
            families.add(t)
    if not families:
        return ""
    if len(families) == 1:
        return families.pop()
    return "Mixta"


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return str(value) if not isinstance(value, (int, str, bool)) else value


def _describe_attributes(gdf: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        series = gdf[col]
        dtype = str(series.dtype)
        if "int" in dtype:
            kind = "entero"
        elif "float" in dtype:
            kind = "decimal"
        elif "datetime" in dtype:
            kind = "fecha"
        elif "bool" in dtype:
            kind = "booleano"
        else:
            kind = "texto"
        sample = []
        try:
            for v in series.dropna().unique()[:5]:
                sample.append(_json_safe(v))
        except TypeError:
            pass
        info: dict[str, Any] = {"name": str(col), "type": kind, "sample": sample}
        if kind in ("entero", "decimal") and series.notna().any():
            info["min"] = _json_safe(series.min())
            info["max"] = _json_safe(series.max())
        try:
            info["distinct"] = int(series.nunique())
        except TypeError:
            pass
        out.append(info)
    return out


# --------------------------------------------------------------------------
# Vector
# --------------------------------------------------------------------------


def _read_csv(path: Path, opts: IngestOptions) -> Any:
    import geopandas as gpd
    import pandas as pd
    from shapely import wkt as shapely_wkt

    df = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if df is None or df.empty:
        raise IngestError("El CSV está vacío o no se pudo leer.")

    lower = {c.lower().strip(): c for c in df.columns}
    lon_col = opts.csv_lon or next((lower[n] for n in LON_NAMES if n in lower), None)
    lat_col = opts.csv_lat or next((lower[n] for n in LAT_NAMES if n in lower), None)
    wkt_col = next((lower[n] for n in WKT_NAMES if n in lower), None)

    if lon_col and lat_col and lon_col in df.columns and lat_col in df.columns:
        x = pd.to_numeric(df[lon_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        y = pd.to_numeric(df[lat_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        df = df.loc[x.notna() & y.notna()].copy()
        x, y = x.loc[df.index], y.loc[df.index]
        geometry = gpd.points_from_xy(x, y)
        projected = bool(len(x)) and (x.abs().max() > 180 or y.abs().max() > 90)
    elif wkt_col:
        geometry = df[wkt_col].astype(str).map(lambda s: shapely_wkt.loads(s) if s and s != "nan" else None)
        df = df.drop(columns=[wkt_col])
        projected = False
        bounds = [g.bounds for g in geometry if g is not None]
        if bounds:
            projected = any(abs(b[0]) > 180 or abs(b[1]) > 90 for b in bounds)
    else:
        raise IngestError(
            "El CSV debe tener columnas de coordenadas (p. ej. 'longitud' y 'latitud', 'x' y 'y') "
            "o una columna 'wkt'."
        )

    if projected:
        if not opts.source_epsg:
            raise IngestError(
                "Las coordenadas del CSV parecen planas (metros). Indique el EPSG de origen, "
                "por ejemplo 9377 (MAGNA-SIRGAS Origen Nacional) o 3116 (MAGNA Bogotá)."
            )
        crs = f"EPSG:{opts.source_epsg}"
    else:
        crs = f"EPSG:{opts.source_epsg}" if opts.source_epsg else "EPSG:4326"
    return gpd.GeoDataFrame(df, geometry=geometry, crs=crs)


def _ingest_vector(path: Path, out_dir: Path, opts: IngestOptions, source_format: str) -> IngestResult:
    import geopandas as gpd
    import pyogrio
    from shapely import make_valid

    warnings: list[str] = []
    sublayers: list[str] = []
    ext = path.suffix.lower()

    if ext == ".csv":
        gdf = _read_csv(path, opts)
    elif ext in (".parquet", ".geoparquet"):
        try:
            gdf = gpd.read_parquet(path)
        except Exception as exc:
            raise IngestError(f"No se pudo leer el GeoParquet: {exc}") from exc
    else:
        try:
            layers = pyogrio.list_layers(path)
            sublayers = [str(row[0]) for row in layers]
        except Exception:
            sublayers = []
        layer = opts.layer_name if opts.layer_name in sublayers else (sublayers[0] if sublayers else None)
        if len(sublayers) > 1:
            warnings.append(
                f"El archivo contiene {len(sublayers)} capas; se cargó «{layer}». "
                "Puede elegir otra en el campo «Capa interna»."
            )
        try:
            gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
        except Exception as exc:
            raise IngestError(f"No se pudo leer el archivo vectorial: {exc}") from exc

    if gdf.empty:
        raise IngestError("El geodato no contiene entidades.")
    if gdf.geometry is None:
        raise IngestError("El archivo no tiene geometrías.")

    source_crs = _crs_label(gdf.crs)
    if gdf.crs is None:
        if not opts.source_epsg:
            raise IngestError(
                "El archivo no declara su sistema de referencia (falta el .prj). "
                "Indique el EPSG de origen, por ejemplo 9377, 3116, 4686 o 4326."
            )
        gdf = gdf.set_crs(epsg=opts.source_epsg)
        source_crs = _crs_label(gdf.crs) + " (indicado por el usuario)"

    # Limpieza de geometrías
    before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if len(gdf) < before:
        warnings.append(f"Se descartaron {before - len(gdf)} entidades sin geometría.")
    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        gdf.loc[invalid, gdf.geometry.name] = gdf.loc[invalid, gdf.geometry.name].apply(make_valid)
        warnings.append(f"Se repararon {int(invalid.sum())} geometrías inválidas.")

    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Columnas no serializables → texto
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        dtype = str(gdf[col].dtype)
        if dtype == "object" or "datetime" in dtype:
            gdf[col] = gdf[col].map(lambda v: None if v is None or (isinstance(v, float) and math.isnan(v)) else str(v) if not isinstance(v, (str, int, float, bool)) else v)

    minx, miny, maxx, maxy = (float(v) for v in gdf.total_bounds)
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        raise IngestError("No se pudo calcular la extensión del geodato.")
    if not (-180 <= minx <= 180 and -90 <= miny <= 90 and -180 <= maxx <= 180 and -90 <= maxy <= 90):
        raise IngestError(
            "Las coordenadas transformadas quedaron fuera de rango. Revise el EPSG de origen."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "datos.geojson"
    if out_path.exists():
        out_path.unlink()
    gdf.to_file(
        out_path,
        driver="GeoJSON",
        engine="pyogrio",
        layer_options={
            "RFC7946": "YES",
            "COORDINATE_PRECISION": str(opts.coordinate_precision),
            "WRITE_BBOX": "NO",
        },
    )

    return IngestResult(
        kind="vector",
        source_format=source_format,
        processed_path=out_path,
        geometry_type=_geometry_family(list(gdf.geom_type.unique())),
        feature_count=int(len(gdf)),
        bbox=[round(minx, 6), round(miny, 6), round(maxx, 6), round(maxy, 6)],
        source_crs=source_crs,
        attributes=_describe_attributes(gdf),
        sublayers=sublayers,
        warnings=warnings,
    )


# --------------------------------------------------------------------------
# Ráster
# --------------------------------------------------------------------------

# Rampas de color sencillas (sin depender de matplotlib)
COLOR_RAMPS: dict[str, list[str]] = {
    "terreno": ["#333399", "#0888ee", "#00cc66", "#80e680", "#ffff99", "#bfad77", "#805c54", "#bfadaa", "#ffffff"],
    "verdes": ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"],
    "ndvi": ["#a50026", "#f46d43", "#fee08b", "#d9ef8b", "#66bd63", "#006837"],
    "agua": ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
    "viridis": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    "calor": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    "grises": ["#000000", "#ffffff"],
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _apply_ramp(values: np.ndarray, vmin: float, vmax: float, ramp: str) -> np.ndarray:
    stops = [_hex_to_rgb(c) for c in COLOR_RAMPS.get(ramp, COLOR_RAMPS["terreno"])]
    span = vmax - vmin if vmax > vmin else 1.0
    t = np.clip((values - vmin) / span, 0, 1)
    positions = np.linspace(0, 1, len(stops))
    rgb = np.zeros(values.shape + (3,), dtype=np.uint8)
    for channel in range(3):
        rgb[..., channel] = np.interp(t, positions, [s[channel] for s in stops]).astype(np.uint8)
    return rgb


def render_raster_preview(cog_path: Path, out_path: Path, info: dict[str, Any], style: dict[str, Any] | None = None) -> None:
    """Genera un PNG RGBA de la COG (EPSG:3857) para el visor del geoportal."""
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling

    style = style or {}
    with rasterio.open(cog_path) as src:
        scale = max(src.width, src.height) / 2048
        width = max(1, int(src.width / max(scale, 1)))
        height = max(1, int(src.height / max(scale, 1)))
        count = src.count
        bands = [1, 2, 3] if count >= 3 and style.get("rasterMode", "rgb" if count >= 3 else "single") == "rgb" else [int(style.get("band", 1))]
        data = src.read(bands, out_shape=(len(bands), height, width), resampling=Resampling.bilinear, masked=True)

    if len(bands) == 3:
        rgb = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(3):
            band = data[i].astype("float64")
            valid = band.compressed()
            lo, hi = (np.percentile(valid, [2, 98]) if valid.size else (0, 1))
            rgb[..., i] = (np.clip((band.filled(lo) - lo) / ((hi - lo) or 1), 0, 1) * 255).astype(np.uint8)
        mask = np.ma.getmaskarray(data).any(axis=0)
    else:
        band = data[0].astype("float64")
        stats = info.get("stats", {})
        vmin = float(style.get("rasterMin", stats.get("p2", stats.get("min", 0))))
        vmax = float(style.get("rasterMax", stats.get("p98", stats.get("max", 1))))
        rgb = _apply_ramp(band.filled(vmin), vmin, vmax, str(style.get("colorRamp", "terreno")))
        mask = np.ma.getmaskarray(band)

    alpha = np.where(mask, 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA").save(out_path, optimize=True)


def _ingest_raster(path: Path, out_dir: Path, opts: IngestOptions, source_format: str) -> IngestResult:
    import rasterio
    from pyproj import Transformer
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.shutil import copy as rio_copy
    from rasterio.vrt import WarpedVRT

    warnings: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    cog_path = out_dir / "datos.tif"
    try:
        with rasterio.open(path) as src:
            src_crs = src.crs
            if src_crs is None:
                if not opts.source_epsg:
                    raise IngestError(
                        "El ráster no declara su sistema de referencia. Indique el EPSG de origen."
                    )
                src_crs = CRS.from_epsg(opts.source_epsg)
            source_crs = src_crs.to_string()
            try:
                from pyproj import CRS as PCRS

                source_crs = _crs_label(PCRS.from_user_input(src_crs.to_wkt()))
            except Exception:
                pass
            nodata = src.nodata
            dtype = src.dtypes[0]
            resampling = Resampling.nearest if "int" in dtype and src.count == 1 else Resampling.bilinear
            with WarpedVRT(src, src_crs=src_crs, crs="EPSG:3857", resampling=resampling, nodata=nodata) as vrt:
                rio_copy(
                    vrt,
                    cog_path,
                    driver="COG",
                    COMPRESS="DEFLATE",
                    PREDICTOR="2" if "float" not in dtype else "3",
                    OVERVIEWS="AUTO",
                    BIGTIFF="IF_SAFER",
                )
    except IngestError:
        raise
    except rasterio.errors.RasterioError as exc:
        raise IngestError(f"No se pudo procesar el ráster: {exc}") from exc

    with rasterio.open(cog_path) as cog:
        left, bottom, right, top = cog.bounds
        band = cog.read(1, out_shape=(1, min(cog.height, 1024), min(cog.width, 1024)), masked=True)
        valid = band.compressed().astype("float64")
        stats: dict[str, float] = {}
        if valid.size:
            stats = {
                "min": float(valid.min()),
                "max": float(valid.max()),
                "mean": float(valid.mean()),
                "p2": float(np.percentile(valid, 2)),
                "p98": float(np.percentile(valid, 98)),
            }
        info = {
            "width": cog.width,
            "height": cog.height,
            "bands": cog.count,
            "dtype": cog.dtypes[0],
            "nodata": _json_safe(cog.nodata),
            "resolution_m": round(abs(cog.transform.a), 3),
            "stats": stats,
        }

    to_wgs = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    west, south = to_wgs.transform(left, bottom)
    east, north = to_wgs.transform(right, top)
    info["corners"] = [[west, north], [east, north], [east, south], [west, south]]

    preview_path = out_dir / "vista_previa.png"
    render_raster_preview(cog_path, preview_path, info)

    return IngestResult(
        kind="raster",
        source_format=source_format,
        processed_path=cog_path,
        preview_path=preview_path,
        geometry_type="Ráster",
        feature_count=0,
        bbox=[round(west, 6), round(south, 6), round(east, 6), round(north, 6)],
        source_crs=source_crs,
        raster_info=info,
        warnings=warnings,
    )


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------

FORMAT_NAMES = {
    ".geojson": "GeoJSON",
    ".json": "GeoJSON",
    ".shp": "Shapefile",
    ".gpkg": "GeoPackage",
    ".kml": "KML",
    ".kmz": "KMZ",
    ".gml": "GML",
    ".fgb": "FlatGeobuf",
    ".parquet": "GeoParquet",
    ".geoparquet": "GeoParquet",
    ".csv": "CSV",
    ".tif": "GeoTIFF",
    ".tiff": "GeoTIFF",
    ".img": "ERDAS Imagine",
    ".asc": "ASCII Grid",
    ".jp2": "JPEG 2000",
    ".vrt": "VRT",
}


def ingest_file(path: Path, out_dir: Path, opts: IngestOptions | None = None) -> IngestResult:
    """Procesa ``path`` y escribe los productos normalizados en ``out_dir``."""
    opts = opts or IngestOptions()
    ext = path.suffix.lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise IngestError(
            f"Formato «{ext or 'sin extensión'}» no admitido. Formatos válidos: "
            + ", ".join(sorted(ACCEPTED_EXTENSIONS))
        )

    workdir = Path(tempfile.mkdtemp(prefix="ingesta-", dir=out_dir.parent if out_dir.parent.exists() else None))
    try:
        target = path
        source_format = FORMAT_NAMES.get(ext, ext.lstrip(".").upper())
        if ext in ARCHIVE_EXTENSIONS:
            if not zipfile.is_zipfile(path):
                raise IngestError("El archivo comprimido está dañado o no es un ZIP válido.")
            _safe_extract(path, workdir)
            target = _find_dataset(workdir)
            inner = target.suffix.lower()
            source_format = "KMZ" if ext == ".kmz" else FORMAT_NAMES.get(inner, inner.upper())
            if inner == ".shp":
                source_format = "Shapefile (ZIP)"
        elif ext == ".shp":
            raise IngestError(
                "Para Shapefile cargue un .zip con todos sus archivos (.shp, .shx, .dbf y .prj)."
            )

        if target.suffix.lower() in RASTER_EXTENSIONS:
            return _ingest_raster(target, out_dir, opts, source_format)
        return _ingest_vector(target, out_dir, opts, source_format)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def read_geojson_head(path: Path, limit: int = 50) -> dict[str, Any]:
    """Devuelve las primeras ``limit`` entidades (para la tabla de atributos)."""
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    feats = data.get("features", [])[:limit]
    return {"type": "FeatureCollection", "features": feats}
