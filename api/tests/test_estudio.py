"""Estudio SIG: GeoLibre integrado, su política de despliegue y la API que lo sirve."""

from __future__ import annotations

import json

from test_api import _upload


def _instalar_falso(tmp_path, monkeypatch):
    """Simula la compilación web de GeoLibre instalada (sin descargarla)."""
    carpeta = tmp_path / "geolibre"
    carpeta.mkdir()
    (carpeta / "index.html").write_text("<!doctype html><title>GeoLibre</title>", encoding="utf-8")
    (carpeta / ".version-geoportal").write_text("3.9.0", encoding="utf-8")
    monkeypatch.setenv("GEOPORTAL_GEOLIBRE_DIR", str(carpeta))
    return carpeta


def test_estudio_valores_por_defecto(client, auth, tmp_path, monkeypatch):
    monkeypatch.setenv("GEOPORTAL_GEOLIBRE_DIR", str(tmp_path / "sin-geolibre"))
    r = client.get("/api/admin/geolibre", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["ajustes"]["idioma"] == "es"
    assert d["ajustes"]["color_acento"] == "#10A13B"
    assert d["estado"]["instalado"] is False
    assert d["estado"]["version_disponible"] == "3.9.0"
    assert d["integrado"] is False
    p = d["politica"]
    assert p["version"] == 1
    # Compartir y Galería con el servicio del propio geoportal
    assert p["sharing"]["shareUrl"] == "http://portal.test/api/compartir"
    # El origen del portal y sus variantes http/https y con «www.»
    assert p["sharing"]["embedOrigins"] == ["http://portal.test", "https://portal.test", "https://www.portal.test", "http://www.portal.test"]
    assert p["ai"] == {"enabled": False}
    assert p["branding"]["appName"] == "Geoportal Ambiental"
    assert set(p["capabilities"]) == set(d["opciones"]["capacidades"])
    # Sin instalar, el visor usa la instancia externa
    cfg = client.get("/api/config").json()
    assert cfg["estudio"]["activo"] is False
    assert cfg["geolibre_url"] == "http://visor.test"


def test_estudio_validacion(client, auth):
    for malo in ({"nivel": "experto"}, {"idioma": "xx"}, {"color_acento": "verde"}, {"url_colaboracion": "http://relé"},
                 {"url_compartir": "ftp://x"}, {"geolens_url": "http://inseguro"}, {"servicios": [{"name": "Sin URL", "kind": "wms"}]},
                 {"url_externa": "ftp://geolibre"}, {"nombre": "x"}):
        r = client.put("/api/admin/geolibre", headers=auth, json=malo)
        assert r.status_code == 422, malo
    r = client.put(
        "/api/admin/geolibre",
        headers=auth,
        json={
            "menus_ocultos": ["help", "no-existe"],
            "capacidades": ["project:edit", "inventada"],
            "elementos_ocultos": "help.diagnostics, project.recent",
            "servicios": [
                {"name": "IDEAM", "kind": "wms", "fields": {"url": "https://ideam.example/wms", "layers": "a"}},
                {"name": "IDEAM", "kind": "xyz", "fields": {"url": "https://ideam.example/{z}/{x}/{y}.png"}},
            ],
        },
    )
    assert r.status_code == 200
    a = r.json()["ajustes"]
    assert a["menus_ocultos"] == ["help"]
    assert a["capacidades"] == ["project:edit"]
    assert a["elementos_ocultos"] == ["help.diagnostics", "project.recent"]
    assert [s["id"] for s in a["servicios"]] == ["ideam", "ideam-2"]
    pol = r.json()["politica"]
    assert pol["interface"]["hiddenMenus"] == ["help"]
    assert "allowed" not in pol["plugins"]  # omitido: cualquier complemento externo
    pol = client.put("/api/admin/geolibre", headers=auth, json={"restringir_complementos": True, "complementos_permitidos": ""}).json()["politica"]
    assert pol["plugins"]["allowed"] == []  # lista vacía: ningún complemento externo
    pol = client.put("/api/admin/geolibre", headers=auth, json={"complementos_permitidos": "geolens, stac"}).json()["politica"]
    assert pol["plugins"]["allowed"] == ["geolens", "stac"]
    assert pol["services"]["catalog"][0]["fields"] == {"url": "https://ideam.example/wms", "layers": "a"}


def test_estudio_integrado_escribe_politica(client, auth, tmp_path, monkeypatch):
    carpeta = _instalar_falso(tmp_path, monkeypatch)
    r = client.put(
        "/api/admin/geolibre",
        headers=auth,
        json={"usar_integrado": True, "nombre": "Estudio Ambiental", "modo": "visor", "acento": "emerald", "compartir_propio": True},
    )
    assert r.status_code == 200
    assert r.json()["archivos_escritos"] is True
    assert r.json()["integrado"] is True
    dep = json.loads((carpeta / "deployment.json").read_text(encoding="utf-8"))
    assert dep["branding"] == {"appName": "Estudio Ambiental", "welcome": False}
    # Compartir y Galería con el servicio del propio geoportal (share.geolibre.app no responde a otros dominios)
    assert dep["sharing"]["shareUrl"] == "http://portal.test/api/compartir"
    interfaz = json.loads((carpeta / "geoportal-ajustes.json").read_text(encoding="utf-8"))
    # Por defecto, la disposición completa de web.geolibre.app: menús con texto y todos los paneles
    assert interfaz == {
        "type": "geolibre-interface", "version": 1, "language": "es", "theme": {"scheme": "emerald", "customColor": "#10A13B"},
        "layout": {"toolbarLabels": True, "showProjectInfo": True, "compactLayerList": False, "layerPanelVisible": True,
                   "browserPanelVisible": True, "stylePanelVisible": True, "commentsPanelVisible": True, "bottomPanelsUnderMap": True},
    }
    assert dep["interface"]["level"] == "advanced"
    assert client.get("/api/geolibre/deployment.json").json() == dep
    assert client.get("/api/geolibre/ajustes.json").json() == interfaz

    # GeoLibre copiado a mano trae un deployment.json vacío: /api/config lo regenera
    (carpeta / "deployment.json").write_text("null", encoding="utf-8")
    (carpeta / "geoportal-ajustes.json").unlink()
    client.get("/api/config")
    assert json.loads((carpeta / "deployment.json").read_text(encoding="utf-8")) == dep
    assert (carpeta / "geoportal-ajustes.json").is_file()
    # Un archivo de interfaz que no coincide con los ajustes (versión anterior, sin «layout») se regenera
    (carpeta / "geoportal-ajustes.json").write_text('{"type":"geolibre-interface","version":1,"language":"es"}', encoding="utf-8")
    assert client.get("/api/config").json()["estudio"]["paneles_plegados"] is False
    assert json.loads((carpeta / "geoportal-ajustes.json").read_text(encoding="utf-8")) == interfaz
    assert "panels=collapsed" not in client.get("/api/config").json()["geolibre_proyecto_url"]

    # Preajuste «Esencial» (compacto): barra con iconos, lista compacta y paneles plegados
    compacto = {"nivel": "intermediate", "paneles_plegados": True, "lista_compacta": True, "etiquetas_barra": False, "info_proyecto": False,
                "panel_explorador": False, "panel_comentarios": False}
    r = client.put("/api/admin/geolibre", headers=auth, json=compacto)
    assert r.json()["politica"]["interface"]["level"] == "intermediate"
    assert client.get("/api/geolibre/ajustes.json").json()["layout"]["toolbarLabels"] is False
    assert "&panels=collapsed" in client.get("/api/config").json()["geolibre_proyecto_url"]

    cfg = client.get("/api/config").json()
    assert cfg["estudio"]["activo"] is True
    assert cfg["estudio"]["version"] == "3.9.0"
    assert cfg["geolibre_url"] == "http://portal.test/geolibre"
    assert cfg["estudio"]["ajustes_url"] == "http://portal.test/geolibre/geoportal-ajustes.json"
    # Modo visor: el enlace del proyecto abre GeoLibre en modo de solo consulta
    assert cfg["geolibre_proyecto_url"].startswith("http://portal.test/geolibre/?url=")
    assert "settingsUrl=" in cfg["geolibre_proyecto_url"] and cfg["geolibre_proyecto_url"].endswith("&layout=viewer")
    assert not cfg["geolibre_editor_url"].endswith("&layout=viewer")


def test_estudio_instancia_externa(client, auth, tmp_path, monkeypatch):
    _instalar_falso(tmp_path, monkeypatch)
    r = client.put("/api/admin/geolibre", headers=auth, json={"usar_integrado": False, "url_externa": "https://gis.example.org/geolibre/"})
    assert r.status_code == 200
    assert r.json()["integrado"] is False
    assert r.json()["url_externa"] == "https://gis.example.org/geolibre"
    cfg = client.get("/api/config").json()
    assert cfg["estudio"]["activo"] is False
    assert cfg["geolibre_url"] == "https://gis.example.org/geolibre"
    assert cfg["geolibre_proyecto_url"].startswith("https://gis.example.org/geolibre/?url=")
    # Volver al integrado conserva la URL externa para la próxima vez
    r = client.put("/api/admin/geolibre", headers=auth, json={"usar_integrado": True})
    assert r.json()["integrado"] is True and r.json()["url_externa"] == "https://gis.example.org/geolibre"


def test_estudio_solo_administradores(client, auth):
    r = client.post("/api/admin/usuarios", headers=auth, json={"username": "editora", "password": "Editora-Segura-2026", "role": "editor"})
    assert r.status_code in (200, 201)
    t = client.post("/api/auth/ingresar", json={"username": "editora", "password": "Editora-Segura-2026"}).json()["access_token"]
    ed = {"Authorization": f"Bearer {t}"}
    assert client.get("/api/admin/geolibre", headers=ed).status_code == 403
    assert client.put("/api/admin/geolibre", headers=ed, json={"nombre": "Otro"}).status_code == 403
    assert client.post("/api/admin/geolibre/instalar", headers=ed).status_code == 403


def test_proyecto_base_e_ids_estables(client, auth, geojson_file):
    r = _upload(client, auth, geojson_file, {"title": "Humedales"})
    assert r.status_code == 201, r.text
    capa = r.json()["capa"]
    assert client.post(f"/api/admin/capas/{capa['id']}/publicacion?publicar=true", headers=auth).status_code == 200
    publica = next(c for c in client.get("/api/capas").json() if c["slug"] == capa["slug"])
    assert len(publica["geolibre_id"]) == 36
    proyecto = client.get("/api/proyecto.geolibre?base=oscuro").json()
    assert proyecto["basemapStyleUrl"] == "https://tiles.openfreemap.org/styles/dark"
    assert any(l["id"] == publica["geolibre_id"] for l in proyecto["layers"])
    # Un mapa base desconocido conserva el configurado
    assert client.get("/api/proyecto.geolibre?base=no-existe").json()["basemapStyleUrl"].startswith("https://")
    uno = client.get(f"/api/capas/{capa['slug']}/proyecto.geolibre?base=claro").json()
    assert uno["basemapStyleUrl"].endswith("/positron")
    assert uno["layers"][0]["id"] == publica["geolibre_id"]


def test_cors_sigue_a_la_instancia_externa(client, auth):
    acao = "access-control-allow-origin"
    assert client.get("/api/capas", headers={"Origin": "http://visor.test"}).headers.get(acao) == "http://visor.test"
    assert acao not in client.get("/api/capas", headers={"Origin": "https://otro.sitio"}).headers
    client.put("/api/admin/geolibre", headers=auth, json={"usar_integrado": False, "url_externa": "https://gis.example.org/geolibre"})
    assert client.get("/api/capas", headers={"Origin": "https://gis.example.org"}).headers.get(acao) == "https://gis.example.org"
    pre = client.options("/api/capas", headers={"Origin": "https://gis.example.org", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "range"})
    assert pre.status_code == 200 and pre.headers.get(acao) == "https://gis.example.org"
    assert acao not in client.get("/api/capas", headers={"Origin": "http://visor.test"}).headers


def test_ajustes_de_la_revision_anterior_pasan_a_la_interfaz_completa(client, auth, tmp_path, monkeypatch):
    """Ajustes guardados con la presentación compacta (revisión 1) se leen con la disposición completa."""
    from app.config import get_settings

    _instalar_falso(tmp_path, monkeypatch)
    viejos = {"nombre": "Mi Estudio", "nivel": "intermediate", "etiquetas_barra": False, "lista_compacta": True, "paneles_plegados": True,
              "panel_explorador": False, "panel_comentarios": False, "compartir_publico": True, "servicios_predeterminados": False}
    (get_settings().data_dir / "geolibre-ajustes.json").write_text(json.dumps(viejos), encoding="utf-8")
    a = client.get("/api/admin/geolibre", headers=auth).json()["ajustes"]
    assert a["nombre"] == "Mi Estudio" and a["servicios_predeterminados"] is False  # lo demás se conserva
    assert a["nivel"] == "advanced" and a["etiquetas_barra"] is True and a["paneles_plegados"] is False and a["lista_compacta"] is False
    assert "compartir_publico" not in a and a["compartir_propio"] is True and a["revision"] == 2
    # Una vez guardados con la revisión 2, los valores elegidos se respetan
    client.put("/api/admin/geolibre", headers=auth, json={"etiquetas_barra": False})
    assert client.get("/api/admin/geolibre", headers=auth).json()["ajustes"]["etiquetas_barra"] is False


def test_apariencia_institucional_opcional(client, auth, tmp_path, monkeypatch):
    """Sin la apariencia institucional no se envía ?settingsUrl= y GeoLibre guarda los ajustes del visitante."""
    _instalar_falso(tmp_path, monkeypatch)
    client.put("/api/admin/geolibre", headers=auth, json={"usar_integrado": True})
    cfg = client.get("/api/config").json()
    assert cfg["estudio"]["ajustes_url"].endswith("/geolibre/geoportal-ajustes.json") and "settingsUrl=" in cfg["geolibre_editor_url"]
    client.put("/api/admin/geolibre", headers=auth, json={"apariencia_institucional": False})
    cfg = client.get("/api/config").json()
    assert cfg["estudio"]["ajustes_url"] is None and "settingsUrl=" not in cfg["geolibre_editor_url"]
    r = client.put("/api/admin/geolibre", headers=auth, json={"compartir_propio": False})
    assert r.json()["politica"]["sharing"]["shareUrl"] == "off"
    r = client.put("/api/admin/geolibre", headers=auth, json={"url_compartir": "https://proyectos.example.org"})
    assert r.json()["politica"]["sharing"]["shareUrl"] == "https://proyectos.example.org"
