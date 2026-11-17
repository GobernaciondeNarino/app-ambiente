"""Servicio de compartir de GeoLibre (contrato v1) en la edición PHP + MySQL: tablas en instalaciones
existentes, tokens personales, ciclo completo, visibilidad, rutas opcionales y límites.
Mismas comprobaciones que api/tests/test_compartir.py. El sitio vive en una subcarpeta (/geoportal/).
Las pruebas comparten la base de datos del módulo: cada una usa sus propios títulos y no cuenta totales ajenos."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

import httpx
import pytest
from conftest import MYSQL, instalar_sitio
from test_edicion_php import CLAVE

CLAVE_EDITORA = "Editora-2026!"


def consulta(sitio, sql: str) -> list[dict]:
    """Ejecuta SQL en la base de datos de la prueba (filas como diccionarios; [] si no devuelve filas)."""
    codigo = (
        "$p=new PDO('mysql:host='.getenv('H').';port='.getenv('P').';dbname='.getenv('D').';charset=utf8mb4', getenv('U'), getenv('W'));"
        "$s=$p->query(getenv('SQL')); echo json_encode($s->columnCount() ? $s->fetchAll(PDO::FETCH_ASSOC) : []);"
    )
    env = os.environ | {"H": MYSQL["host"], "P": MYSQL["port"], "U": MYSQL["user"], "W": MYSQL["password"], "D": sitio["bd"], "SQL": sql}
    r = subprocess.run(["php", "-r", codigo], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0, r.stderr or r.stdout
    return json.loads(r.stdout)


def opcion(sitio, clave: str, valor: str) -> None:
    consulta(sitio, f"INSERT INTO gp_opciones (clave, valor) VALUES ('{clave}', '{valor}') ON DUPLICATE KEY UPDATE valor = VALUES(valor)")


def proyecto(nombre: str | None = "Humedales de Nariño", capas: int = 1, relleno: str = "") -> str:
    doc = {"version": "1.0", "mapView": {"center": [-77.3, 1.2], "zoom": 8, "bearing": 0, "pitch": 0},
           "layers": [{"id": f"c{i}", "name": f"Capa {i}"} for i in range(capas)], "relleno": relleno}
    if nombre is not None:
        doc["name"] = nombre
    return json.dumps(doc, ensure_ascii=False)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Sitio:
    """Clientes y datos del sitio de prueba: «api» con la sesión del administrador; «base», el servicio."""

    def __init__(self, sitio, jwt: str):
        self.sitio = sitio
        self.url = sitio["url"].rstrip("/")  # http://127.0.0.1:<puerto>/geoportal
        self.base = self.url + "/api/compartir"
        self.sesion = bearer(jwt)
        self.c = httpx.Client(timeout=60, follow_redirects=False)

    def emitir(self, sesion=None, nombre="GeoLibre de pruebas", **extra) -> dict:
        r = self.c.post(self.url + "/api/admin/compartir/tokens", headers=sesion or self.sesion, json={"name": nombre, **extra})
        assert r.status_code == 201, r.text
        return r.json()

    def publicar(self, token, visibilidad="public", **kw) -> dict:
        cuerpo = {"filename": "Humedales.geolibre.json", "content": proyecto(**kw), "visibility": visibilidad}
        r = self.c.post(self.base + "/api/projects", headers=bearer(token), json=cuerpo)
        assert r.status_code == 201, r.text
        return r.json()["project"]

    def acciones(self) -> list[str]:
        return [a["action"] for a in self.c.get(self.url + "/api/admin/bitacora", headers=self.sesion).json()]


@pytest.fixture(scope="module")
def s(sitio):
    sitio_ = Sitio(sitio, instalar_sitio(sitio, CLAVE))
    yield sitio_
    sitio_.c.close()


@pytest.fixture(scope="module")
def tk(s) -> str:
    return s.emitir()["token"]


def test_tablas_en_instalacion_existente(s):
    tablas = "SELECT table_name AS t FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'gp\\_compartir\\_%'"
    assert len(consulta(s.sitio, tablas)) == 3  # instalación nueva: el asistente ya las crea
    # Instalación anterior al servicio: sin tablas ni opción; la primera petición las crea
    consulta(s.sitio, "DROP TABLE gp_compartir_versiones, gp_compartir_proyectos, gp_compartir_tokens")
    consulta(s.sitio, "DELETE FROM gp_opciones WHERE clave = 'compartir_esquema'")
    assert consulta(s.sitio, tablas) == []
    r = s.c.get(s.base + "/api/projects")
    assert r.status_code == 200 and r.json() == {"projects": [], "limit": 24, "offset": 0, "total": 0}
    assert len(consulta(s.sitio, tablas)) == 3
    assert consulta(s.sitio, "SELECT valor FROM gp_opciones WHERE clave = 'compartir_esquema'") == [{"valor": "1"}]


def test_tokens_personales(s):
    d = s.emitir(nombre="  Portátil de la Secretaría  ", expires_in_days=30)
    token = d["token"]
    assert token.startswith("gpc_") and len(token) == 52 and d["prefix"] == token[:12]
    assert d["name"] == "Portátil de la Secretaría" and d["username"] == "admin"
    assert d["share_url"] == s.base and d["expires_at"] and d["expired"] is False
    lista = s.c.get(s.url + "/api/admin/compartir/tokens", headers=s.sesion)
    assert lista.status_code == 200 and token not in lista.text and lista.json()["share_url"] == s.base
    assert d["id"] in [t["id"] for t in lista.json()["tokens"]]
    # Solo se guarda el SHA-256
    fila = consulta(s.sitio, f"SELECT * FROM gp_compartir_tokens WHERE id = {int(d['id'])}")[0]
    assert fila["token_hash"] == hashlib.sha256(token.encode()).hexdigest() and token not in json.dumps(fila)
    # Validación
    for cuerpo in ({}, {"name": " "}, {"name": "n" * 101}, {"name": 5}, {"name": "a", "expires_in_days": 0},
                   {"name": "a", "expires_in_days": 366}, {"name": "a", "expires_in_days": "30"}, {"name": "a", "expires_in_days": True}):
        assert s.c.post(s.url + "/api/admin/compartir/tokens", headers=s.sesion, json=cuerpo).status_code == 422, cuerpo
    assert s.c.post(s.url + "/api/admin/compartir/tokens", headers=s.sesion, json=[1]).status_code == 422
    assert s.c.get(s.url + "/api/admin/compartir/tokens?todos=quizás", headers=s.sesion).status_code == 422
    assert s.c.put(s.url + "/api/admin/compartir/tokens", headers=s.sesion, json={}).status_code == 405
    # El token de sesión no sirve en el servicio y el token personal no sirve en el administrador
    r = s.c.get(s.base + "/api/users/me", headers=s.sesion)
    assert r.status_code == 401 and "invalid_token" in r.headers["www-authenticate"]
    r = s.c.get(s.base + "/api/users/me")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer" and r.json()["error"] == r.json()["detail"]
    assert s.c.get(s.url + "/api/admin/compartir/tokens", headers=bearer(token)).status_code == 401
    yo = s.c.get(s.base + "/api/users/me", headers=bearer(token))
    assert yo.status_code == 200 and yo.headers["cache-control"] == "private, no-store"
    assert yo.json()["user"]["username"] == "admin" and yo.json()["sessionId"] is None
    assert yo.json()["user"]["email"] == "sig@ejemplo.gov.co"
    assert set(yo.json()["scopes"]) == {"read:projects", "write:projects", "share:public"}
    usado = [t for t in s.c.get(s.url + "/api/admin/compartir/tokens", headers=s.sesion).json()["tokens"] if t["id"] == d["id"]]
    assert usado[0]["last_used_at"]
    # Revocar: deja de autenticar; repetir es inocuo; un id desconocido es 404
    assert s.c.delete(s.url + f"/api/admin/compartir/tokens/{d['id']}", headers=s.sesion).status_code == 204
    assert s.c.get(s.base + "/api/users/me", headers=bearer(token)).status_code == 401
    assert s.c.delete(s.url + f"/api/admin/compartir/tokens/{d['id']}", headers=s.sesion).status_code == 204
    assert d["id"] not in [t["id"] for t in s.c.get(s.url + "/api/admin/compartir/tokens", headers=s.sesion).json()["tokens"]]
    assert s.c.delete(s.url + "/api/admin/compartir/tokens/99999", headers=s.sesion).status_code == 404
    assert s.c.get(s.base + "/api/users/me", headers=bearer("gpc_" + "0" * 48)).status_code == 401
    assert {"compartir_token_emitido", "compartir_token_revocado"} <= set(s.acciones())


def test_ciclo_completo(s, tk):
    p = s.publicar(tk)
    slug, ident = "humedales-de-narino", p["id"]
    assert p["slug"] == slug and p["username"] == "admin" and p["title"] == "Humedales de Nariño"
    assert p["projectUrl"] == p["viewerUrl"] == f"{s.url}/?compartido=admin/{slug}#mapa"
    assert p["rawJsonUrl"] == f"{s.base}/admin/{slug}.geolibre.json"
    assert p["versionCount"] == 1 and p["canEdit"] is True and p["featured"] is True and p["visibility"] == "public"
    # Listados
    publica = s.c.get(s.base + "/api/projects?limit=5").json()
    assert publica["limit"] == 5 and publica["offset"] == 0 and publica["total"] >= 1
    mio = [x for x in publica["projects"] if x["id"] == ident]
    assert mio and "canEdit" not in mio[0]
    assert ident in [x["id"] for x in s.c.get(s.base + "/api/projects?mine=true", headers=bearer(tk)).json()["projects"]]
    assert s.c.get(s.base + "/api/projects?mine=true").status_code == 401
    assert ident in [x["id"] for x in s.c.get(s.base + "/api/projects?featured=true").json()["projects"]]
    assert ident in [x["id"] for x in s.c.get(s.base + "/api/users/admin/projects").json()["projects"]]
    assert s.c.get(s.base + "/api/users/ADMIN/projects").json()["total"] == 0  # el usuario se compara exacto
    assert s.c.get(s.base + "/api/users/nadie/projects").json() == {"projects": [], "limit": 24, "offset": 0, "total": 0}
    # JSON público con ETag
    contenido = proyecto()
    raw = f"{s.base}/admin/{slug}.geolibre.json"
    r = s.c.get(raw)
    assert r.status_code == 200 and r.text == contenido and r.headers["content-type"].startswith("application/json")
    assert r.headers["cache-control"] == "public, no-cache" and r.headers["x-content-type-options"] == "nosniff"
    etag = r.headers["etag"]
    assert etag == f'"{ident}-v1"'
    for cabecera in (etag, f"W/{etag}", f'"otro", {etag}', "*"):
        r304 = s.c.get(raw, headers={"If-None-Match": cabecera})
        assert r304.status_code == 304 and r304.headers["etag"] == etag and r304.content == b"", cabecera
    assert s.c.head(raw).status_code == 200
    assert s.c.get(s.base + f"/api/projects/{ident}").json()["project"]["views"] == 1  # ni el 304 ni HEAD cuentan
    pagina = s.c.get(f"{s.base}/admin/{slug}")
    assert pagina.status_code == 302 and pagina.headers["location"] == p["projectUrl"]
    # Versiones: con la esperada, sin aviso; con una desfasada se guarda igual y avisa (contrato v1)
    r = s.c.put(s.base + f"/api/projects/{ident}/content", headers=bearer(tk), json={"content": proyecto("Humedales v2"), "expectedVersion": 1})
    assert r.status_code == 201 and r.json()["version"] == 2 and "warning" not in r.json()
    assert r.json()["project"]["versionCount"] == 2
    r = s.c.put(s.base + f"/api/projects/{ident}/content", headers=bearer(tk), json={"content": proyecto("Humedales v3"), "expectedVersion": 1})
    assert r.status_code == 201 and r.json()["version"] == 3 and "version conflict" in r.json()["warning"]
    assert s.c.put(s.base + f"/api/projects/{ident}/content", headers=bearer(tk), json={"content": proyecto(), "expectedVersion": "3"}).status_code == 422
    v = s.c.get(s.base + f"/api/projects/{ident}/versions", headers=bearer(tk))
    assert v.status_code == 200 and [x["number"] for x in v.json()["versions"]] == [3, 2, 1]
    assert v.json()["versions"][0]["url"] == f"{s.base}/api/projects/{ident}/versions/3"
    assert s.c.get(s.base + f"/api/projects/{ident}/versions").status_code == 401
    v1 = s.c.get(s.base + f"/api/projects/{ident}/versions/1")
    assert v1.status_code == 200 and v1.text == contenido and v1.headers["etag"] == f'"{ident}-v1"'
    for n in ("9", "0", "abc"):
        assert s.c.get(s.base + f"/api/projects/{ident}/versions/{n}").status_code == 404, n
    r = s.c.get(raw, headers={"If-None-Match": etag})
    assert r.status_code == 200 and r.headers["etag"] == f'"{ident}-v3"' and json.loads(r.text)["name"] == "Humedales v3"
    # Borrar
    assert s.c.delete(s.base + f"/api/projects/{ident}", headers=bearer(tk)).status_code == 204
    assert s.c.get(raw).status_code == 404
    assert s.c.get(s.base + f"/api/projects/{ident}").status_code == 404
    assert ident not in [x["id"] for x in s.c.get(s.base + "/api/projects").json()["projects"]]
    assert consulta(s.sitio, f"SELECT COUNT(*) AS n FROM gp_compartir_versiones WHERE project_id = '{ident}'") == [{"n": 0}]
    assert {"compartir_publicacion", "compartir_actualizacion", "compartir_eliminacion"} <= set(s.acciones())


def test_visibilidad_y_permisos(s, tk):
    r = s.c.post(s.url + "/api/admin/usuarios", headers=s.sesion, json={"username": "editora", "password": CLAVE_EDITORA, "role": "editor"})
    assert r.status_code == 201, r.text
    id_editora = r.json()["id"]
    sesion_ed = bearer(s.c.post(s.url + "/api/auth/ingresar", json={"username": "editora", "password": CLAVE_EDITORA}).json()["access_token"])
    ed = s.emitir(sesion_ed, "Equipo de la editora")["token"]
    privado = s.publicar(ed, "private", nombre="Borrador privado")
    oculto = s.publicar(ed, "unlisted", nombre="Enlace no listado")
    del_admin = s.publicar(tk, "public", nombre="Mapa oficial")
    del_editor = s.publicar(ed, "public", nombre="Mapa de la editora")
    assert del_admin["featured"] is True and del_editor["featured"] is False
    # Privado: solo su dueño, con su token
    raw = s.base + "/editora/borrador-privado.geolibre.json"
    assert s.c.get(raw).status_code == 404 and s.c.get(s.base + f"/api/projects/{privado['id']}").status_code == 404
    assert s.c.get(raw, headers=bearer(tk)).status_code == 404  # tampoco un administrador
    assert s.c.get(s.base + "/editora/borrador-privado").status_code == 404
    r = s.c.get(raw, headers=bearer(ed))
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store" and "etag" not in r.headers
    r = s.c.get(s.base + f"/api/projects/{privado['id']}", headers=bearer(ed))
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store"
    # No listado: legible con su dirección, fuera de los listados públicos
    assert s.c.get(s.base + "/editora/enlace-no-listado.geolibre.json").status_code == 200
    publicos = {x["id"] for x in s.c.get(s.base + "/api/projects?limit=100").json()["projects"]}
    assert {del_admin["id"], del_editor["id"]} <= publicos and not {privado["id"], oculto["id"]} & publicos
    destacados = {x["id"] for x in s.c.get(s.base + "/api/projects?featured=true&limit=100").json()["projects"]}
    assert del_admin["id"] in destacados and del_editor["id"] not in destacados
    assert s.c.get(s.base + "/api/projects?mine=true", headers=bearer(ed)).json()["total"] == 3
    assert s.c.get(s.base + "/api/users/editora/projects").json()["total"] == 1
    assert s.c.get(s.base + "/api/users/editora/projects", headers=bearer(ed)).json()["total"] == 3
    assert s.c.get(s.base + "/api/users/editora/projects", headers=bearer(tk)).json()["total"] == 1
    assert s.c.get(s.base + "/api/projects?shared_with_me=true", headers=bearer(ed)).json()["total"] == 0
    # Permisos de escritura
    cuerpo = {"content": proyecto()}
    assert s.c.put(s.base + f"/api/projects/{del_admin['id']}/content", headers=bearer(ed), json=cuerpo).status_code == 403
    assert s.c.put(s.base + f"/api/projects/{privado['id']}/content", headers=bearer(tk), json=cuerpo).status_code == 404
    assert s.c.put(s.base + f"/api/projects/{oculto['id']}/content", headers=bearer(tk), json=cuerpo).status_code == 403
    assert s.c.delete(s.base + f"/api/projects/{del_admin['id']}", headers=bearer(ed)).status_code == 403
    assert s.c.delete(s.base + "/api/projects/00000000-0000-4000-8000-000000000000", headers=bearer(ed)).status_code == 404
    # Un administrador puede retirar el proyecto de otro (moderación)
    assert s.c.delete(s.base + f"/api/projects/{privado['id']}", headers=bearer(tk)).status_code == 204
    assert s.c.get(s.base + "/api/projects?mine=true", headers=bearer(ed)).json()["total"] == 2
    # Tokens: el editor ve los suyos; «todos» es del administrador
    assert s.c.get(s.url + "/api/admin/compartir/tokens?todos=true", headers=sesion_ed).status_code == 403
    todos = s.c.get(s.url + "/api/admin/compartir/tokens?todos=true", headers=s.sesion).json()["tokens"]
    assert {t["username"] for t in todos} == {"admin", "editora"}
    assert [t["username"] for t in s.c.get(s.url + "/api/admin/compartir/tokens", headers=sesion_ed).json()["tokens"]] == ["editora"]
    otro = s.c.get(s.url + "/api/admin/compartir/tokens", headers=s.sesion).json()["tokens"][0]["id"]
    assert s.c.delete(s.url + f"/api/admin/compartir/tokens/{otro}", headers=sesion_ed).status_code == 404
    # Un token presentado y no válido siempre es 401, también en lo público
    assert s.c.get(s.base + "/api/projects", headers=bearer("gpc_" + "0" * 48)).status_code == 401
    assert s.c.get(s.base + "/api/projects", headers={"Authorization": "Basic eDp5"}).status_code == 401
    # Usuario desactivado: su token deja de autenticar
    assert s.c.put(s.url + f"/api/admin/usuarios/{id_editora}", headers=s.sesion, json={"active": False}).status_code == 200
    assert s.c.get(s.base + "/api/users/me", headers=bearer(ed)).status_code == 401


def test_rutas_opcionales_y_errores(s, tk):
    h = bearer(tk)
    for ruta in ("/api/shares", "/api/shares/x", "/api/organizations/mine", "/api/groups/mine", "/api/transfers/incoming", "/api/transfers/outgoing"):
        r = s.c.get(s.base + ruta, headers=h)
        assert r.status_code == 404 and r.json()["error"] == r.json()["detail"] and "no está disponible" in r.json()["error"], ruta
    assert s.c.delete(s.base + "/api/shares/x", headers=h).status_code == 404
    assert s.c.get(s.base + "/api/collections/browse").json() == {"collections": []}
    assert s.c.get(s.base + "/api/collections/ana/rios").status_code == 404
    ident = s.publicar(tk, nombre="Rutas del servicio")["id"]
    casos = {("PATCH", f"/api/projects/{ident}"): 405, ("POST", "/api/users/me"): 405, ("GET", f"/api/projects/{ident}/content"): 405,
             ("DELETE", "/api/projects"): 405, ("GET", "/api/nada"): 404, ("GET", ""): 404, ("GET", "/"): 404,
             ("POST", "/admin/rutas-del-servicio.geolibre.json"): 405, ("DELETE", "/admin/rutas-del-servicio"): 405,
             ("GET", "/a/b/c"): 404, ("GET", "/api/projects/no-es-un-uuid"): 404, ("GET", "/api"): 404}
    for (metodo, ruta), estado in casos.items():
        r = s.c.request(metodo, s.base + ruta, headers=h)
        assert r.status_code == estado and r.json()["error"] == r.json()["detail"], (metodo, ruta, r.status_code, r.text)
        assert r.headers["cache-control"] == "no-store"
    for consulta_ in ("limit=0", "limit=101", "limit=abc", "offset=-1", "mine=quizás", "mine=true&shared_with_me=true",
                      "shared_source=groups", "shared_with_me=true&shared_source=otra"):
        assert s.c.get(s.base + f"/api/projects?{consulta_}", headers=h).status_code == 422, consulta_
    assert s.c.get(s.base + "/api/projects?shared_with_me=true").status_code == 401
    assert s.c.get(s.base + "/api/projects?shared_with_me=true&shared_source=groups", headers=h).json()["total"] == 0


def test_validacion_del_proyecto(s, tk):
    h = bearer(tk)

    def enviar(cuerpo):
        return s.c.post(s.base + "/api/projects", headers=h, json=cuerpo)

    assert s.c.post(s.base + "/api/projects", headers=h, content=b"{roto").status_code == 422
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


def test_limites_de_tamano_cupo_y_versiones(s, tk):
    h = bearer(tk)
    opcion(s.sitio, "compartir_max_mb", "1")
    r = s.c.post(s.base + "/api/projects", headers=h, json={"content": proyecto(relleno="x" * 1_100_000)})
    assert r.status_code == 413 and "1 MB" in r.json()["error"]
    r = s.c.post(s.base + "/api/projects", headers=h, content=b'{"content": "' + b"x" * 3_200_000 + b'"}')
    assert r.status_code == 413
    opcion(s.sitio, "compartir_max_mb", "10")
    # Versiones conservadas: las 3 últimas; «versionCount» sigue siendo el número de la vigente
    opcion(s.sitio, "compartir_max_versiones", "3")
    ident = s.publicar(tk, nombre="Versiones limitadas")["id"]
    for n in range(4):
        r = s.c.put(s.base + f"/api/projects/{ident}/content", headers=h, json={"content": proyecto(f"v{n + 2}")})
        assert r.status_code == 201 and r.json()["version"] == n + 2
    assert [v["number"] for v in s.c.get(s.base + f"/api/projects/{ident}/versions", headers=h).json()["versions"]] == [5, 4, 3]
    assert s.c.get(s.base + f"/api/projects/{ident}").json()["project"]["versionCount"] == 5
    assert s.c.get(s.base + f"/api/projects/{ident}/versions/2").status_code == 404
    opcion(s.sitio, "compartir_max_versiones", "20")
    # Cupo por usuario y hora (publicaciones y versiones nuevas): queda espacio para una sola más
    hechas = consulta(s.sitio, "SELECT COUNT(*) AS n FROM gp_bitacora WHERE username = 'admin' AND action IN "
                               "('compartir_publicacion', 'compartir_actualizacion') AND at >= UTC_TIMESTAMP() - INTERVAL 1 HOUR")[0]["n"]
    opcion(s.sitio, "compartir_max_hora", str(int(hechas) + 1))
    try:
        assert s.c.post(s.base + "/api/projects", headers=h, json={"content": proyecto()}).status_code == 201
        r = s.c.post(s.base + "/api/projects", headers=h, json={"content": proyecto()})
        assert r.status_code == 429 and int(r.headers["retry-after"]) > 0 and r.json()["error"] == r.json()["detail"]
        assert s.c.put(s.base + f"/api/projects/{ident}/content", headers=h, json={"content": proyecto()}).status_code == 429
    finally:
        opcion(s.sitio, "compartir_max_hora", "60")


def test_obtener_token_lleva_a_mi_cuenta(s):
    """«Obtener token de API» de GeoLibre abre ${shareUrl}/settings: lleva a «Mi cuenta» del administrador (como Python)."""
    r = s.c.get(s.base + "/settings")
    assert r.status_code == 302 and r.headers["location"] == s.url + "/admin/#cuenta"
    assert s.c.post(s.base + "/settings").status_code == 405
