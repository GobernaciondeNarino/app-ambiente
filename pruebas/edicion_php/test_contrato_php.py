"""Contrato común con la edición Python: validación de entradas, códigos HTTP y cabeceras."""

from __future__ import annotations

import json

import httpx
import pytest
from conftest import instalar_sitio
from test_edicion_php import CLAVE, _cargar, _fc

INFO = {"kind": "vector", "source_format": "GeoJSON", "warnings": []}
FC = _fc([(-77.28, 1.21), (-78.76, 1.8)], [{"nombre": "Galeras"}, {"nombre": "Tumaco"}])


@pytest.fixture(scope="module")
def api(sitio):
    token = instalar_sitio(sitio, CLAVE)
    with httpx.Client(base_url=sitio["url"] + "api", timeout=60, headers={"Authorization": f"Bearer {token}"}) as c:
        r = _cargar(c, sitio["url"] + "api/admin/capas", token, FC, INFO, {"title": "Estaciones", "published": True}, nombre="estaciones.geojson")
        assert r.status_code == 201, r.text
        c.capa = r.json()["capa"]
        c.token = token
        yield c


def test_entradas_no_validas_son_422_y_no_500(api):
    cid = api.capa["id"]
    # (int) 'abc' = 0 llegaba a la base de datos como categoría inexistente: 500 «Error de base de datos»
    for cat in ("abc", 0, 99999):
        r = api.put(f"/admin/capas/{cid}", json={"category_id": cat})
        assert r.status_code == 422, (cat, r.text)
    for cuerpo in ({"keywords": "a,b"}, {"keywords": [1, 2]}, {"popup_fields": "nombre"}, {"downloadable": "quizás"},
                   {"style": [1, 2]}, {"style": {"band": "x"}}, {"title": 5}):
        assert api.put(f"/admin/capas/{cid}", json=cuerpo).status_code == 422, cuerpo
    capa = api.get(f"/admin/capas/{cid}").json()
    assert capa["downloadable"] is True and capa["keywords"] == [] and capa["category_id"] is None
    for ruta in ("/capas?tipo=x", "/capas?q=" + "a" * 121, "/admin/capas?estado=x", "/admin/capas?categoria_id=abc",
                 f"/admin/capas/{cid}/muestra?limite=0", f"/admin/capas/{cid}/muestra?limite=9999", "/admin/bitacora?limite=abc",
                 f"/capas/{api.capa['slug']}/descarga?original=quizás"):
        assert api.get(ruta).status_code == 422, ruta
    assert len(api.get(f"/admin/capas/{cid}/muestra?limite=1").json()["features"]) == 1
    # Cuerpo que no es un objeto JSON, y campos de ingreso ausentes o de otro tipo
    assert api.put("/admin/geolibre", json=[1]).status_code == 422
    for cuerpo in ([1, 2], {}, {"username": ["admin"], "password": CLAVE}, {"username": "a" * 81, "password": "x"}):
        assert api.post("/auth/ingresar", json=cuerpo).status_code == 422, cuerpo
    assert api.post("/auth/cambiar-clave", json={}).status_code == 422
    # Metadatos rotos en la carga
    r = _cargar(api, str(api.base_url) + "/admin/capas", api.token, FC, INFO, {})
    assert r.status_code == 201
    r = api.post("/admin/capas", files={"archivo": ("a.geojson", b"{}"), "procesado": ("p.geojson", FC)},
                 data={"info": json.dumps(INFO), "metadatos": "{roto"})
    assert r.status_code == 422 and r.json()["detail"].startswith("Metadatos no válidos")
    assert api.post("/admin/categorias", json={"name": "Nueva", "position": "x"}).status_code == 422
    assert api.post("/admin/usuarios", json={"username": "otro", "password": "Editora-2026!", "full_name": "n" * 161}).status_code == 422


