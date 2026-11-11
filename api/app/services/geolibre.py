"""Construcción de proyectos GeoLibre (``.geolibre`` / ``.geolibre.json``).

El esquema sigue ``docs/project-format.md`` de GeoLibre
(https://github.com/opengeos/GeoLibre). Cada capa publicada del geoportal se
traduce a una capa GeoLibre:

* vector pequeño → capa ``geojson`` con las entidades embebidas y ``source.url``
  apuntando a la API (GeoLibre puede refrescarla).
* vector grande → capa ``geojson`` servida por URL mediante el control vectorial
  (``sourceKind: maplibre-gl-vector``) para no inflar el archivo del proyecto.
* ráster → capa ``cog`` apuntando a la COG publicada.

Las categorías del geoportal se convierten en carpetas (``layerGroups``) del
panel de capas.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any

from ..config import Settings
from ..models import Category, Layer

PROJECT_VERSION = "0.2.0"

DEFAULT_LAYER_STYLE: dict[str, Any] = {
    "minZoom": 0,
    "maxZoom": 24,
    "fillColor": "#10A13B",
    "strokeColor": "#0B6E28",
    "strokeWidth": 1.5,
    "strokeWidthUnit": "pixels",
    "strokeOpacity": 1,
    "strokeDash": [],
    "strokeBlur": 0,
    "fillOpacity": 0.5,
    "circleRadius": 6,
    "textColor": "#383838",
    "textHaloColor": "#ffffff",
    "textHaloWidth": 2,
    "textSize": 13,
    "vectorStyleMode": "single",
    "pointRenderer": "single",
    "rasterBrightnessMin": 0,
    "rasterBrightnessMax": 1,
    "rasterSaturation": 0,
    "rasterContrast": 0,
    "rasterHueRotate": 0,
    "blendMode": "normal",
}

# Correspondencia simbología geoportal → estilo GeoLibre
_STYLE_KEYS = {
    "fillColor": "fillColor",
    "strokeColor": "strokeColor",
    "strokeWidth": "strokeWidth",
    "fillOpacity": "fillOpacity",
    "circleRadius": "circleRadius",
}

# Rampas del geoportal → mapas de color de GeoLibre (nombres de matplotlib/rio-tiler)
_COLORMAPS = {
    "terreno": "terrain",
    "verdes": "greens",
    "ndvi": "rdylgn",
    "agua": "blues",
    "viridis": "viridis",
    "calor": "ylorrd",
    "grises": "gray",
}


def _stable_uuid(*parts: str) -> str:
    """UUID determinista: el mismo geodato conserva su id entre descargas."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "geoportal-ambiente:" + ":".join(parts)))


def layer_urls(settings: Settings, layer: Layer) -> dict[str, str]:
    base = f"{settings.public_base_url}/api/capas/{layer.slug}"
    urls = {
        "ficha": base,
        "datos": f"{base}/datos" + (".geojson" if layer.kind == "vector" else ".tif"),
        "proyecto": f"{base}/proyecto.geolibre",
    }
    if layer.kind == "raster":
        urls["vista_previa"] = f"{base}/vista-previa.png"
    if layer.downloadable:
        urls["descarga"] = f"{base}/descarga"
        urls["descarga_original"] = f"{base}/descarga?original=1"
    return urls


def geolibre_open_url(settings: Settings, project_url: str, viewer: bool = True) -> str:
    from urllib.parse import quote

    url = f"{settings.geolibre_url}/?url={quote(project_url, safe='')}"
    if viewer:
        url += "&layout=viewer"
    return url


