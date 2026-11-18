"""Servicio de compartir de GeoLibre (contrato v1) en la edición Python: tokens personales, ciclo completo,
visibilidad, rutas opcionales y límites. Mismas comprobaciones que pruebas/edicion_php/test_compartir_php.py."""

from __future__ import annotations

import hashlib
import json

import pytest

BASE = "/api/compartir"
URL = "http://portal.test"  # GEOPORTAL_PUBLIC_URL de conftest.py
CLAVE_EDITORA = "Editora-2026!"


def proyecto(nombre: str | None = "Humedales de Nariño", capas: int = 1, relleno: str = "") -> str:
    doc = {"version": "1.0", "mapView": {"center": [-77.3, 1.2], "zoom": 8, "bearing": 0, "pitch": 0},
           "layers": [{"id": f"c{i}", "name": f"Capa {i}"} for i in range(capas)], "relleno": relleno}
    if nombre is not None:
        doc["name"] = nombre
    return json.dumps(doc, ensure_ascii=False)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def emitir(client, sesion: dict, nombre: str = "GeoLibre de pruebas", **extra) -> dict:
    r = client.post("/api/admin/compartir/tokens", headers=sesion, json={"name": nombre, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def publicar(client, token: str, visibilidad: str = "public", **kw) -> dict:
    cuerpo = {"filename": "Humedales.geolibre.json", "content": proyecto(**kw), "visibility": visibilidad}
    r = client.post(f"{BASE}/api/projects", headers=bearer(token), json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()["project"]


def acciones(client, auth) -> list[str]:
    return [a["action"] for a in client.get("/api/admin/bitacora", headers=auth).json()]


@pytest.fixture()
def tk(client, auth) -> str:
    return emitir(client, auth)["token"]


@pytest.fixture()
def editora(client, auth) -> dict:
    r = client.post("/api/admin/usuarios", headers=auth, json={"username": "editora", "password": CLAVE_EDITORA, "role": "editor"})
    assert r.status_code == 201, r.text
    jwt = client.post("/api/auth/ingresar", json={"username": "editora", "password": CLAVE_EDITORA}).json()["access_token"]
    sesion = bearer(jwt)
    return {"id": r.json()["id"], "sesion": sesion, "token": emitir(client, sesion, "Equipo de la editora")["token"]}


def test_tokens_personales(client, auth):
    d = emitir(client, auth, "  Portátil de la Secretaría  ", expires_in_days=30)
    token = d["token"]
    assert token.startswith("gpc_") and len(token) == 52 and d["prefix"] == token[:12]
    assert d["name"] == "Portátil de la Secretaría" and d["username"] == "admin"
    assert d["share_url"] == URL + "/api/compartir" and d["expires_at"] and d["expired"] is False
    lista = client.get("/api/admin/compartir/tokens", headers=auth)
    assert lista.status_code == 200 and token not in lista.text and lista.json()["share_url"] == URL + "/api/compartir"
    assert [t["id"] for t in lista.json()["tokens"]] == [d["id"]]
    # Solo se guarda el SHA-256
    from app.db import session_scope
    from app.models import ShareToken

    with session_scope() as s:
        fila = s.get(ShareToken, d["id"])
        assert fila.token_hash == hashlib.sha256(token.encode()).hexdigest() and token not in (fila.name, fila.prefix, fila.token_hash)
    # Validación
    for cuerpo in ({}, {"name": " "}, {"name": "n" * 101}, {"name": 5}, {"name": "a", "expires_in_days": 0},
                   {"name": "a", "expires_in_days": 366}, {"name": "a", "expires_in_days": "30"}, {"name": "a", "expires_in_days": True}):
        assert client.post("/api/admin/compartir/tokens", headers=auth, json=cuerpo).status_code == 422, cuerpo
    assert client.post("/api/admin/compartir/tokens", headers=auth, json=[1]).status_code == 422
    assert client.get("/api/admin/compartir/tokens?todos=quizás", headers=auth).status_code == 422
    # El token de sesión no sirve en el servicio y el token personal no sirve en el administrador
    r = client.get(f"{BASE}/api/users/me", headers=auth)
    assert r.status_code == 401 and "invalid_token" in r.headers["www-authenticate"]
    r = client.get(f"{BASE}/api/users/me")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer" and r.json()["error"] == r.json()["detail"]
    assert client.get("/api/admin/compartir/tokens", headers=bearer(token)).status_code == 401
    yo = client.get(f"{BASE}/api/users/me", headers=bearer(token))
    assert yo.status_code == 200 and yo.headers["cache-control"] == "private, no-store"
    assert yo.json()["user"]["username"] == "admin" and yo.json()["sessionId"] is None
    assert set(yo.json()["scopes"]) == {"read:projects", "write:projects", "share:public"}
    assert client.get("/api/admin/compartir/tokens", headers=auth).json()["tokens"][0]["last_used_at"]
    # Revocar: deja de autenticar; repetir es inocuo; un id desconocido es 404
    assert client.delete(f"/api/admin/compartir/tokens/{d['id']}", headers=auth).status_code == 204
    assert client.get(f"{BASE}/api/users/me", headers=bearer(token)).status_code == 401
    assert client.delete(f"/api/admin/compartir/tokens/{d['id']}", headers=auth).status_code == 204
    assert client.get("/api/admin/compartir/tokens", headers=auth).json()["tokens"] == []
    assert client.delete("/api/admin/compartir/tokens/99999", headers=auth).status_code == 404
    assert client.get(f"{BASE}/api/users/me", headers=bearer("gpc_" + "0" * 48)).status_code == 401
    assert {"compartir_token_emitido", "compartir_token_revocado"} <= set(acciones(client, auth))


def test_ciclo_completo(client, auth, tk):
    p = publicar(client, tk)
    slug, ident = "humedales-de-narino", p["id"]
    assert p["slug"] == slug and p["username"] == "admin" and p["title"] == "Humedales de Nariño"
    assert p["projectUrl"] == p["viewerUrl"] == f"{URL}/?compartido=admin/{slug}#mapa"
    assert p["rawJsonUrl"] == f"{URL}/api/compartir/admin/{slug}.geolibre.json"
    assert p["versionCount"] == 1 and p["canEdit"] is True and p["featured"] is True and p["visibility"] == "public"
    # Listados
    publica = client.get(f"{BASE}/api/projects?limit=5").json()
    assert publica["total"] == 1 and publica["limit"] == 5 and publica["offset"] == 0
    assert publica["projects"][0]["id"] == ident and "canEdit" not in publica["projects"][0]
    assert client.get(f"{BASE}/api/projects?mine=true", headers=bearer(tk)).json()["projects"][0]["canEdit"] is True
    assert client.get(f"{BASE}/api/projects?mine=true").status_code == 401
    assert client.get(f"{BASE}/api/projects?featured=true").json()["total"] == 1
    assert client.get(f"{BASE}/api/users/admin/projects").json()["total"] == 1
    assert client.get(f"{BASE}/api/users/ADMIN/projects").json()["total"] == 0  # el usuario se compara exacto
    assert client.get(f"{BASE}/api/users/nadie/projects").json() == {"projects": [], "limit": 24, "offset": 0, "total": 0}
    # JSON público con ETag
    contenido = proyecto()
    r = client.get(f"{BASE}/admin/{slug}.geolibre.json")
    assert r.status_code == 200 and r.text == contenido and r.headers["content-type"].startswith("application/json")
    assert r.headers["cache-control"] == "public, no-cache" and r.headers["x-content-type-options"] == "nosniff"
    etag = r.headers["etag"]
    assert etag == f'"{ident}-v1"'
    for cabecera in (etag, f"W/{etag}", f'"otro", {etag}', "*"):
        r304 = client.get(f"{BASE}/admin/{slug}.geolibre.json", headers={"If-None-Match": cabecera})
        assert r304.status_code == 304 and r304.headers["etag"] == etag and r304.content == b"", cabecera
    assert client.head(f"{BASE}/admin/{slug}.geolibre.json").status_code == 200
    assert client.get(f"{BASE}/api/projects/{ident}").json()["project"]["views"] == 1  # ni el 304 ni HEAD cuentan
    pagina = client.get(f"{BASE}/admin/{slug}", follow_redirects=False)
    assert pagina.status_code == 302 and pagina.headers["location"] == p["projectUrl"]
    # Versiones: con la esperada, sin aviso; con una desfasada se guarda igual y avisa (contrato v1)
    cuerpo = {"content": proyecto("Humedales v2"), "expectedVersion": 1}
    r = client.put(f"{BASE}/api/projects/{ident}/content", headers=bearer(tk), json=cuerpo)
    assert r.status_code == 201 and r.json()["version"] == 2 and "warning" not in r.json()
    assert r.json()["project"]["versionCount"] == 2
    r = client.put(f"{BASE}/api/projects/{ident}/content", headers=bearer(tk), json={"content": proyecto("Humedales v3"), "expectedVersion": 1})
    assert r.status_code == 201 and r.json()["version"] == 3 and "version conflict" in r.json()["warning"]
    assert client.put(f"{BASE}/api/projects/{ident}/content", headers=bearer(tk), json={"content": proyecto(), "expectedVersion": "3"}).status_code == 422
    v = client.get(f"{BASE}/api/projects/{ident}/versions", headers=bearer(tk))
    assert v.status_code == 200 and [x["number"] for x in v.json()["versions"]] == [3, 2, 1]
    assert v.json()["versions"][0]["url"] == f"{URL}/api/compartir/api/projects/{ident}/versions/3"
    assert client.get(f"{BASE}/api/projects/{ident}/versions").status_code == 401
    v1 = client.get(f"{BASE}/api/projects/{ident}/versions/1")
    assert v1.status_code == 200 and v1.text == contenido and v1.headers["etag"] == f'"{ident}-v1"'
    for n in ("9", "0", "abc"):
        assert client.get(f"{BASE}/api/projects/{ident}/versions/{n}").status_code == 404, n
    r = client.get(f"{BASE}/admin/{slug}.geolibre.json", headers={"If-None-Match": etag})
    assert r.status_code == 200 and r.headers["etag"] == f'"{ident}-v3"' and json.loads(r.text)["name"] == "Humedales v3"
    # Borrar
    assert client.delete(f"{BASE}/api/projects/{ident}", headers=bearer(tk)).status_code == 204
    assert client.get(f"{BASE}/admin/{slug}.geolibre.json").status_code == 404
    assert client.get(f"{BASE}/api/projects/{ident}").status_code == 404
    assert client.get(f"{BASE}/api/projects").json()["total"] == 0
    from app.db import session_scope
    from app.models import SharedProjectVersion

    with session_scope() as s:
        assert s.query(SharedProjectVersion).filter_by(project_id=ident).count() == 0
    assert {"compartir_publicacion", "compartir_actualizacion", "compartir_eliminacion"} <= set(acciones(client, auth))


def test_visibilidad_y_permisos(client, auth, tk, editora):
    ed = editora["token"]
    privado = publicar(client, ed, "private", nombre="Borrador privado")
    oculto = publicar(client, ed, "unlisted", nombre="Enlace no listado")
    del_admin = publicar(client, tk, "public", nombre="Mapa oficial")
    del_editor = publicar(client, ed, "public", nombre="Mapa de la editora")
    assert del_admin["featured"] is True and del_editor["featured"] is False
    # Privado: solo su dueño, con su token
    raw = f"{BASE}/editora/borrador-privado.geolibre.json"
    assert client.get(raw).status_code == 404 and client.get(f"{BASE}/api/projects/{privado['id']}").status_code == 404
    assert client.get(raw, headers=bearer(tk)).status_code == 404  # tampoco un administrador
    assert client.get(f"{BASE}/editora/borrador-privado", follow_redirects=False).status_code == 404
    r = client.get(raw, headers=bearer(ed))
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store" and "etag" not in r.headers
    r = client.get(f"{BASE}/api/projects/{privado['id']}", headers=bearer(ed))
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store"
    # No listado: legible con su dirección, fuera de los listados públicos
    assert client.get(f"{BASE}/editora/enlace-no-listado.geolibre.json").status_code == 200
    publicos = {x["id"] for x in client.get(f"{BASE}/api/projects").json()["projects"]}
    assert publicos == {del_admin["id"], del_editor["id"]}
    assert {x["id"] for x in client.get(f"{BASE}/api/projects?featured=true").json()["projects"]} == {del_admin["id"]}
    assert client.get(f"{BASE}/api/projects?mine=true", headers=bearer(ed)).json()["total"] == 3
    assert client.get(f"{BASE}/api/users/editora/projects").json()["total"] == 1
    assert client.get(f"{BASE}/api/users/editora/projects", headers=bearer(ed)).json()["total"] == 3
    assert client.get(f"{BASE}/api/users/editora/projects", headers=bearer(tk)).json()["total"] == 1
    assert client.get(f"{BASE}/api/projects?shared_with_me=true", headers=bearer(ed)).json()["total"] == 0
    # Permisos de escritura
    cuerpo = {"content": proyecto()}
    assert client.put(f"{BASE}/api/projects/{del_admin['id']}/content", headers=bearer(ed), json=cuerpo).status_code == 403
    assert client.put(f"{BASE}/api/projects/{privado['id']}/content", headers=bearer(tk), json=cuerpo).status_code == 404
    assert client.put(f"{BASE}/api/projects/{oculto['id']}/content", headers=bearer(tk), json=cuerpo).status_code == 403
    assert client.delete(f"{BASE}/api/projects/{del_admin['id']}", headers=bearer(ed)).status_code == 403
    assert client.delete(f"{BASE}/api/projects/00000000-0000-4000-8000-000000000000", headers=bearer(ed)).status_code == 404
    # Un administrador puede retirar el proyecto de otro (moderación)
    assert client.delete(f"{BASE}/api/projects/{privado['id']}", headers=bearer(tk)).status_code == 204
    assert client.get(f"{BASE}/api/projects?mine=true", headers=bearer(ed)).json()["total"] == 2
    # Tokens: el editor ve los suyos; «todos» es del administrador
    assert client.get("/api/admin/compartir/tokens?todos=true", headers=editora["sesion"]).status_code == 403
    assert len(client.get("/api/admin/compartir/tokens?todos=true", headers=auth).json()["tokens"]) == 2
    mios = client.get("/api/admin/compartir/tokens", headers=editora["sesion"]).json()["tokens"]
    assert [t["username"] for t in mios] == ["editora"]
    otro = client.get("/api/admin/compartir/tokens", headers=auth).json()["tokens"][0]["id"]
    assert client.delete(f"/api/admin/compartir/tokens/{otro}", headers=editora["sesion"]).status_code == 404
    # Un token presentado y no válido siempre es 401, también en lo público
    assert client.get(f"{BASE}/api/projects", headers=bearer("gpc_" + "0" * 48)).status_code == 401
    assert client.get(f"{BASE}/api/projects", headers={"Authorization": "Basic eDp5"}).status_code == 401
    # Usuario desactivado: su token deja de autenticar
    assert client.put(f"/api/admin/usuarios/{editora['id']}", headers=auth, json={"active": False}).status_code == 200
    assert client.get(f"{BASE}/api/users/me", headers=bearer(ed)).status_code == 401


def test_rutas_opcionales_y_errores(client, tk):
    h = bearer(tk)
    for ruta in ("/api/shares", "/api/shares/x", "/api/organizations/mine", "/api/groups/mine", "/api/transfers/incoming", "/api/transfers/outgoing"):
        r = client.get(BASE + ruta, headers=h)
        assert r.status_code == 404 and r.json()["error"] == r.json()["detail"] and "no está disponible" in r.json()["error"], ruta
    assert client.delete(f"{BASE}/api/shares/x", headers=h).status_code == 404
    assert client.get(f"{BASE}/api/collections/browse").json() == {"collections": []}
    assert client.get(f"{BASE}/api/collections/ana/rios").status_code == 404
    ident = publicar(client, tk)["id"]
    casos = {("PATCH", f"/api/projects/{ident}"): 405, ("POST", "/api/users/me"): 405, ("GET", f"/api/projects/{ident}/content"): 405,
             ("DELETE", "/api/projects"): 405, ("GET", "/api/nada"): 404, ("GET", ""): 404, ("GET", "/"): 404,
             ("POST", "/admin/humedales-de-narino.geolibre.json"): 405, ("DELETE", "/admin/humedales-de-narino"): 405,
             ("GET", "/a/b/c"): 404, ("GET", "/api/projects/no-es-un-uuid"): 404, ("GET", "/api"): 404}
    for (metodo, ruta), estado in casos.items():
        r = client.request(metodo, BASE + ruta, headers=h)
        assert r.status_code == estado and r.json()["error"] == r.json()["detail"], (metodo, ruta, r.status_code, r.text)
        assert r.headers["cache-control"] == "no-store"
    for consulta in ("limit=0", "limit=101", "limit=abc", "offset=-1", "mine=quizás", "mine=true&shared_with_me=true",
                     "shared_source=groups", "shared_with_me=true&shared_source=otra"):
        assert client.get(f"{BASE}/api/projects?{consulta}", headers=h).status_code == 422, consulta
    assert client.get(f"{BASE}/api/projects?shared_with_me=true").status_code == 401
    assert client.get(f"{BASE}/api/projects?shared_with_me=true&shared_source=groups", headers=h).json()["total"] == 0


def test_validacion_del_proyecto(client, tk):
    h = bearer(tk)

    def enviar(cuerpo):
        return client.post(f"{BASE}/api/projects", headers=h, json=cuerpo)

    assert client.post(f"{BASE}/api/projects", headers=h, content=b"{roto").status_code == 422
    assert enviar([1]).status_code == 422
    for contenido in (None, 5, "", "no es JSON", "[]", "{}", '{"version": "1", "layers": {}}', '{"version": true, "layers": []}',
                      '{"version": "", "layers": []}', '{"layers": []}', '{"version": NaN, "layers": []}'):
        r = enviar({"filename": "a.geolibre.json", "content": contenido})
        assert r.status_code == 422 and r.json()["error"].startswith("content"), contenido
    for extra in ({"visibility": "organization"}, {"visibility": "todos"}, {"organizationId": "org"}, {"groupIds": ["g"]}, {"filename": 5}):
        assert enviar({"content": proyecto(), **extra}).status_code == 422, extra
    assert enviar({"content": proyecto("t" * 101)}).status_code == 422
    # «filename» solo da el título de respaldo: nada de rutas
    r = enviar({"filename": "../../etc/passwd.geolibre.json", "content": proyecto(None)})
    assert r.status_code == 201 and r.json()["project"]["slug"] == "passwd" and r.json()["project"]["visibility"] == "private"
    assert enviar({"content": proyecto("¡¿?!")}).json()["project"]["slug"] == "proyecto"
    slugs = [enviar({"content": proyecto("Páramo de Chiles"), "visibility": "public"}).json()["project"]["slug"] for _ in range(2)]
    assert slugs == ["paramo-de-chiles", "paramo-de-chiles-2"]
    titulo = json.loads(proyecto())
    titulo["title"] = "Título explícito"
    assert enviar({"content": json.dumps(titulo)}).json()["project"]["title"] == "Título explícito"


def test_limites_de_tamano_cupo_y_versiones(client, tk):
    from app import config

    ajustes = config.get_settings()
    h = bearer(tk)
    ajustes.share_max_mb = 1
    r = client.post(f"{BASE}/api/projects", headers=h, json={"content": proyecto(relleno="x" * 1_100_000)})
    assert r.status_code == 413 and "1 MB" in r.json()["error"]
    r = client.post(f"{BASE}/api/projects", headers=h, content=b'{"content": "' + b"x" * 3_200_000 + b'"}')
    assert r.status_code == 413
    ajustes.share_max_mb = 10
    # Versiones conservadas: las 3 últimas; «versionCount» sigue siendo el número de la vigente
    ajustes.share_max_versions = 3
    ident = publicar(client, tk)["id"]
    for n in range(4):
        r = client.put(f"{BASE}/api/projects/{ident}/content", headers=h, json={"content": proyecto(f"v{n + 2}")})
        assert r.status_code == 201 and r.json()["version"] == n + 2
    assert [v["number"] for v in client.get(f"{BASE}/api/projects/{ident}/versions", headers=h).json()["versions"]] == [5, 4, 3]
    assert client.get(f"{BASE}/api/projects/{ident}").json()["project"]["versionCount"] == 5
    assert client.get(f"{BASE}/api/projects/{ident}/versions/2").status_code == 404
    # Cupo por usuario y hora (publicaciones y versiones nuevas)
    ajustes.share_max_per_hour = 6
    r = client.post(f"{BASE}/api/projects", headers=h, json={"content": proyecto()})
    assert r.status_code == 201
    r = client.post(f"{BASE}/api/projects", headers=h, json={"content": proyecto()})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0 and r.json()["error"] == r.json()["detail"]
    assert client.put(f"{BASE}/api/projects/{ident}/content", headers=h, json={"content": proyecto()}).status_code == 429


def test_obtener_token_lleva_a_mi_cuenta(client):
    """«Obtener token de API» de GeoLibre abre ${shareUrl}/settings: lleva a «Mi cuenta» del administrador."""
    r = client.get(f"{BASE}/settings", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].endswith("/admin/#cuenta")
    assert client.post(f"{BASE}/settings").status_code == 405
