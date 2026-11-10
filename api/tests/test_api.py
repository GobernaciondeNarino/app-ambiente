from __future__ import annotations

import json

from conftest import ADMIN_PASSWORD


def _upload(client, auth, path, meta=None, **form):
    with path.open("rb") as fh:
        data = {"metadatos": json.dumps(meta or {})}
        data.update({k: str(v) for k, v in form.items()})
        return client.post("/api/admin/capas", headers=auth, files={"archivo": (path.name, fh)}, data=data)


def test_login_and_me(client, auth):
    r = client.get("/api/auth/yo", headers=auth)
    assert r.status_code == 200
    assert r.json()["role"] == "administrador"


def test_bad_login(client):
    r = client.post("/api/auth/ingresar", json={"username": "admin", "password": "mala"})
    assert r.status_code == 401


def test_admin_requires_token(client):
    assert client.get("/api/admin/capas").status_code == 401


def test_default_categories_seeded(client, auth):
    cats = client.get("/api/admin/categorias", headers=auth).json()
    assert any(c["slug"] == "recurso-hidrico" for c in cats)


def test_upload_publish_and_public_flow(client, auth, shapefile_zip):
    cats = client.get("/api/admin/categorias", headers=auth).json()
    hidrico = next(c for c in cats if c["slug"] == "recurso-hidrico")
    r = _upload(
        client,
        auth,
        shapefile_zip,
        {
            "title": "Drenajes principales",
            "description": "Red de drenaje doble",
            "category_id": hidrico["id"],
            "keywords": ["hidrografía", "ríos"],
            "style": {"strokeColor": "#0E7FC0", "strokeWidth": 2},
        },
    )
    assert r.status_code == 201, r.text
    capa = r.json()["capa"]
    assert capa["slug"] == "drenajes-principales"
    assert capa["published"] is False
    assert capa["label_field"] == "NOMBRE_GEO"
    assert capa["style"]["strokeColor"] == "#0E7FC0"

    # Borrador: no visible públicamente
    assert client.get("/api/capas").json() == []
    assert client.get(f"/api/capas/{capa['slug']}/datos.geojson").status_code == 404

    # Publicar
    r = client.post(f"/api/admin/capas/{capa['id']}/publicacion?publicar=true", headers=auth)
    assert r.status_code == 200 and r.json()["published"] is True

    public = client.get("/api/capas").json()
    assert [c["slug"] for c in public] == ["drenajes-principales"]
    assert "created_by" not in public[0]
    assert client.get("/api/capas?q=hidrografía").json()
    assert client.get("/api/categorias").json()[0]["slug"] == "recurso-hidrico"

    geo = client.get("/api/capas/drenajes-principales/datos.geojson")
    assert geo.status_code == 200
    assert len(geo.json()["features"]) == 2

    # Proyecto GeoLibre
    proj = client.get("/api/proyecto.geolibre").json()
    assert proj["version"] == "0.2.0"
    assert proj["layerGroups"][0]["name"] == "Recurso hídrico"
    layer = proj["layers"][0]
    assert layer["type"] == "geojson"
    assert layer["groupId"] == proj["layerGroups"][0]["id"]
    assert layer["source"]["url"] == "http://portal.test/api/capas/drenajes-principales/datos.geojson"
    assert layer["geojson"]["features"]
    assert layer["descriptiveMetadata"]["keywords"] == ["hidrografía", "ríos"]
    assert layer["popup"]["titleField"] == "NOMBRE_GEO"

    cfg = client.get("/api/config").json()
    assert cfg["geolibre_proyecto_url"].startswith("http://visor.test/?url=http%3A%2F%2Fportal.test")

    # Descarga
    d = client.get("/api/capas/drenajes-principales/descarga?original=1")
    assert d.status_code == 200 and d.content[:2] == b"PK"


def test_raster_upload_and_range_request(client, auth, raster_file):
    r = _upload(client, auth, raster_file, {"title": "Modelo digital de elevación", "published": True})
    assert r.status_code == 201, r.text
    capa = r.json()["capa"]
    assert capa["kind"] == "raster"
    assert capa["published"] is True  # el administrador puede publicar al cargar
    cog = client.get(f"/api/capas/{capa['slug']}/datos.tif", headers={"Range": "bytes=0-99"})
    assert cog.status_code == 206
    assert len(cog.content) == 100
    assert client.get(f"/api/capas/{capa['slug']}/vista-previa.png").status_code == 200
    proj = client.get(f"/api/capas/{capa['slug']}/proyecto.geolibre").json()
    assert proj["layers"][0]["type"] == "cog"
    assert proj["layers"][0]["metadata"]["rasterState"]["mode"] == "single"

    # Cambio de rampa regenera la vista previa
    r = client.put(f"/api/admin/capas/{capa['id']}", headers=auth, json={"style": {"colorRamp": "verdes"}})
    assert r.status_code == 200 and r.json()["style"]["colorRamp"] == "verdes"


