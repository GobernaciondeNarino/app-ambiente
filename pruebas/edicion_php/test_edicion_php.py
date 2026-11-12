"""Instalación con el asistente y contrato de la API en la edición PHP + MySQL.

Simulan lo que hace el navegador: el administrador sube el archivo original y el
resultado de la ingesta (GeoJSON en EPSG:4326 o la vista previa del ráster).
"""

from __future__ import annotations

import base64
import json
import uuid

import httpx

CLAVE = "Admin-Geoportal-2026"
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
TIFF_MINIMO = b"II*\x00" + bytes(252)
ESTADO: dict = {}


def _fc(coords: list[tuple[float, float]], props: list[dict]) -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": p, "geometry": {"type": "Point", "coordinates": list(c)}}
                for c, p in zip(coords, props)
            ],
        }
    ).encode()


def _cargar(c: httpx.Client, url: str, token: str, procesado: bytes | None, info: dict, meta: dict, nombre="datos.zip", extra=None):
    original = TIFF_MINIMO if nombre.endswith(".tif") else b"PK\x03\x04original"
    files = {"archivo": (nombre, original)}
    if procesado is not None:
        files["procesado"] = ("datos.geojson" if info.get("kind") == "vector" else "vista_previa.png", procesado)
    if extra:
        files.update(extra)
    return c.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"info": json.dumps(info), "metadatos": json.dumps(meta)},
    )


def test_asistente_de_instalacion(sitio):
    url = sitio["url"]
    with httpx.Client(follow_redirects=False, timeout=30) as c:
        r = c.get(url + "api/salud")
        assert r.status_code == 503 and r.json()["estado"] == "sin_instalar"
        assert c.get(url + "api/config").json()["instalar"] == "instalar/"
        assert "Comprobación del servidor" in c.get(url + "instalar/").text

        bd = {"db_host": "127.0.0.1", "db_puerto": "3306", "db_nombre": sitio["bd"], "db_prefijo": "gp_"}
        from conftest import MYSQL

        bd.update(db_host=MYSQL["host"], db_puerto=MYSQL["port"], db_usuario=MYSQL["user"])
        r = c.post(url + "instalar/?paso=bd", data=bd | {"db_clave": MYSQL["password"] + "-errada"})
        assert "Usuario o contraseña de la base de datos incorrectos" in r.text
        r = c.post(url + "instalar/?paso=bd", data=bd | {"db_prefijo": "1malo"})
        assert "Prefijo de tablas" in r.text

        r = c.post(url + "instalar/?paso=bd", data=bd | {"db_clave": MYSQL["password"]})
        assert r.status_code == 303 and r.headers["location"] == "?paso=sitio"
        config = (sitio["raiz"] / "config.php").read_text()
        assert "clave_secreta" in config and sitio["bd"] in config

        sitio_form = {
            "nombre_portal": "Geoportal de prueba",
            "url_publica": "",
            "geolibre_url": "https://web.geolibre.app",
            "admin_usuario": "admin",
            "admin_nombre": "Administración",
            "admin_correo": "sig@ejemplo.gov.co",
            "datos_dir": str(sitio["datos"]),
        }
        r = c.post(url + "instalar/?paso=sitio", data=sitio_form | {"admin_clave": "123", "admin_clave2": "123"})
        assert "al menos 10 caracteres" in r.text
        r = c.post(url + "instalar/?paso=sitio", data=sitio_form | {"admin_clave": CLAVE, "admin_clave2": CLAVE})
        assert "quedó instalado" in r.text
        assert (sitio["datos"] / ".htaccess").read_text().strip().endswith("Require all denied")

        # El asistente queda bloqueado: no se puede reinstalar ni sobrescribir config.php
        assert "ya está instalado" in c.get(url + "instalar/").text
        r = c.post(url + "instalar/?paso=bd", data=bd | {"db_clave": "x"})
        assert "ya está instalado" in r.text and (sitio["raiz"] / "config.php").read_text() == config
        assert c.get(url + "api/salud").json()["edicion"] == "php"