def test_publicar_es_obligatorio_y_original_es_booleano(api):
    cid, slug = api.capa["id"], api.capa["slug"]
    # Sin «publicar» la capa se retiraba (FILTER_VALIDATE_BOOLEAN con '' devuelve false)
    assert api.post(f"/admin/capas/{cid}/publicacion").status_code == 422
    assert api.get(f"/admin/capas/{cid}").json()["published"] is True
    assert api.post(f"/admin/capas/{cid}/publicacion?publicar=1").json()["published"] is True
    # «?original=false» entregaba el original
    for valor, nombre in (("false", f"{slug}.geojson"), ("0", f"{slug}.geojson"), ("true", "estaciones.geojson"), ("1", "estaciones.geojson")):
        r = api.get(f"/capas/{slug}/descarga?original={valor}")
        assert r.status_code == 200 and f'filename="{nombre}"' in r.headers["content-disposition"], valor


def test_metodos_no_previstos_son_405(api):
    antes = api.get("/admin/geolibre").json()["ajustes"]
    # DELETE se trataba como GET; GET/DELETE de un usuario pedían un cuerpo JSON (422); GET de ingresar, 401
    for metodo, ruta in (("DELETE", "/admin/geolibre"), ("GET", "/admin/usuarios/1"), ("DELETE", "/admin/usuarios/1"),
                         ("GET", "/admin/categorias/1"), ("PUT", "/admin/categorias"), ("POST", "/capas"),
                         ("DELETE", f"/capas/{api.capa['slug']}"), ("DELETE", "/admin/configuracion")):
        r = api.request(metodo, ruta)
        assert r.status_code == 405 and r.json() == {"detail": "Método no permitido."}, (metodo, ruta, r.text)
    assert httpx.get(str(api.base_url) + "/auth/ingresar").status_code == 405
    assert api.get("/nada").status_code == 404 and api.get("/capas/no-existe/otra").status_code == 404
    assert api.get("/admin/geolibre").json()["ajustes"] == antes


def test_estudio_put_responde_como_get_y_nulos(api):
    r = api.put("/admin/geolibre", json={"nombre": "Estudio"})
    assert r.status_code == 200 and set(api.get("/admin/geolibre").json()) <= set(r.json())
    assert r.json()["opciones"]["idiomas"][0] == "es"
    for campo in ("modo", "idioma", "nombre", "color_acento", "nivel", "acento"):
        assert api.put("/admin/geolibre", json={campo: None}).status_code == 422, campo
    assert api.put("/admin/geolibre", json={"servicios": {"a": {"name": "S", "kind": "wms", "url": "https://a.example/wms"}}}).status_code == 422


def test_categoria_conserva_icono_y_usuario_activo_nulo(api):
    cat = next(c for c in api.get("/admin/categorias").json() if c["slug"] == "recurso-hidrico")
    r = api.put(f"/admin/categorias/{cat['id']}", json={"name": "Recurso hídrico", "description": "D", "color": "#0E7FC0", "position": 0})
    assert r.status_code == 200 and r.json()["icon"] == "agua" and r.json()["description"] == "D"
    yo = api.get("/auth/yo").json()
    # «active: null» no es una desactivación (antes respondía 400)
    assert api.put(f"/admin/usuarios/{yo['id']}", json={"full_name": "Admin", "active": None}).status_code == 200


def test_cabeceras_vary_y_www_authenticate(api, sitio):
    origen = "https://web.geolibre.app"
    r = httpx.get(sitio["url"] + "api/proyecto.geolibre", headers={"Origin": origen})
    assert r.headers["access-control-allow-origin"] == origen
    vary = {v.strip() for v in ",".join(r.headers.get_list("vary")).split(",")}
    assert {"Origin", "Host"} <= vary  # antes «Vary: Host…» reemplazaba a «Vary: Origin»
    assert httpx.get(sitio["url"] + "api/admin/capas").headers.get("www-authenticate") == "Bearer"
    assert "www-authenticate" not in api.get("/admin/capas").headers
    assert httpx.head(sitio["url"] + f"api/capas/{api.capa['slug']}/datos.geojson").status_code == 200


