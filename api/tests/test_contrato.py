"""Contrato común con la edición PHP: errores en JSON y en español, bordes de la API y HEAD."""

from __future__ import annotations

from test_api import _upload


def _publicar(client, auth, path, meta) -> dict:
    r = _upload(client, auth, path, meta)
    assert r.status_code == 201, r.text
    capa = r.json()["capa"]
    assert client.post(f"/api/admin/capas/{capa['id']}/publicacion?publicar=true", headers=auth).status_code == 200
    return capa


def test_errores_en_json_y_en_espanol(client, auth, geojson_file):
    # Validación: un texto («detail») en español, no la lista en inglés de pydantic
    r = client.post("/api/admin/categorias", headers=auth, json={"name": "x"})
    assert r.status_code == 422 and r.json() == {"detail": "name: debe tener al menos 2 caracteres."}
    r = client.get("/api/admin/bitacora?limite=0", headers=auth)
    assert r.status_code == 422 and r.json()["detail"] == "limite: debe ser mayor o igual que 1."
    assert client.post("/api/auth/ingresar", json=[1, 2]).json() == {"detail": "El cuerpo de la petición debe ser un objeto JSON."}
    r = client.post("/api/auth/ingresar", content=b"hola", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and r.json() == {"detail": "El cuerpo de la petición debe ser JSON."}
    # Rutas y métodos inexistentes, como en la edición PHP
    assert client.get("/api/nada").json() == {"detail": "Recurso no encontrado."}
    r = client.post("/api/capas")
    assert r.status_code == 405 and r.json() == {"detail": "Método no permitido."}
    # Metadatos de la carga: sin el volcado interno de pydantic
    r = _upload(client, auth, geojson_file, {"title": "x"})
    assert r.status_code == 422 and r.json()["detail"] == "Metadatos no válidos: title: debe tener al menos 2 caracteres."
    capa = _upload(client, auth, geojson_file, {"title": "Humedales"}).json()["capa"]
    r = client.put(f"/api/admin/capas/{capa['id']}", headers=auth, json={"style": {"strokeWidth": "ancho", "band": 1}})
    assert r.status_code == 422 and r.json()["detail"] == "strokeWidth: debe ser numérico."
    r = client.put(f"/api/admin/capas/{capa['id']}", headers=auth, json={"data_date": "ayer"})
    assert r.json()["detail"] == "data_date: use el formato AAAA, AAAA-MM o AAAA-MM-DD."


def test_ingesta_sin_rutas_internas(client, auth, tmp_path):
    roto = tmp_path / "roto.gpkg"
    roto.write_bytes(b"no es un geopackage")
    r = _upload(client, auth, roto)
    assert r.status_code == 422
    detalle = r.json()["detail"]
    assert "roto.gpkg" in detalle and str(tmp_path) not in detalle and "/tmp/" not in detalle


def test_identificadores_imposibles_y_error_interno(client, auth, monkeypatch):
    enorme = "99999999999999999999"
    assert client.get(f"/api/admin/capas/{enorme}", headers=auth).status_code == 404
    assert client.get(f"/api/admin/capas/{enorme}/datos", headers=auth).status_code == 404
    assert client.put(f"/api/admin/categorias/{enorme}", headers=auth, json={"name": "Nada"}).status_code == 404
    assert client.put(f"/api/admin/usuarios/{enorme}", headers=auth, json={"full_name": "x"}).status_code == 404
    # Un error no previsto responde JSON en español, sin traza
    from fastapi.testclient import TestClient

    from app.services import estudio

    monkeypatch.setattr(estudio, "config_publica", lambda s: (_ for _ in ()).throw(RuntimeError("/ruta/secreta")))
    with TestClient(client.app, raise_server_exceptions=False) as c:
        r = c.get("/api/config")
    assert r.status_code == 500 and r.json() == {"detail": "Error interno del servidor."}


def test_head_comodines_y_capas_vacias(client, auth, geojson_file):
    capa = _publicar(client, auth, geojson_file, {"title": "Humedales"})
    for ruta in ("datos.geojson", "descarga", ""):
        r = client.head(f"/api/capas/{capa['slug']}/{ruta}".rstrip("/"))
        assert r.status_code == 200, ruta
    assert int(client.head(f"/api/capas/{capa['slug']}/datos.geojson").headers["content-length"]) > 0
    assert client.head("/api/capas/no-existe/datos.geojson").status_code == 404
    # «%» y «_» se buscan literalmente (en la edición PHP ya era así)
    assert client.get("/api/capas?q=%25").json() == [] and client.get("/api/capas?q=_").json() == []
    assert client.get("/api/admin/capas?q=%25", headers=auth).json() == []
    assert len(client.get("/api/capas?q=humed").json()) == 1
    # «?capas=,,» sin identificadores no filtra
    assert len(client.get("/api/proyecto.geolibre?capas=,,").json()["layers"]) == 1
    assert client.get("/api/proyecto.geolibre?capas=zzz").json()["layers"] == []


def test_salud_raiz_y_version(client):
    assert client.get("/api/salud").json() == {"estado": "ok", "edicion": "docker", "version": "1.2.0"}
    raiz = client.get("/api/").json()
    assert raiz["version"] == "1.2.0" and raiz["documentacion"] == "http://portal.test/api/docs"


def test_estudio_valores_nulos(client, auth):
    assert client.put("/api/admin/geolibre", headers=auth, json={"nombre": None}).status_code == 422
    r = client.put("/api/admin/geolibre", headers=auth, json={"panel_inicial": None, "geolens_url": None, "overpass_url": None})
    assert r.status_code == 200
    a = r.json()["ajustes"]
    assert a["panel_inicial"] == "" and a["geolens_url"] == "off" and a["overpass_url"] == "" and a["nombre"] == "Geoportal Ambiental"
    assert client.put("/api/admin/geolibre", headers=auth, json=[1]).status_code == 422


def test_categoria_conserva_campos_no_enviados(client, auth):
    cat = next(c for c in client.get("/api/admin/categorias", headers=auth).json() if c["slug"] == "recurso-hidrico")
    assert cat["icon"] == "agua"
    # El administrador envía nombre, descripción, color y orden, pero no el icono
    r = client.put(f"/api/admin/categorias/{cat['id']}", headers=auth, json={"name": "Recurso hídrico", "description": "D", "color": "#0E7FC0", "position": 0})
    assert r.status_code == 200 and r.json()["icon"] == "agua" and r.json()["description"] == "D"


def test_editor_puede_enviar_published_nulo(client, auth, geojson_file):
    client.post("/api/admin/usuarios", headers=auth, json={"username": "editora", "password": "Editora-2026!", "role": "editor"})
    tk = client.post("/api/auth/ingresar", json={"username": "editora", "password": "Editora-2026!"}).json()["access_token"]
    ed = {"Authorization": f"Bearer {tk}"}
    capa = _upload(client, ed, geojson_file, {"title": "Humedales"}).json()["capa"]
    assert client.put(f"/api/admin/capas/{capa['id']}", headers=ed, json={"published": None, "description": "x"}).status_code == 200
    assert client.put(f"/api/admin/capas/{capa['id']}", headers=ed, json={"published": True}).status_code == 403
