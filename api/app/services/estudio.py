"""Estudio SIG: GeoLibre integrado en el geoportal (edición Docker/Python).

Misma lógica que portal/api/lib/geolibre.php: se instala la compilación web
oficial de GeoLibre en portal/geolibre/ y se configura con sus mecanismos
oficiales (deployment.json y archivo de interfaz para ?settingsUrl=).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from fastapi import HTTPException

from ..config import Settings, origin_of

CAPACIDADES = ["project:edit", "data:add", "processing:run", "export:data", "plugins:install", "settings:manage"]
MENUS = ["project", "edit", "view", "addData", "processing", "controls", "plugins", "help"]
NIVELES = ["beginner", "intermediate", "advanced"]
ACENTOS = ["blue", "violet", "emerald", "rose", "amber", "custom"]
IDIOMAS = ["es", "en", "pt", "fr", "de", "it", "nl", "ar", "az", "fa", "he", "hi", "id", "ja", "ka", "ko", "ru", "th", "tr", "vi", "zh"]
TIPOS_SERVICIO = ["wms", "wfs", "wmts", "xyz", "arcgis", "csw"]
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
RAIZ_REPO = Path(__file__).resolve().parents[3]


def ajustes_defecto() -> dict[str, Any]:
    return {
        "modo": "completo",
        "nombre": "Geoportal Ambiental",
        "bienvenida": False,
        "idioma": "es",
        "acento": "custom",
        "color_acento": "#10A13B",
        "nivel": "advanced",
        "bloquear_nivel": False,
        "menus_ocultos": [],
        "elementos_ocultos": [],
        "fuentes_ocultas": [],
        "complementos_ocultos": [],
        "capacidades": list(CAPACIDADES),
        "complementos_activos": [],
        "complementos_bloqueados": [],
        "instalar_complementos": True,
        "registro_complementos": "",
        "panel_inicial": "",
        "mapas_regionales": False,
        "servicios_predeterminados": True,
        "servicios": [],
        "compartir_publico": False,
        "url_compartir": "",
        "url_colaboracion": "",
        "overpass_url": "",
        "geolens_url": "off",
    }


def carpeta_geolibre(settings: Settings) -> Path:
    env = os.getenv("GEOPORTAL_GEOLIBRE_DIR")
    if env:
        return Path(env)
    portal = os.getenv("GEOPORTAL_PORTAL_DIR")
    return (Path(portal) if portal else RAIZ_REPO / "portal") / "geolibre"


def version_fijada() -> dict[str, Any]:
    for ruta in (RAIZ_REPO / "portal" / "api" / "geolibre-version.json", Path("/app/geolibre-version.json")):
        if ruta.is_file():
            return json.loads(ruta.read_text(encoding="utf-8"))
    return {}


def _ruta_ajustes(settings: Settings) -> Path:
    return settings.data_dir / "geolibre-ajustes.json"


def ajustes(settings: Settings) -> dict[str, Any]:
    guardados: dict[str, Any] = {}
    ruta = _ruta_ajustes(settings)
    if ruta.is_file():
        try:
            guardados = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            guardados = {}
    return ajustes_defecto() | (guardados if isinstance(guardados, dict) else {})


def preferencia_url(settings: Settings) -> str:
    ruta = settings.data_dir / "geolibre-url.txt"
    if ruta.is_file():
        return ruta.read_text(encoding="utf-8").strip()
    return settings.geolibre_url


def integrado(settings: Settings) -> bool:
    pref = preferencia_url(settings)
    return pref in ("", "local") and (carpeta_geolibre(settings) / "index.html").is_file()


def _falla(detalle: str, estado: int = 422):
    raise HTTPException(estado, detalle)


def _lista(valor: Any, permitidos: list[str] | None = None) -> list[str]:
    if isinstance(valor, str):
        valor = re.split(r"[\s,]+", valor)
    if not isinstance(valor, list):
        return []
    out: list[str] = []
    for x in valor:
        x = str(x).strip()
        if x and ID_RE.match(x) and (permitidos is None or x in permitidos) and x not in out:
            out.append(x)
    return out[:200]


def _url_valida(url: str, esquemas: tuple[str, ...]) -> bool:
    p = urlsplit(url)
    return p.scheme in esquemas and bool(p.hostname) and not p.username and not p.fragment


def validar(settings: Settings, d: dict[str, Any]) -> dict[str, Any]:
    a = ajustes(settings)
    if "modo" in d:
        a["modo"] = d["modo"] if d["modo"] in ("completo", "visor") else _falla("modo: completo o visor.")
    if "nombre" in d:
        n = " ".join(str(d["nombre"]).split())
        if not 2 <= len(n) <= 60:
            _falla("Nombre de la aplicación: entre 2 y 60 caracteres.")
        a["nombre"] = n
    for b in ("bienvenida", "bloquear_nivel", "instalar_complementos", "mapas_regionales", "servicios_predeterminados", "compartir_publico"):
        if b in d:
            a[b] = bool(d[b])
    if "idioma" in d:
        a["idioma"] = d["idioma"] if d["idioma"] in IDIOMAS else _falla("Idioma no disponible en GeoLibre.")
    if "acento" in d:
        a["acento"] = d["acento"] if d["acento"] in ACENTOS else _falla("Color de acento no válido.")
    if "color_acento" in d:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", str(d["color_acento"])):
            _falla("color_acento: use #RRGGBB.")
        a["color_acento"] = str(d["color_acento"]).upper()
    if "nivel" in d:
        a["nivel"] = d["nivel"] if d["nivel"] in NIVELES else _falla("Nivel de interfaz no válido.")
    if "menus_ocultos" in d:
        a["menus_ocultos"] = _lista(d["menus_ocultos"], MENUS)
    if "capacidades" in d:
        a["capacidades"] = _lista(d["capacidades"], CAPACIDADES)
    for k in ("elementos_ocultos", "fuentes_ocultas", "complementos_ocultos", "complementos_activos", "complementos_bloqueados"):
        if k in d:
            a[k] = _lista(d[k])
    if "panel_inicial" in d:
        p = str(d["panel_inicial"]).strip()
        if p and not ID_RE.match(p):
            _falla("Panel inicial no válido.")
        a["panel_inicial"] = p
    for k, esquemas in (("registro_complementos", ("https",)), ("url_compartir", ("https",)), ("url_colaboracion", ("wss",)), ("overpass_url", ("https",))):
        if k in d:
            v = str(d[k]).strip().rstrip("/")
            if v and (not _url_valida(v, esquemas) or (k == "overpass_url" and urlsplit(v).query)):
                _falla(f"{k}: use una dirección {' o '.join(esquemas)}://")
            a[k] = v
    if "geolens_url" in d:
        v = str(d["geolens_url"]).strip() or "off"
        if v not in ("off", "same-origin") and not _url_valida(v, ("https",)):
            _falla("GeoLens: off, same-origin o una URL https.")
        a["geolens_url"] = v
    if "servicios" in d:
        if not isinstance(d["servicios"], list):
            _falla("servicios debe ser una lista.")
        from .layers import slugify  # importación diferida: layers importa este módulo

        servicios = []
        for i, s in enumerate(d["servicios"][:100]):
            s = s if isinstance(s, dict) else {}
            nombre = str(s.get("name", "")).strip()
            tipo = str(s.get("kind", ""))
            campos_in = s.get("fields") if isinstance(s.get("fields"), dict) else {}
            url = str(campos_in.get("url", s.get("url", ""))).strip()
            if not nombre or tipo not in TIPOS_SERVICIO or not _url_valida(url, ("https", "http")):
                _falla(f"Servicio {i + 1}: indique nombre, tipo ({', '.join(TIPOS_SERVICIO)}) y una URL válida.")
            campos: dict[str, Any] = {"url": url}
            for k, v in campos_in.items():
                if k != "url" and re.match(r"^[A-Za-z][A-Za-z0-9_]{0,40}$", str(k)) and isinstance(v, (str, int, float, bool)):
                    campos[k] = v[:500] if isinstance(v, str) else v
            ident = slugify(str(s.get("id") or nombre), 60) or "servicio"
            usados = {x["id"] for x in servicios}
            base_id, n = ident, 2
            while ident in usados:  # GeoLibre exige ids únicos en el catálogo
                ident, n = f"{base_id[:56]}-{n}", n + 1
            servicios.append({
                "id": ident,
                "name": nombre[:120],
                "kind": tipo,
                "category": str(s.get("category") or "Gobernación de Nariño").strip()[:80],
                "fields": campos,
            })
        a["servicios"] = servicios
    return a


def guardar(settings: Settings, a: dict[str, Any]) -> None:
    _ruta_ajustes(settings).write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")


def url_externa(settings: Settings) -> str:
    """Instancia externa de GeoLibre que se usa cuando el Estudio integrado está desactivado."""
    ruta = settings.data_dir / "geolibre-url-externa.txt"
    if ruta.is_file() and ruta.read_text(encoding="utf-8").strip():
        return ruta.read_text(encoding="utf-8").strip()
    pref = preferencia_url(settings)
    return "https://web.geolibre.app" if pref in ("", "local") else pref


def guardar_url_externa(settings: Settings, url: str) -> None:
    url = (url or "").strip().rstrip("/")
    if url and (not _url_valida(url, ("https", "http")) or urlsplit(url).query):
        _falla("GeoLibre externo: use una URL http(s) sin parámetros, p. ej. https://web.geolibre.app")
    (settings.data_dir / "geolibre-url-externa.txt").write_text(url or "https://web.geolibre.app", encoding="utf-8")


def usar_integrado(settings: Settings) -> bool:
    return preferencia_url(settings) in ("", "local")


def guardar_preferencia_url(settings: Settings, usar_integrado: bool) -> None:
    (settings.data_dir / "geolibre-url.txt").write_text("local" if usar_integrado else url_externa(settings), encoding="utf-8")


def politica(a: dict[str, Any], origen_portal: str) -> dict[str, Any]:
    interfaz: dict[str, Any] = {"enabled": True, "level": a["nivel"], "lock": bool(a["bloquear_nivel"])}
    for k, campo in (("menus_ocultos", "hiddenMenus"), ("elementos_ocultos", "hiddenMenuItems"), ("fuentes_ocultas", "hiddenDataSources"), ("complementos_ocultos", "hiddenPlugins")):
        if a[k]:
            interfaz[campo] = list(a[k])
    complementos: dict[str, Any] = {"sideload": bool(a["instalar_complementos"])}
    if a["complementos_bloqueados"]:
        complementos["blocked"] = list(a["complementos_bloqueados"])
    if a["complementos_activos"]:
        complementos["defaultActive"] = list(a["complementos_activos"])
    if a["registro_complementos"]:
        complementos["registryUrl"] = a["registro_complementos"]
    if a["panel_inicial"]:
        complementos["openPanel"] = a["panel_inicial"]
    compartir: dict[str, Any] = {
        "shareUrl": a["url_compartir"] or ("https://share.geolibre.app" if a["compartir_publico"] else "off"),
        "embedOrigins": [o for o in [origen_portal] if o],
    }
    if a["url_colaboracion"]:
        compartir["collabUrl"] = a["url_colaboracion"]
    servicios: dict[str, Any] = {"builtins": bool(a["servicios_predeterminados"])}
    if a["servicios"]:
        servicios["catalog"] = a["servicios"]
    out: dict[str, Any] = {
        "version": 1,
        "capabilities": list(a["capacidades"]),
        "interface": interfaz,
        "plugins": complementos,
        "services": servicios,
        "basemaps": {"regional": bool(a["mapas_regionales"])},
        "sharing": compartir,
        "geolens": {"url": a["geolens_url"] or "off"},
        "ai": {"enabled": False},
        "branding": {"appName": a["nombre"], "welcome": bool(a["bienvenida"])},
    }
    if a["overpass_url"]:
        out["osm"] = {"overpassUrl": a["overpass_url"]}
    return out


def interfaz(a: dict[str, Any]) -> dict[str, Any]:
    return {"type": "geolibre-interface", "version": 1, "language": a["idioma"], "theme": {"scheme": a["acento"], "customColor": a["color_acento"]}}


def estado(settings: Settings) -> dict[str, Any]:
    dir_ = carpeta_geolibre(settings)
    instalada = None
    if (dir_ / "index.html").is_file():
        v = dir_ / ".version-geoportal"
        instalada = v.read_text(encoding="utf-8").strip() if v.is_file() else "desconocida"
    fijada = version_fijada()
    escribible = os.access(dir_ if dir_.is_dir() else dir_.parent, os.W_OK)
    return {
        "instalado": instalada is not None,
        "version_instalada": instalada,
        "version_disponible": fijada.get("version"),
        "tamano_descarga_mb": round(fijada["tamano_bytes"] / 1048576) if fijada.get("tamano_bytes") else None,
        "puede_instalar": escribible and bool(fijada),
        "requisitos": {"zip": True, "descarga": True, "escritura": escribible},
    }


def escribir_archivos(settings: Settings, a: dict[str, Any] | None = None) -> bool:
    dir_ = carpeta_geolibre(settings)
    if not (dir_ / "index.html").is_file():
        return False
    a = a or ajustes(settings)
    origen = origin_of(settings.public_base_url)
    try:
        (dir_ / "deployment.json").write_text(json.dumps(politica(a, origen), ensure_ascii=False, indent=2), encoding="utf-8")
        (dir_ / "geoportal-ajustes.json").write_text(json.dumps(interfaz(a), ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def instalar(settings: Settings) -> dict[str, Any]:
    """Descarga la versión fijada desde PyPI, verifica el SHA-256 y extrae solo la app web."""
    fijada = version_fijada()
    if not fijada.get("paquete") or not fijada.get("sha256"):
        _falla("Falta portal/api/geolibre-version.json.", 500)
    if not estado(settings)["puede_instalar"]:
        _falla("No hay permiso de escritura en la carpeta de GeoLibre. Use scripts/descargar-geolibre.sh.", 409)
    dir_ = carpeta_geolibre(settings)
    tmp = Path(tempfile.mkdtemp(prefix="geolibre-", dir=settings.tmp_dir))
    try:
        whl = tmp / "geolibre.whl"
        with urllib.request.urlopen(fijada["paquete"], timeout=600) as r, whl.open("wb") as fh:  # noqa: S310 - URL fija https
            shutil.copyfileobj(r, fh)
        h = hashlib.sha256()
        with whl.open("rb") as fh:
            for bloque in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloque)
        if h.hexdigest() != fijada["sha256"]:
            _falla("La descarga no coincide con la suma SHA-256 publicada: se rechazó.", 502)
        prefijo = fijada.get("carpeta_en_paquete", "geolibre/static/app/")
        nuevo = tmp / "app"
        n = 0
        with zipfile.ZipFile(whl) as z:
            for info in z.infolist():
                if not info.filename.startswith(prefijo) or info.is_dir():
                    continue
                rel = info.filename[len(prefijo):]
                if not rel or ".." in rel.split("/") or rel.startswith("/") or "\\" in rel:
                    _falla("El paquete contiene rutas no permitidas.", 502)
                destino = nuevo / rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, destino.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                n += 1
        if not (nuevo / "index.html").is_file():
            _falla("El paquete no contiene la aplicación web de GeoLibre.", 502)
        (nuevo / ".version-geoportal").write_text(fijada["version"], encoding="utf-8")
        dir_.mkdir(parents=True, exist_ok=True)
        # Se reemplaza el contenido (la carpeta puede ser un volumen montado)
        for hijo in dir_.iterdir():
            shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
        for hijo in nuevo.iterdir():
            shutil.move(str(hijo), dir_ / hijo.name)
        escribir_archivos(settings)
        return {"version": fijada["version"], "archivos": n}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def config_publica(settings: Settings) -> dict[str, Any]:
    a = ajustes(settings)
    e = estado(settings)
    base = settings.public_base_url
    return {
        "instalado": e["instalado"],
        "version": e["version_instalada"],
        "url": f"{base}/geolibre/",
        "ajustes_url": f"{base}/geolibre/geoportal-ajustes.json",
        "modo": a["modo"],
        "idioma": a["idioma"],
        "activo": integrado(settings),
    }


def url_abrir(settings: Settings, proyecto: str, visor: bool | None = None) -> str:
    a = ajustes(settings)
    visor = a["modo"] == "visor" if visor is None else visor
    if integrado(settings):
        base = f"{settings.public_base_url}/geolibre/"
        extra = "&settingsUrl=" + quote(base + "geoportal-ajustes.json", safe="")
    else:
        base = url_externa(settings).rstrip("/") + "/"
        extra = "&welcome=0"
    return f"{base}?url={quote(proyecto, safe='')}&locale={a['idioma']}{extra}" + ("&layout=viewer" if visor else "")
