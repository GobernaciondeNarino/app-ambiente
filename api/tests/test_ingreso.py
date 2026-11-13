"""Límite de intentos de ingreso (mismos umbrales, mensaje y código que la edición PHP)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import ADMIN_PASSWORD
from fastapi.testclient import TestClient

INGRESO = "/api/auth/ingresar"
BUENA = {"username": "admin", "password": ADMIN_PASSWORD}
MALA = {"username": "admin", "password": "mala"}
BLOQUEO = {"detail": "Demasiados intentos fallidos. Espere unos minutos e inténtelo de nuevo."}


def _desde(client, ip: str) -> TestClient:
    """Cliente de la misma aplicación con otra IP de origen."""
    return TestClient(client.app, client=(ip, 50000))


def _mover_fallos(minutos: float) -> None:
    """Fecha los fallos registrados hace «minutos» (simula el paso del tiempo)."""
    from app.db import session_scope
    from app.models import AuditLog

    with session_scope() as s:
        for e in s.query(AuditLog).filter(AuditLog.action == "ingreso_fallido"):
            e.at = datetime.now(timezone.utc) - timedelta(minutes=minutos)
        s.commit()


def test_bloqueo_por_usuario_e_ip_sin_dejar_fuera_a_otra_ip(client, auth):
    a, b = _desde(client, "203.0.113.5"), _desde(client, "198.51.100.7")
    for _ in range(5):
        assert a.post(INGRESO, json=MALA).status_code == 401
    # Bloqueado: ni la contraseña correcta entra, y lleva Retry-After
    r = a.post(INGRESO, json=BUENA)
    assert r.status_code == 429 and r.json() == BLOQUEO and 890 <= int(r.headers["retry-after"]) <= 900
    assert a.post(INGRESO, json=MALA).status_code == 429
    # Otra IP sigue entrando con la clave correcta; otro usuario desde la IP bloqueada no está bloqueado
    assert b.post(INGRESO, json=BUENA).status_code == 200
    assert a.post(INGRESO, json={"username": "otra", "password": "x"}).status_code == 401
    # Bitácora: la IP en «detail»; los intentos bloqueados no cuentan como fallos nuevos
    log = client.get("/api/admin/bitacora", headers=auth).json()
    fallos = [e for e in log if e["action"] == "ingreso_fallido" and e["username"] == "admin"]
    bloqueados = [e for e in log if e["action"] == "ingreso_bloqueado"]
    assert len(fallos) == 5 and {e["detail"] for e in fallos} == {"203.0.113.5"}
    assert len(bloqueados) == 2 and {(e["username"], e["detail"]) for e in bloqueados} == {("admin", "203.0.113.5")}
    # Retry-After: segundos hasta que caduque el fallo más antiguo de la ventana; después se vuelve a entrar
    _mover_fallos(14)
    assert 55 <= int(a.post(INGRESO, json=BUENA).headers["retry-after"]) <= 61
    _mover_fallos(16)
    assert a.post(INGRESO, json=BUENA).status_code == 200


def test_ingreso_correcto_no_borra_los_fallos(client):
    c = _desde(client, "192.0.2.20")
    for _ in range(4):
        assert c.post(INGRESO, json=MALA).status_code == 401
    assert c.post(INGRESO, json=BUENA).status_code == 200
    assert c.post(INGRESO, json=MALA).status_code == 401  # quinto fallo de la ventana
    assert c.post(INGRESO, json=BUENA).status_code == 429


def test_bloqueo_por_ip_frena_el_rociado_de_usuarios(client):
    c, otra = _desde(client, "192.0.2.30"), _desde(client, "192.0.2.31")
    for i in range(20):
        assert c.post(INGRESO, json={"username": f"usuario{i}", "password": "x"}).status_code == 401
    r = c.post(INGRESO, json=BUENA)
    assert r.status_code == 429 and r.json() == BLOQUEO and int(r.headers["retry-after"]) > 0
    assert otra.post(INGRESO, json=BUENA).status_code == 200