def test_ingreso_y_configuracion(sitio):
    url = sitio["url"]
    with httpx.Client(timeout=30) as c:
        assert c.post(url + "api/auth/ingresar", json={"username": "admin", "password": "mala"}).status_code == 401
        r = c.post(url + "api/auth/ingresar", json={"username": "admin", "password": CLAVE})
        assert r.status_code == 200
        ESTADO["token"] = r.json()["access_token"]
        h = {"Authorization": f"Bearer {ESTADO['token']}"}
        assert c.get(url + "api/auth/yo", headers=h).json()["role"] == "administrador"
        assert c.get(url + "api/admin/capas").status_code == 401
        assert c.get(url + "api/admin/capas", headers={"Authorization": "Bearer x.y.z"}).status_code == 401
        cfg = c.get(url + "api/config").json()
        assert cfg["edicion"] == "php" and cfg["ingesta"] == "navegador"
        assert cfg["proyecto_url"] == url + "api/proyecto.geolibre"
        assert c.put(url + "api/admin/configuracion", headers=h, json={"geolibre_url": "javascript:alert(1)"}).status_code == 422
        r = c.put(url + "api/admin/configuracion", headers=h, json={"nombre_portal": "Geoportal Nariño", "max_carga_mb": 50})
        assert r.status_code == 200 and r.json()["max_carga_mb"] == 50
        cats = c.get(url + "api/admin/categorias", headers=h).json()
        ESTADO["hidrico"] = next(x["id"] for x in cats if x["slug"] == "recurso-hidrico")


def test_carga_vector_validada_en_el_servidor(sitio):
    url = sitio["url"] + "api/admin/capas"
    tk = ESTADO["token"]
    with httpx.Client(timeout=60) as c:
        info = {"kind": "vector", "source_format": "Shapefile (ZIP)", "source_crs": "EPSG:9377 — MAGNA-SIRGAS / Origen-Nacional", "warnings": []}
        fc = _fc([(-77.28, 1.21), (-78.76, 1.8)], [{"nombre": "Galeras", "altitud": 4276, "codigo": "52001"}, {"nombre": "Tumaco", "altitud": 2.5, "codigo": "52835"}])
        r = _cargar(c, url, tk, fc, info, {"title": "Estaciones de prueba", "category_id": ESTADO["hidrico"], "keywords": ["clima", "Clima"], "published": True})
        assert r.status_code == 201, r.text
        capa = r.json()["capa"]
        ESTADO["vector"] = capa
        assert capa["feature_count"] == 2 and capa["geometry_type"] == "Punto"
        assert capa["bbox"] == [-78.76, 1.21, -77.28, 1.8]
        assert capa["keywords"] == ["clima"]
        assert capa["label_field"] == "nombre"
        tipos = {a["name"]: a["type"] for a in capa["attributes"]}
        assert tipos == {"nombre": "texto", "altitud": "decimal", "codigo": "texto"}
        assert capa["published"] is True and capa["source_crs"].startswith("EPSG:9377")

        # El servidor no confía en el navegador
        fuera = _fc([(4590000.0, 1700000.0)], [{}])
        r = _cargar(c, url, tk, fuera, info, {"title": "Coordenadas planas"})
        assert r.status_code == 422 and "fuera del rango" in r.json()["detail"]
        assert _cargar(c, url, tk, None, info, {"title": "Sin procesar"}).status_code == 422
        assert _cargar(c, url, tk, b"{no es json", info, {"title": "Roto"}).status_code == 422
        r = _cargar(c, url, tk, fc, info, {"title": "Formato raro"}, nombre="datos.exe")
        assert r.status_code == 422 and "no admitido" in r.json()["detail"]
        r = _cargar(c, url, tk, fc, info | {"kind": "raster"}, {"title": "Tipo inconsistente"})
        assert r.status_code == 422
        # Los intentos fallidos no dejan capas a medias
        assert len(c.get(url, headers={"Authorization": f"Bearer {tk}"}).json()) == 1