FECHA_INEXISTENTE = "data_date: la fecha no existe (mes de 01 a 12 y un día válido para ese mes)."
FECHA_FORMATO = "data_date: use el formato AAAA, AAAA-MM o AAAA-MM-DD."
CORREO_NO_VALIDO = "correo electrónico no válido (p. ej. nombre@entidad.gov.co)."


def _cargar_capa(api, meta):
    return _cargar(api, str(api.base_url) + "/admin/capas", api.token, FC, INFO, meta)


def test_fecha_de_la_informacion(api):
    r = _cargar_capa(api, {"title": "Con fecha", "data_date": "2024-02-29"})
    assert r.status_code == 201 and r.json()["capa"]["data_date"] == "2024-02-29"
    url = f"/admin/capas/{r.json()['capa']['id']}"
    guardada = "2024-02-29"
    for valor in ("2024", None, "2024-02", " 1990-12-31 ", "", "2000-02-29"):
        r = api.put(url, json={"data_date": valor})
        guardada = guardada if valor is None else valor.strip()
        assert r.status_code == 200 and r.json()["data_date"] == guardada, valor
    for valor in ("2026-13", "2026-02-30", "2023-02-29", "2026-00", "2026-04-31", "2026-12-32", "0000"):
        r = api.put(url, json={"data_date": valor})
        assert r.status_code == 422 and r.json()["detail"] == FECHA_INEXISTENTE, valor
    for valor in ("2026-1", "26-01-01", "2026/01/01", "ayer"):
        r = api.put(url, json={"data_date": valor})
        assert r.status_code == 422 and r.json()["detail"] == FECHA_FORMATO, valor
    assert api.get(url).json()["data_date"] == "2000-02-29"
    r = _cargar_capa(api, {"title": "Otra", "data_date": "2026-02-30"})
    assert r.status_code == 422 and r.json()["detail"] == "Metadatos no válidos: " + FECHA_INEXISTENTE


def test_correos_de_contacto_y_de_usuario(api):
    r = _cargar_capa(api, {"title": "Con correo", "contact_email": " sig@narino.gov.co "})
    assert r.status_code == 201 and r.json()["capa"]["contact_email"] == "sig@narino.gov.co"
    url = f"/admin/capas/{r.json()['capa']['id']}"
    for valor in ("correo", "a@b", "a..b@x.co", "josé@x.co", "a@x.co b", "@x.co"):
        r = api.put(url, json={"contact_email": valor})
        assert r.status_code == 422 and r.json()["detail"] == "contact_email: " + CORREO_NO_VALIDO, valor
    assert api.put(url, json={"contact_email": "o'neil+sig@sub-dominio.gov.co"}).json()["contact_email"] == "o'neil+sig@sub-dominio.gov.co"
    assert api.put(url, json={"contact_email": ""}).json()["contact_email"] == ""
    r = _cargar_capa(api, {"title": "Otra", "contact_email": "malo"})
    assert r.status_code == 422 and r.json()["detail"] == "Metadatos no válidos: contact_email: " + CORREO_NO_VALIDO
    # Usuarios: crear y editar
    nuevo = {"username": "editora", "password": "Editora-2026!", "role": "editor"}
    r = api.post("/admin/usuarios", json=nuevo | {"email": "editora@"})
    assert r.status_code == 422 and r.json()["detail"] == "email: " + CORREO_NO_VALIDO
    r = api.post("/admin/usuarios", json=nuevo | {"email": "editora@narino.gov.co"})
    assert r.status_code == 201 and r.json()["email"] == "editora@narino.gov.co"
    uid = r.json()["id"]
    r = api.put(f"/admin/usuarios/{uid}", json={"email": "x@y"})
    assert r.status_code == 422 and r.json()["detail"] == "email: " + CORREO_NO_VALIDO
    assert api.put(f"/admin/usuarios/{uid}", json={"email": None}).json()["email"] == "editora@narino.gov.co"
    assert api.put(f"/admin/usuarios/{uid}", json={"email": ""}).json()["email"] == ""