def _descriptive_metadata(layer: Layer, settings: Settings) -> dict[str, Any]:
    meta: dict[str, Any] = {"title": layer.title}
    if layer.description:
        meta["abstract"] = layer.description
    if layer.keywords:
        meta["keywords"] = list(layer.keywords)
    if layer.license:
        meta["license"] = layer.license
    attribution = layer.source or "Gobernación de Nariño — Secretaría de Ambiente y Desarrollo Sostenible"
    meta["attribution"] = attribution
    contact: dict[str, str] = {"organization": attribution}
    if layer.author:
        contact["name"] = layer.author
    if layer.contact_email and "@" in layer.contact_email:
        contact["email"] = layer.contact_email
    meta["contact"] = contact
    if layer.lineage:
        meta["lineage"] = layer.lineage
    if layer.data_date:
        meta["temporalExtent"] = {"start": layer.data_date, "end": layer.data_date}
    meta["links"] = [
        {"href": f"{settings.public_base_url}/?capa={layer.slug}", "rel": "about", "title": "Ficha en el geoportal"}
    ]
    return meta


def _popup(layer: Layer) -> dict[str, Any] | None:
    fields = [f for f in (layer.popup_fields or []) if f]
    if not fields and not layer.label_field:
        return None
    popup: dict[str, Any] = {"click": True, "hover": bool(layer.label_field)}
    if layer.label_field:
        popup["titleField"] = layer.label_field
    if fields:
        popup["fields"] = [{"field": f} for f in fields]
    return popup


def build_layer(layer: Layer, settings: Settings, group_id: str | None = None) -> dict[str, Any]:
    style = copy.deepcopy(DEFAULT_LAYER_STYLE)
    for src_key, dst_key in _STYLE_KEYS.items():
        if src_key in (layer.style or {}):
            style[dst_key] = layer.style[src_key]
    if layer.geometry_type == "Línea":
        # En GeoLibre el color de línea es el del trazo
        style["strokeColor"] = (layer.style or {}).get("strokeColor", style["fillColor"])

    urls = layer_urls(settings, layer)
    layer_id = _stable_uuid("capa", layer.slug)
    out: dict[str, Any] = {
        "id": layer_id,
        "name": layer.title,
        "visible": bool(layer.visible_by_default),
        "opacity": float(layer.opacity if layer.opacity is not None else 1),
        "style": style,
        "metadata": {},
        "descriptiveMetadata": _descriptive_metadata(layer, settings),
        "capabilities": {
            "query": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": bool(layer.downloadable),
        },
    }
    if group_id:
        out["groupId"] = group_id

    if layer.kind == "raster":
        rstyle = layer.style or {}
        info = layer.raster_info or {}
        stats = info.get("stats", {})
        raster_state: dict[str, Any] = {}
        if info.get("bands", 1) >= 3 and rstyle.get("rasterMode", "rgb") == "rgb":
            raster_state.update({"bands": [1, 2, 3], "mode": "rgb"})
        else:
            raster_state.update(
                {
                    "bands": [int(rstyle.get("band", 1))],
                    "mode": "single",
                    "colormap": _COLORMAPS.get(str(rstyle.get("colorRamp", "terreno")), "terrain"),
                }
            )
            vmin = rstyle.get("rasterMin", stats.get("p2", stats.get("min")))
            vmax = rstyle.get("rasterMax", stats.get("p98", stats.get("max")))
            if vmin is not None and vmax is not None:
                raster_state["rescale"] = [[float(vmin), float(vmax)]]
        out.update(
            {
                "type": "cog",
                "source": {"type": "raster", "url": urls["datos"]},
                "sourcePath": urls["datos"],
                "metadata": {
                    "customLayerType": "raster",
                    "externalDeckLayer": True,
                    "externalNativeLayer": True,
                    "identifiable": False,
                    "nativeLayerIds": [layer_id],
                    "panelCollapsed": True,
                    "rasterOverlayMode": "interleaved",
                    "rasterSource": "url",
                    "rasterState": raster_state,
                    "sourceIds": [],
                    "sourceKind": "maplibre-gl-raster",
                },
            }
        )
        return out

    # Vector
    out["type"] = "geojson"
    popup = _popup(layer)
    if popup:
        out["popup"] = popup
    processed = Path(layer.processed_path) if layer.processed_path else None
    size_mb = processed.stat().st_size / 1024**2 if processed and processed.exists() else 0
    if processed and processed.exists() and size_mb <= settings.inline_max_mb:
        with processed.open("r", encoding="utf-8") as fh:
            out["geojson"] = json.load(fh)
        out["source"] = {"type": "geojson", "url": urls["datos"]}
        out["sourcePath"] = urls["datos"]
    else:
        out["source"] = {"type": "geojson", "url": urls["datos"]}
        out["sourcePath"] = urls["datos"]
        out["metadata"] = {
            "sourceKind": "maplibre-gl-vector",
            "externalNativeLayer": True,
            "controlOwnsPaint": True,
            "identifiable": False,
            "nativeLayerIds": [],
            "sourceIds": [f"{layer_id}-source"],
            "vectorSource": "url",
            "vectorState": {"renderMode": "geojson", "format": "geojson"},
        }
    return out