def test_carga_raster_y_rangos(sitio):
    url = sitio["url"]
    tk = ESTADO["token"]
    h = {"Authorization": f"Bearer {tk}"}
    info = {
        "kind": "raster",
        "source_format": "GeoTIFF",
        "source_crs": "EPSG:9377",
        "raster_info": {
            "width": 300, "height": 300, "bands": 1, "dtype": "float32", "nodata": -9999,
            "stats": {"min": 1800, "max": 6000, "p2": 1850, "p98": 5700},
            "corners": [[-76.68, 1.55], [-76.41, 1.55], [-76.41, 1.28], [-76.68, 1.28]],
        },
    }
    with httpx.Client(timeout=60) as c:
        r = _cargar(c, url + "api/admin/capas", tk, PNG_1X1, info, {"title": "DEM de prueba", "published": True}, nombre="dem.tif",
                    extra={"geotiff": ("datos_4326.tif", TIFF_MINIMO)})
        assert r.status_code == 201, r.text
        capa = r.json()["capa"]
        ESTADO["raster"] = capa
        assert capa["kind"] == "raster" and capa["bbox"] == [-76.68, 1.28, -76.41, 1.55]
        # El GeoTIFF publicado es la copia teselada en 4326; el original se conserva
        rango = c.get(url + f"api/capas/{capa['slug']}/datos.tif", headers={"Range": "bytes=0-9"})
        assert rango.status_code == 206 and rango.headers["content-range"] == f"bytes 0-9/{len(TIFF_MINIMO)}"
        assert c.get(url + f"api/capas/{capa['slug']}/datos.tif", headers={"Range": "bytes=999999-"}).status_code == 416
        original = c.get(url + f"api/admin/capas/{capa['id']}/original", headers=h)
        assert original.status_code == 200 and original.content == TIFF_MINIMO
        assert c.get(url + f"api/capas/{capa['slug']}/vista-previa.png").content == PNG_1X1
        # Vista previa regenerada en el navegador tras cambiar la simbología
        r = c.put(url + f"api/admin/capas/{capa['id']}", headers=h, json={"style": {"colorRamp": "calor"}})
        assert r.json()["style"]["colorRamp"] == "calor"
        r = c.post(url + f"api/admin/capas/{capa['id']}/vista-previa", headers=h, files={"vista_previa": ("v.png", PNG_1X1)})
        assert r.status_code == 200
        r = c.post(url + f"api/admin/capas/{capa['id']}/vista-previa", headers=h, files={"vista_previa": ("v.png", b"no es png")})
        assert r.status_code == 422
        # Una vista previa que no es PNG o un original que no es TIFF se rechazan
        r = _cargar(c, url + "api/admin/capas", tk, b"GIF89a", info, {"title": "Malo"}, nombre="dem.tif")
        assert r.status_code == 422


