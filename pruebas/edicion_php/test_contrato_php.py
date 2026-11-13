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