def test_invalid_file_is_rejected_cleanly(client, auth, tmp_path):
    bad = tmp_path / "roto.geojson"
    bad.write_text("{esto no es json")
    r = _upload(client, auth, bad)
    assert r.status_code == 422
    assert client.get("/api/admin/capas", headers=auth).json() == []


def test_editor_cannot_publish_or_delete(client, auth, geojson_file):
    r = client.post(
        "/api/admin/usuarios",
        headers=auth,
        json={"username": "editora", "password": "Editora-2026!", "role": "editor", "full_name": "Editora"},
    )
    assert r.status_code == 201, r.text
    tok = client.post("/api/auth/ingresar", json={"username": "editora", "password": "Editora-2026!"}).json()["access_token"]
    ed = {"Authorization": f"Bearer {tok}"}

    r = _upload(client, ed, geojson_file, {"title": "Humedales", "published": True})
    assert r.status_code == 201
    capa = r.json()["capa"]
    assert capa["published"] is False
    assert client.post(f"/api/admin/capas/{capa['id']}/publicacion?publicar=true", headers=ed).status_code == 403
    assert client.delete(f"/api/admin/capas/{capa['id']}", headers=ed).status_code == 403
    assert client.get("/api/admin/usuarios", headers=ed).status_code == 403
    # Pero sí puede editar metadatos
    r = client.put(f"/api/admin/capas/{capa['id']}", headers=ed, json={"description": "Inventario de humedales"})
    assert r.status_code == 200


def test_weak_password_rejected(client, auth):
    r = client.post("/api/admin/usuarios", headers=auth, json={"username": "debil", "password": "123", "role": "editor"})
    assert r.status_code == 422


def test_replace_file_and_delete(client, auth, geojson_file, csv_file):
    capa = _upload(client, auth, geojson_file, {"title": "Puntos"}).json()["capa"]
    with csv_file.open("rb") as fh:
        r = client.post(f"/api/admin/capas/{capa['id']}/archivo", headers=auth, files={"archivo": (csv_file.name, fh)})
    assert r.status_code == 200, r.text
    assert r.json()["capa"]["geometry_type"] == "Punto"
    assert r.json()["capa"]["title"] == "Puntos"
    assert client.delete(f"/api/admin/capas/{capa['id']}", headers=auth).status_code == 204
    log = client.get("/api/admin/bitacora", headers=auth).json()
    assert {e["action"] for e in log} >= {"carga", "actualizacion_archivo", "eliminacion"}


def test_change_password(client, auth):
    r = client.post(
        "/api/auth/cambiar-clave",
        headers=auth,
        json={"current_password": ADMIN_PASSWORD, "new_password": "Otra-Clave-2027"},
    )
    assert r.status_code == 200
    assert client.post("/api/auth/ingresar", json={"username": "admin", "password": "Otra-Clave-2027"}).status_code == 200


def test_public_url_autodetected_for_subdirectory(client, auth, geojson_file, monkeypatch):
    """Sin GEOPORTAL_PUBLIC_URL, las URL siguen al dominio y subdirectorio del proxy."""
    from app import config

    monkeypatch.setattr(config.get_settings(), "public_base_url", "")
    capa = _upload(client, auth, geojson_file, {"title": "Humedales", "published": True}).json()["capa"]
    h = {"X-Forwarded-Host": "www.narino.gov.co", "X-Forwarded-Proto": "https", "X-Forwarded-Prefix": "/ambiente/geoportal/"}
    ficha = client.get(f"/api/capas/{capa['slug']}", headers=h).json()
    assert ficha["urls"]["datos"] == "https://www.narino.gov.co/ambiente/geoportal/api/capas/humedales/datos.geojson"
    proj = client.get("/api/proyecto.geolibre", headers=h)
    assert "Host" in proj.headers["vary"]
    assert proj.json()["layers"][0]["source"]["url"].startswith("https://www.narino.gov.co/ambiente/geoportal/api/")
    cfg = client.get("/api/config", headers={"Host": "sig.narino.gov.co"}).json()
    assert cfg["proyecto_url"] == "http://sig.narino.gov.co/api/proyecto.geolibre"
    # Cabeceras malformadas no se reflejan
    bad = client.get("/api/config", headers={"X-Forwarded-Host": "evil.com/<x>", "X-Forwarded-Prefix": "/a b"}).json()
    assert bad["proyecto_url"] == "http://localhost/api/proyecto.geolibre"


def test_docs_use_relative_openapi(client):
    r = client.get("/api/docs")
    assert r.status_code == 200 and "'openapi.json'" in r.text or '"openapi.json"' in r.text
    assert client.get("/api/openapi.json").status_code == 200