def test_api_publica_y_proyecto_geolibre(sitio):
    url = sitio["url"]
    with httpx.Client(timeout=30) as c:
        capas = c.get(url + "api/capas").json()
        assert {x["slug"] for x in capas} == {ESTADO["vector"]["slug"], ESTADO["raster"]["slug"]}
        assert "created_by" not in capas[0] and "published" not in capas[0]
        assert [x["slug"] for x in c.get(url + "api/capas?q=clima").json()] == [ESTADO["vector"]["slug"]]
        assert [x["slug"] for x in c.get(url + "api/categorias").json()] == ["recurso-hidrico"]
        geo = c.get(url + f"api/capas/{ESTADO['vector']['slug']}/datos.geojson")
        assert geo.headers["content-type"].startswith("application/geo+json") and len(geo.json()["features"]) == 2

        proj = c.get(url + "api/proyecto.geolibre").json()
        assert proj["version"] == "0.2.0" and proj["name"] == "Geoportal Nariño"
        tipos = {l["type"] for l in proj["layers"]}
        assert tipos == {"geojson", "cog"}
        vec = next(l for l in proj["layers"] if l["type"] == "geojson")
        # Mismo identificador que la edición Python (UUID v5 del slug)
        assert vec["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "geoportal-ambiente:capa:" + ESTADO["vector"]["slug"]))
        assert vec["groupId"] == proj["layerGroups"][0]["id"] and proj["layerGroups"][0]["name"] == "Recurso hídrico"
        assert vec["geojson"]["features"] and vec["popup"]["titleField"] == "nombre"
        assert vec["source"]["url"] == url + f"api/capas/{ESTADO['vector']['slug']}/datos.geojson"
        cog = next(l for l in proj["layers"] if l["type"] == "cog")
        assert cog["metadata"]["rasterState"]["colormap"] == "ylorrd"
        assert cog["metadata"]["rasterState"]["rescale"] == [[1850.0, 5700.0]]

        d = c.get(url + f"api/capas/{ESTADO['vector']['slug']}/descarga?original=1")
        assert d.status_code == 200 and "attachment" in d.headers["content-disposition"]
        # CORS solo para GeoLibre
        assert c.get(url + "api/capas", headers={"Origin": "https://web.geolibre.app"}).headers["access-control-allow-origin"] == "https://web.geolibre.app"
        assert "access-control-allow-origin" not in c.get(url + "api/capas", headers={"Origin": "https://otro.sitio"}).headers


def test_estudio_sig(sitio):
    url = sitio["url"]
    origen = url.split("/geoportal/")[0]
    h = {"Authorization": f"Bearer {ESTADO['token']}"}
    acao = "access-control-allow-origin"
    with httpx.Client(timeout=30) as c:
        d = c.get(url + "api/admin/geolibre", headers=h).json()
        assert d["estado"]["instalado"] is False and d["estado"]["version_disponible"] == "3.7.0"
        assert d["integrado"] is False and d["ajustes"]["idioma"] == "es"
        assert d["politica"]["sharing"] == {"shareUrl": "off", "embedOrigins": [origen]}
        assert d["politica"]["ai"] == {"enabled": False}
        for malo in ({"nivel": "experto"}, {"idioma": "xx"}, {"color_acento": "verde"}, {"url_colaboracion": "http://relé"},
                     {"geolens_url": "http://inseguro"}, {"servicios": [{"name": "Sin URL", "kind": "wms"}]},
                     {"url_externa": "javascript:alert(1)"}, {"nombre": "x"}):
            assert c.put(url + "api/admin/geolibre", headers=h, json=malo).status_code == 422, malo

        # GeoLibre «instalado» sin descargarlo: basta su index.html
        carpeta = sitio["raiz"] / "geolibre"
        carpeta.mkdir()
        (carpeta / "index.html").write_text("<!doctype html><title>GeoLibre</title>")
        (carpeta / ".version-geoportal").write_text("3.7.0")
        r = c.put(url + "api/admin/geolibre", headers=h, json={
            "usar_integrado": True, "nombre": "Estudio Ambiental", "menus_ocultos": ["help", "x"], "capacidades": ["project:edit", "data:add"],
            "servicios": [{"name": "IDEAM", "kind": "wms", "fields": {"url": "https://ideam.example/wms", "layers": "a"}},
                          {"name": "IDEAM", "kind": "xyz", "fields": {"url": "https://ideam.example/{z}/{x}/{y}.png"}}],
        })
        assert r.status_code == 200 and r.json()["archivos_escritos"] is True and r.json()["integrado"] is True
        assert [s["id"] for s in r.json()["ajustes"]["servicios"]] == ["ideam", "ideam-2"]
        dep = json.loads((carpeta / "deployment.json").read_text())
        assert dep["branding"] == {"appName": "Estudio Ambiental", "welcome": False}
        assert dep["interface"]["hiddenMenus"] == ["help"] and dep["capabilities"] == ["project:edit", "data:add"]
        assert dep["sharing"]["embedOrigins"] == [origen]
        assert c.get(url + "geolibre/deployment.json").json() == dep == c.get(url + "api/geolibre/deployment.json").json()
        interfaz = c.get(url + "geolibre/geoportal-ajustes.json").json()
        assert interfaz == {"type": "geolibre-interface", "version": 1, "language": "es", "theme": {"scheme": "custom", "customColor": "#10A13B"}}

        cfg = c.get(url + "api/config").json()
        assert cfg["estudio"]["activo"] is True and cfg["estudio"]["version"] == "3.7.0"
        assert cfg["geolibre_url"] == url + "geolibre"
        assert cfg["geolibre_editor_url"].startswith(url + "geolibre/?url=") and "settingsUrl=" in cfg["geolibre_editor_url"]
        # La instancia externa de respaldo sigue con CORS
        assert c.get(url + "api/capas", headers={"Origin": "https://web.geolibre.app"}).headers.get(acao) == "https://web.geolibre.app"

        r = c.put(url + "api/admin/geolibre", headers=h, json={"usar_integrado": False, "url_externa": "https://gis.example.org/geolibre/"})
        assert r.json()["integrado"] is False and r.json()["url_externa"] == "https://gis.example.org/geolibre"
        cfg = c.get(url + "api/config").json()
        assert cfg["estudio"]["activo"] is False and cfg["geolibre_url"] == "https://gis.example.org/geolibre"
        assert c.get(url + "api/capas", headers={"Origin": "https://gis.example.org"}).headers.get(acao) == "https://gis.example.org"
        assert acao not in c.get(url + "api/capas", headers={"Origin": "https://web.geolibre.app"}).headers
        r = c.put(url + "api/admin/geolibre", headers=h, json={"usar_integrado": True, "nombre": "Geoportal Ambiental", "menus_ocultos": [], "servicios": []})
        assert r.json()["integrado"] is True

        # Proyecto con el mapa base del visor e identificadores estables para la API de incrustación
        assert c.get(url + "api/proyecto.geolibre?base=oscuro").json()["basemapStyleUrl"] == "https://tiles.openfreemap.org/styles/dark"
        capa = c.get(url + f"api/capas/{ESTADO['vector']['slug']}").json()
        assert capa["geolibre_id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "geoportal-ambiente:capa:" + ESTADO["vector"]["slug"]))
        assert "geolibre_configuracion" in {a["action"] for a in c.get(url + "api/admin/bitacora", headers=h).json()}


def test_roles_bitacora_y_eliminacion(sitio):
    url = sitio["url"]
    h = {"Authorization": f"Bearer {ESTADO['token']}"}
    with httpx.Client(timeout=30) as c:
        assert c.post(url + "api/admin/usuarios", headers=h, json={"username": "debil", "password": "123"}).status_code == 422
        r = c.post(url + "api/admin/usuarios", headers=h, json={"username": "editora", "password": "Editora-2026!", "role": "editor"})
        assert r.status_code == 201
        tk = c.post(url + "api/auth/ingresar", json={"username": "editora", "password": "Editora-2026!"}).json()["access_token"]
        he = {"Authorization": f"Bearer {tk}"}
        vid = ESTADO["vector"]["id"]
        assert c.post(url + f"api/admin/capas/{vid}/publicacion?publicar=false", headers=he).status_code == 403
        assert c.delete(url + f"api/admin/capas/{vid}", headers=he).status_code == 403
        assert c.get(url + "api/admin/usuarios", headers=he).status_code == 403
        assert c.get(url + "api/admin/configuracion", headers=he).status_code == 403
        assert c.get(url + "api/admin/geolibre", headers=he).status_code == 403
        assert c.post(url + "api/admin/geolibre/instalar", headers=he).status_code == 403
        assert c.put(url + f"api/admin/capas/{vid}", headers=he, json={"published": False}).status_code == 403
        assert c.put(url + f"api/admin/capas/{vid}", headers=he, json={"description": "Editado por la editora"}).status_code == 200
        # Una editora carga siempre como borrador
        r = _cargar(c, url + "api/admin/capas", tk, _fc([(-77.3, 1.2)], [{"a": 1}]), {"kind": "vector", "warnings": []}, {"title": "Borrador", "published": True})
        assert r.status_code == 201 and r.json()["capa"]["published"] is False
        assert c.get(url + f"api/capas/{r.json()['capa']['slug']}").status_code == 404

        assert c.delete(url + f"api/admin/capas/{vid}", headers=h).status_code == 204
        assert not (sitio["datos"] / "procesados" / str(vid)).exists()
        acciones = {a["action"] for a in c.get(url + "api/admin/bitacora", headers=h).json()}
        assert {"instalacion", "ingreso", "ingreso_fallido", "carga", "edicion", "publicacion", "eliminacion", "usuario_creado", "configuracion"} <= acciones
        assert c.delete(url + f"api/admin/categorias/{ESTADO['hidrico']}", headers=h).status_code == 204  # quedó sin capas