def _view_for(bboxes: list[list[float]], settings: Settings) -> dict[str, Any]:
    view: dict[str, Any] = {
        "center": list(settings.map_center),
        "zoom": settings.map_zoom,
        "bearing": 0,
        "pitch": 0,
    }
    valid = [b for b in bboxes if b and len(b) == 4]
    if valid:
        west = min(b[0] for b in valid)
        south = min(b[1] for b in valid)
        east = max(b[2] for b in valid)
        north = max(b[3] for b in valid)
        view["bbox"] = [west, south, east, north]
        view["center"] = [(west + east) / 2, (south + north) / 2]
        span = max(east - west, north - south, 1e-6)
        import math

        view["zoom"] = max(2.0, min(16.0, math.log2(360 / span) - 0.3))
    return view


def build_project(
    layers: list[Layer],
    settings: Settings,
    name: str | None = None,
    categories: list[Category] | None = None,
) -> dict[str, Any]:
    """Arma un proyecto GeoLibre con las capas dadas, agrupadas por categoría."""
    groups: list[dict[str, Any]] = []
    group_ids: dict[int, str] = {}
    cats = {c.id: c for c in (categories or [])}
    # Orden del visor: categorías por su posición, luego capas por su posición
    cat_pos = {c.id: (c.position, c.name) for c in (categories or [])}
    layers = sorted(
        layers,
        key=lambda la: (
            cat_pos.get(la.category_id, (10**6, "")) if la.category_id else (10**6 + 1, ""),
            la.position,
            la.title,
        ),
    )
    for layer in layers:
        if layer.category_id and layer.category_id not in group_ids:
            cat = cats.get(layer.category_id) or layer.category
            if cat is None:
                continue
            gid = _stable_uuid("categoria", cat.slug)
            group_ids[layer.category_id] = gid
            groups.append(
                {"id": gid, "name": cat.name, "parentId": None, "collapsed": False, "visible": True, "opacity": 1}
            )

    built = [build_layer(layer, settings, group_ids.get(layer.category_id or -1)) for layer in layers]
    # GeoLibre dibuja el arreglo de abajo hacia arriba y lista en el panel la
    # última capa primero: se invierte para que la primera categoría quede arriba.
    # Las capas de una misma carpeta siguen siendo contiguas.
    built.reverse()

    project: dict[str, Any] = {
        "version": PROJECT_VERSION,
        "name": name or settings.project_name,
        "mapView": _view_for([layer.bbox for layer in layers if layer.bbox], settings),
        "basemapStyleUrl": settings.basemap_url,
        "basemapVisible": True,
        "basemapOpacity": 1,
        "layers": built,
        "styles": {item["id"]: item["style"] for item in built},
        "preferences": {
            "map": {
                "restrictBounds": False,
                "bounds": [-180, -85, 180, 85],
                "minZoom": 0,
                "maxZoom": 24,
                "maxPitch": 85,
                "renderWorldCopies": True,
            },
            "environmentVariables": [],
        },
        "metadata": {
            "generator": "Geoportal Ambiental — Gobernación de Nariño",
            "portal": settings.public_base_url,
        },
    }
    if groups:
        project["layerGroups"] = groups
    return project
