"""Pruebas de la edición PHP + MySQL (la que se instala subiendo archivos a Plesk).

Requieren PHP 8.1+ con pdo_mysql y un servidor MySQL/MariaDB. Variables:
  GP_MYSQL_HOST (127.0.0.1), GP_MYSQL_PORT (3306), GP_MYSQL_USER (root), GP_MYSQL_PASSWORD ('')
Se omiten si no hay PHP o MySQL disponibles.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

RAIZ_REPO = Path(__file__).resolve().parents[2]
MYSQL = {
    "host": os.getenv("GP_MYSQL_HOST", "127.0.0.1"),
    "port": os.getenv("GP_MYSQL_PORT", "3306"),
    "user": os.getenv("GP_MYSQL_USER", "root"),
    "password": os.getenv("GP_MYSQL_PASSWORD", ""),
}


def _php(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["php", *args], capture_output=True, text=True, check=False)


def _mysql(sql: str) -> None:
    codigo = (
        "$p=new PDO('mysql:host='.getenv('H').';port='.getenv('P'), getenv('U'), getenv('W'));"
        "$p->exec(getenv('SQL'));"
    )
    env = os.environ | {"H": MYSQL["host"], "P": MYSQL["port"], "U": MYSQL["user"], "W": MYSQL["password"], "SQL": sql}
    r = subprocess.run(["php", "-r", codigo], capture_output=True, text=True, env=env, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def sitio(tmp_path_factory):
    if shutil.which("php") is None or "pdo_mysql" not in _php("-m").stdout:
        pytest.skip("PHP con pdo_mysql no disponible")
    base_datos = "gp_prueba_" + uuid.uuid4().hex[:8]
    try:
        _mysql(f"CREATE DATABASE `{base_datos}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except Exception as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"MySQL no disponible: {exc}")
    raiz_web = tmp_path_factory.mktemp("www")
    # Sin la compilación de GeoLibre (≈200 MB) si se descargó localmente: las pruebas la simulan
    portal = RAIZ_REPO / "portal"
    shutil.copytree(portal, raiz_web / "geoportal", ignore=lambda d, n: ["geolibre", "config.php"] if Path(d) == portal else [])
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        ["php", "-d", "upload_max_filesize=64M", "-d", "post_max_size=64M", "-S", f"127.0.0.1:{puerto}", "-t", str(raiz_web), str(Path(__file__).with_name("router.php"))],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{puerto}/geoportal/"
    for _ in range(50):
        try:
            httpx.get(url + "api/salud", timeout=1)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield {
        "url": url,
        "raiz": raiz_web / "geoportal",
        "datos": raiz_web.parent / f"datos-{raiz_web.name}",
        "bd": base_datos,
    }
    proceso.terminate()
    _mysql(f"DROP DATABASE IF EXISTS `{base_datos}`")
