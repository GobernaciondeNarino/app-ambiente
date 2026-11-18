"""Servicio de compartir proyectos de GeoLibre (contrato HTTP v1 de GeoLibre, ``docs/server-api.md``).

El geoportal lo aloja en su mismo origen. Base para ``sharing.shareUrl``: ``<URL pública>/api/compartir``;
GeoLibre llama a ``${base}/api/...`` y lee ``${base}/{usuario}/{slug}.geolibre.json``.

Autenticación: ``Authorization: Bearer gpc_…``, tokens personales que cada usuario emite en el administrador
(``/api/admin/compartir/tokens``; se guarda solo su SHA-256). Los tokens de sesión del administrador no sirven
aquí. Errores: ``{"error": "…", "detail": "…"}``. Misma lógica que ``portal/api/lib/compartir.php``.
"""

from __future__ import annotations

import hashlib
import hmac
import itertools
import math
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import delete, false, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings, request_settings
from ..db import get_session
from ..errores import CUERPO_NO_JSON, CUERPO_NO_OBJETO
from ..models import AuditLog, SharedProject, SharedProjectVersion, ShareToken, User
from ..schemas import (
    ErrorCompartir,
    error_tamano,
    iso_utc,
    json_estricto,
    param_booleano,
    param_entero,
    proyecto_compartido_salida,
    proyecto_geolibre,
    titulo_de_archivo,
    token_compartir_salida,
    url_proyecto_compartido,
    utc,
)
from ..security import current_user
from ..services.layers import ID_MAXIMO, audit, slugify

PREFIJO_TOKEN = "gpc_"
MAX_TOKENS_ACTIVOS = 20
ALCANCES = ["read:projects", "write:projects", "share:public"]
ACCIONES_CUPO = ("compartir_publicacion", "compartir_actualizacion")
# Rutas opcionales del contrato que este servicio no ofrece: GeoLibre trata su 404 como «no disponible»
OPCIONALES = re.compile(r"^(shares|organizations|groups|transfers)(/|$)")
RUTAS_API = re.compile(
    r"^(users/me|users/[^/]+/projects|projects(/[^/]+(/content|/versions(/[^/]+)?)?)?|collections/browse|collections/[^/]+/[^/]+)$"
)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TOKEN_RE = re.compile(r"^gpc_[0-9a-f]{48}$")
ETAG_RE = re.compile(r'(?:W/)?("[^"]*")')
METODOS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
LECTURA = ["GET", "HEAD"]
SIN_CACHE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}

router = APIRouter(prefix="/api/compartir", tags=["compartir"])
router_admin = APIRouter(prefix="/api/admin/compartir", tags=["administración"])


def _lectura(ruta: str):
    """GET que también atiende HEAD (como la edición PHP), sin duplicar la operación en OpenAPI."""

    def decorar(fn):
        router.add_api_route(ruta, fn, methods=["HEAD"], include_in_schema=False)
        return router.get(ruta)(fn)

    return decorar


def instalar(app: FastAPI) -> None:
    """Respuestas de error del servicio con «error» (contrato de GeoLibre) y «detail» (resto de la API)."""

    @app.exception_handler(ErrorCompartir)
    async def _error(_request: Request, exc: ErrorCompartir) -> JSONResponse:
        cabeceras = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", **exc.cabeceras}
        return JSONResponse({"error": exc.mensaje, "detail": exc.mensaje}, status_code=exc.estado, headers=cabeceras)


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _json(datos: dict, estado: int = 200) -> JSONResponse:
    return JSONResponse(datos, status_code=estado, headers=SIN_CACHE)


def _limite(s: Settings) -> int:
    return min(max(1, s.share_max_mb), s.max_upload_mb) * 1024 * 1024


# ---------------------------------------------------------------- tokens personales


def _token_no_valido(falta: bool = False) -> ErrorCompartir:
    """401 con el desafío del contrato: «Bearer» si falta el token; «Bearer error="invalid_token"» si no vale."""
    if falta:
        return ErrorCompartir(401, "Se requiere un token personal del geoportal (Authorization: Bearer gpc_…).", {"WWW-Authenticate": "Bearer"})
    return ErrorCompartir(401, "Token personal no válido, vencido o revocado.", {"WWW-Authenticate": 'Bearer error="invalid_token"'})


def _usuario(request: Request, session: Session, obligatorio: bool = False) -> User | None:
    """Dueño del token personal; None sin Authorization (401 si es obligatorio). Un token presentado y no válido siempre es 401."""
    cabecera = request.headers.get("authorization", "").strip()
    if not cabecera:
        if obligatorio:
            raise _token_no_valido(True)
        return None
    m = re.fullmatch(r"Bearer\s+(\S+)", cabecera, re.I)
    # Los tokens de sesión (JWT) del administrador no tienen esta forma: no sirven aquí
    if not m or not TOKEN_RE.match(m.group(1)):
        raise _token_no_valido()
    resumen = hashlib.sha256(m.group(1).encode()).hexdigest()
    ahora = _ahora()
    candidatos = session.scalars(select(ShareToken).where(ShareToken.prefix == m.group(1)[:12], ShareToken.revoked_at.is_(None)))
    for t in candidatos.all():
        if not hmac.compare_digest(t.token_hash, resumen):
            continue
        if not t.user.active or (t.expires_at is not None and utc(t.expires_at) <= ahora):
            break
        if t.last_used_at is None or utc(t.last_used_at) < ahora - timedelta(seconds=60):
            t.last_used_at = ahora
            session.commit()
        return t.user
    raise _token_no_valido()


@router_admin.get("/tokens")
def listar_tokens(request: Request, yo: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    """Tokens activos del usuario; con ``?todos=true`` (solo administradores), los de todos."""
    todos = param_booleano("todos", request.query_params.get("todos"), HTTPException)
    if todos and yo.role != "administrador":
        raise HTTPException(403, "Se requiere el rol de administrador.")
    consulta = select(ShareToken).where(ShareToken.revoked_at.is_(None))
    if not todos:
        consulta = consulta.where(ShareToken.user_id == yo.id)
    filas = session.scalars(consulta.order_by(ShareToken.created_at.desc(), ShareToken.id.desc())).all()
    base = request_settings(request).public_base_url + "/api/compartir"
    return {"share_url": base, "tokens": [token_compartir_salida(t, _ahora()) for t in filas]}


@router_admin.post("/tokens", status_code=201)
async def crear_token(request: Request, yo: User = Depends(current_user), session: Session = Depends(get_session)) -> JSONResponse:
    """Emite un token. El token completo se devuelve solo en esta respuesta: no se guarda en ninguna parte."""
    try:
        d = json_estricto(await request.body())
    except ValueError:
        raise HTTPException(422, CUERPO_NO_JSON) from None
    if not isinstance(d, dict):
        raise HTTPException(422, CUERPO_NO_OBJETO if isinstance(d, list) else CUERPO_NO_JSON)
    nombre = d["name"].strip() if isinstance(d.get("name"), str) else ""
    if not nombre or len(nombre) > 100:
        raise HTTPException(422, "name: indique un nombre para el token (de 1 a 100 caracteres).")
    dias = d.get("expires_in_days")
    if dias is not None and (not isinstance(dias, int) or isinstance(dias, bool) or not 1 <= dias <= 365):
        raise HTTPException(422, "expires_in_days: debe ser un número entero entre 1 y 365, o null.")
    ahora = _ahora()
    vigente = or_(ShareToken.expires_at.is_(None), ShareToken.expires_at > ahora)
    activos = session.scalar(
        select(func.count()).select_from(ShareToken).where(ShareToken.user_id == yo.id, ShareToken.revoked_at.is_(None), vigente)
    )
    if (activos or 0) >= MAX_TOKENS_ACTIVOS:
        raise HTTPException(409, f"Ya tiene {MAX_TOKENS_ACTIVOS} tokens activos. Revoque alguno antes de crear otro.")
    token = PREFIJO_TOKEN + secrets.token_hex(24)
    t = ShareToken(
        user_id=yo.id, name=nombre, prefix=token[:12], token_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_at=ahora, expires_at=ahora + timedelta(days=dias) if dias is not None else None,
    )
    session.add(t)
    audit(session, yo.username, "compartir_token_emitido", t.prefix, nombre)
    session.commit()
    base = request_settings(request).public_base_url + "/api/compartir"
    salida = {"token": token, "share_url": base, **token_compartir_salida(t, ahora)}
    return JSONResponse(salida, status_code=201, headers={"Cache-Control": "no-store"})


@router_admin.delete("/tokens/{token_id}", status_code=204)
def revocar_token(token_id: str, yo: User = Depends(current_user), session: Session = Depends(get_session)) -> Response:
    t = session.get(ShareToken, int(token_id)) if re.fullmatch(r"\d{1,10}", token_id) and int(token_id) <= ID_MAXIMO else None
    if t is None or (t.user_id != yo.id and yo.role != "administrador"):
        raise HTTPException(404, "Token no encontrado.")
    if t.revoked_at is None:
        t.revoked_at = _ahora()
        de = f" · de {t.user.username}" if t.user.username != yo.username else ""
        audit(session, yo.username, "compartir_token_revocado", t.prefix, t.name + de)
        session.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- proyectos


def _visible(p: SharedProject, yo: User | None) -> bool:
    """Un proyecto privado solo lo ve su dueño; públicos y no listados, cualquiera que tenga la dirección."""
    return p.visibility != "private" or (yo is not None and yo.id == p.user_id)


def _proyecto(session: Session, ident: str, yo: User | None, admin_ve_todo: bool = False) -> SharedProject:
    """Proyecto visible para quien pregunta; 404 si no existe o no puede verlo (el contrato no los distingue)."""
    p = session.get(SharedProject, ident) if UUID_RE.match(ident) else None
    if p is None or not (_visible(p, yo) or admin_ve_todo):
        raise ErrorCompartir(404, "Proyecto no encontrado.")
    return p


def _por_ruta(session: Session, usuario: str, slug: str, yo: User | None) -> SharedProject:
    consulta = select(SharedProject).join(User, User.id == SharedProject.user_id)
    p = session.scalar(consulta.where(User.username == usuario, SharedProject.slug == slug))
    if p is None or not _visible(p, yo):
        raise ErrorCompartir(404, "Proyecto no encontrado.")
    return p


def _salida(request: Request, p: SharedProject, yo: User | None) -> dict:
    return proyecto_compartido_salida(p, request_settings(request).public_base_url, yo.id if yo is not None else None)


def _pagina_proyectos(request: Request, session: Session, condiciones: list, yo: User | None) -> JSONResponse:
    lim = param_entero("limit", request.query_params.get("limit", ""), 24, 1, 100)
    off = param_entero("offset", request.query_params.get("offset", ""), 0, 0, 1_000_000_000)
    consulta = select(SharedProject).join(User, User.id == SharedProject.user_id).where(*condiciones)
    total = session.scalar(select(func.count()).select_from(consulta.subquery()))
    filas = session.scalars(consulta.order_by(SharedProject.updated_at.desc(), SharedProject.id.desc()).offset(off).limit(lim)).all()
    return _json({"projects": [_salida(request, p, yo) for p in filas], "limit": lim, "offset": off, "total": total})


@_lectura("/api/users/me")
def yo_mismo(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    yo = _usuario(request, session, True)
    usuario = {"id": str(yo.id), "username": yo.username, "email": (yo.email or "").strip() or None, "createdAt": iso_utc(yo.created_at)}
    return _json({"user": usuario, "sessionId": None, "scopes": ALCANCES})


@_lectura("/api/users/{usuario}/projects")
def proyectos_de(usuario: str, request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    """El dueño (con su token) ve todos sus proyectos; los demás, solo los públicos. Usuario inexistente: lista vacía."""
    yo = _usuario(request, session)
    condiciones = [User.username == usuario]
    if yo is None or yo.username != usuario:
        condiciones.append(SharedProject.visibility == "public")
    return _pagina_proyectos(request, session, condiciones, yo)


@_lectura("/api/projects")
def listar(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    yo = _usuario(request, session)
    destacados, mios, conmigo = (param_booleano(n, request.query_params.get(n)) for n in ("featured", "mine", "shared_with_me"))
    origen = request.query_params.get("shared_source", "")
    if len(origen) > 2000:
        raise ErrorCompartir(422, "shared_source: admite como máximo 2000 caracteres.")
    origen = origen.strip()
    if mios and conmigo:
        raise ErrorCompartir(422, "mine y shared_with_me no se pueden combinar.")
    if origen and not conmigo:
        raise ErrorCompartir(422, "shared_source requiere shared_with_me=true.")
    if origen and origen not in ("organizations", "groups"):
        raise ErrorCompartir(422, "shared_source: use organizations o groups.")
    if (mios or conmigo) and yo is None:
        raise _token_no_valido(True)
    # Lo autenticado solo amplía con «mine»; sin organizaciones ni grupos, «compartidos conmigo» está vacío
    if conmigo:
        condiciones = [false()]
    else:
        condiciones = [SharedProject.user_id == yo.id] if mios else [SharedProject.visibility == "public"]
    if destacados:
        condiciones += [SharedProject.visibility == "public", User.role == "administrador"]
    return _pagina_proyectos(request, session, condiciones, yo)


# ---------------------------------------------------------------- escritura


async def _cuerpo(request: Request, limite: int) -> dict:
    """Cuerpo JSON (objeto) de POST/PUT; 413 antes de leerlo si declara más de lo admisible."""
    maximo = 2 * limite + 1048576  # el proyecto viaja escapado en una cadena JSON: el cuerpo es mayor
    largo = request.headers.get("content-length", "")
    if largo.isdigit() and int(largo) > maximo:
        raise error_tamano(limite)
    crudo = await request.body()
    if len(crudo) > maximo:
        raise error_tamano(limite)
    try:
        d = json_estricto(crudo)
    except ValueError:
        raise ErrorCompartir(422, CUERPO_NO_JSON) from None
    if not isinstance(d, dict):
        raise ErrorCompartir(422, CUERPO_NO_OBJETO if isinstance(d, list) else CUERPO_NO_JSON)
    return d


def _exigir_cupo(session: Session, s: Settings, yo: User) -> None:
    """Límite simple: publicaciones y versiones nuevas por usuario en la última hora (GEOPORTAL_COMPARTIR_MAX_HORA)."""
    maximo = max(1, s.share_max_per_hour)
    recientes = AuditLog.at >= _ahora() - timedelta(hours=1)
    consulta = select(AuditLog.at).where(AuditLog.username == yo.username, AuditLog.action.in_(ACCIONES_CUPO), recientes)
    fechas = session.scalars(consulta.order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(maximo)).all()
    if len(fechas) < maximo:
        return
    espera = max(1, math.ceil((utc(fechas[-1]) + timedelta(hours=1) - _ahora()).total_seconds()))
    mensaje = f"Demasiadas publicaciones en la última hora (máximo {maximo} por usuario). Espere unos minutos e inténtelo de nuevo."
    raise ErrorCompartir(429, mensaje, {"Retry-After": str(espera)})


def _slug_unico(session: Session, usuario_id: int, titulo: str) -> str:
    """Slug de 1 a 100 caracteres [a-z0-9-], único entre los proyectos del usuario."""
    # slugify() devuelve «capa» si no queda nada: con «x » delante, lo vacío se distingue de un título real
    base = slugify("x " + titulo, 102)[2:] or "proyecto"
    for n in itertools.count(1):
        sufijo = "" if n == 1 else f"-{n}"
        slug = base[: 100 - len(sufijo)].rstrip("-") + sufijo
        if session.scalar(select(SharedProject.id).where(SharedProject.user_id == usuario_id, SharedProject.slug == slug)) is None:
            return slug
    raise AssertionError  # pragma: no cover


@router.post("/api/projects")
async def crear(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    s = request_settings(request)
    yo = _usuario(request, session, True)
    _exigir_cupo(session, s, yo)
    d = await _cuerpo(request, _limite(s))
    titulo_archivo = titulo_de_archivo(d.get("filename"))
    visibilidad = "private" if d.get("visibility") is None else d["visibility"]
    if visibilidad == "organization":
        raise ErrorCompartir(422, "visibility: «organization» no está disponible (este servidor no tiene organizaciones).")
    if not isinstance(visibilidad, str) or visibilidad not in ("public", "unlisted", "private"):
        raise ErrorCompartir(422, "visibility: use public, unlisted o private.")
    if d.get("organizationId") not in (None, ""):
        raise ErrorCompartir(422, "organizationId: este servidor no tiene organizaciones.")
    if d.get("groupIds") not in (None, []):
        raise ErrorCompartir(422, "groupIds: este servidor no tiene grupos.")
    contenido = d.get("content")
    titulo = proyecto_geolibre(contenido, _limite(s)) or titulo_archivo or "Proyecto sin título"
    if len(titulo) > 100:
        raise ErrorCompartir(422, "El título del proyecto admite como máximo 100 caracteres.")
    ident = str(uuid.uuid4())
    for intento in range(1, 6):
        slug = _slug_unico(session, yo.id, titulo)
        ahora = _ahora()
        session.add(SharedProject(id=ident, user_id=yo.id, slug=slug, title=titulo, description="", visibility=visibilidad,
                                  views=0, last_version=1, created_at=ahora, updated_at=ahora))
        try:
            session.flush()
            break
        except IntegrityError:  # otro envío simultáneo tomó el mismo slug
            session.rollback()
            if intento == 5:
                raise
    session.add(SharedProjectVersion(project_id=ident, number=1, content=contenido, size=len(contenido.encode()), created_at=ahora))
    audit(session, yo.username, "compartir_publicacion", f"{yo.username}/{slug}", visibilidad)
    session.commit()
    return _json({"project": _salida(request, session.get(SharedProject, ident), yo)}, 201)


@router.put("/api/projects/{ident}/content")
async def actualizar(ident: str, request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    """Versión nueva. Como el contrato v1: si «expectedVersion» no es la vigente se guarda igual, con «warning» («version conflict»)."""
    s = request_settings(request)
    yo = _usuario(request, session, True)
    p = _proyecto(session, ident, yo)
    if p.user_id != yo.id:
        raise ErrorCompartir(403, "Solo el dueño del proyecto puede guardar versiones nuevas.")
    _exigir_cupo(session, s, yo)
    d = await _cuerpo(request, _limite(s))
    esperada = d.get("expectedVersion")
    if esperada is not None and (not isinstance(esperada, int) or isinstance(esperada, bool) or esperada < 1):
        raise ErrorCompartir(422, "expectedVersion: debe ser un número entero positivo.")
    contenido = d.get("content")
    proyecto_geolibre(contenido, _limite(s))
    bloqueo = select(SharedProject).where(SharedProject.id == p.id).with_for_update()
    p = session.scalar(bloqueo.execution_options(populate_existing=True))
    vigente = p.last_version
    numero, ahora = vigente + 1, _ahora()
    session.add(SharedProjectVersion(project_id=p.id, number=numero, content=contenido, size=len(contenido.encode()), created_at=ahora))
    p.last_version, p.updated_at = numero, ahora
    try:
        session.flush()
    except IntegrityError:  # SQLite no bloquea la fila: otro guardado simultáneo tomó el número
        session.rollback()
        raise ErrorCompartir(409, "Otro guardado simultáneo tomó el número de versión. Inténtelo de nuevo.") from None
    # Se conservan las últimas GEOPORTAL_COMPARTIR_MAX_VERSIONES (20); «versionCount» sigue siendo el número de la vigente
    viejas = SharedProjectVersion.number <= numero - max(1, s.share_max_versions)
    session.execute(delete(SharedProjectVersion).where(SharedProjectVersion.project_id == p.id, viejas))
    audit(session, yo.username, "compartir_actualizacion", f"{p.user.username}/{p.slug}", f"versión {numero}")
    session.commit()
    salida = {"project": _salida(request, p, yo), "version": numero}
    if esperada is not None and esperada != vigente:
        salida["warning"] = f"version conflict: se esperaba la versión {esperada}, pero la vigente era la {vigente}; se guardó como versión {numero}."
    return _json(salida, 201)


@router.delete("/api/projects/{ident}")
def eliminar(ident: str, request: Request, session: Session = Depends(get_session)) -> Response:
    yo = _usuario(request, session, True)
    admin = yo.role == "administrador"
    p = _proyecto(session, ident, yo, admin_ve_todo=admin)
    propio = p.user_id == yo.id
    if not propio and not admin:
        raise ErrorCompartir(403, "Solo el dueño del proyecto o un administrador pueden eliminarlo.")
    destino = f"{p.user.username}/{p.slug}"
    session.execute(delete(SharedProjectVersion).where(SharedProjectVersion.project_id == p.id))
    session.delete(p)
    audit(session, yo.username, "compartir_eliminacion", destino, "" if propio else "por un administrador")
    session.commit()
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- lectura


def _enviar_version(request: Request, session: Session, p: SharedProject, numero: int, contar_vista: bool) -> Response:
    """Documento de una versión: públicos y no listados con «public, no-cache» y ETag fuerte (304); privados, «private, no-store»."""
    clave = (SharedProjectVersion.project_id == p.id, SharedProjectVersion.number == numero)
    if session.scalar(select(SharedProjectVersion.size).where(*clave)) is None:
        raise ErrorCompartir(404, "Versión no encontrada.")
    publico = p.visibility != "private"
    cabeceras = {"Cache-Control": "public, no-cache", "ETag": f'"{p.id}-v{numero}"'} if publico else {"Cache-Control": "private, no-store"}
    si_no = request.headers.get("if-none-match", "").strip()
    if publico and (si_no == "*" or cabeceras["ETag"] in ETAG_RE.findall(si_no)):
        return Response(status_code=304, headers=cabeceras)
    contenido = session.scalar(select(SharedProjectVersion.content).where(*clave))
    if contar_vista:
        session.execute(update(SharedProject).where(SharedProject.id == p.id).values(views=SharedProject.views + 1))
        session.commit()
    return Response(content=contenido, media_type="application/json", headers={**cabeceras, "X-Content-Type-Options": "nosniff"})


@_lectura("/api/projects/{ident}")
def obtener(ident: str, request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    yo = _usuario(request, session)
    return _json({"project": _salida(request, _proyecto(session, ident, yo), yo)})


@_lectura("/api/projects/{ident}/versions")
def versiones(ident: str, request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    p = _proyecto(session, ident, _usuario(request, session, True))
    consulta = select(SharedProjectVersion.number, SharedProjectVersion.created_at).where(SharedProjectVersion.project_id == p.id)
    url = f"{request_settings(request).public_base_url}/api/compartir/api/projects/{p.id}/versions/"
    filas = session.execute(consulta.order_by(SharedProjectVersion.number.desc())).all()
    return _json({"versions": [{"number": n, "createdAt": iso_utc(c), "url": f"{url}{n}"} for n, c in filas]})


@_lectura("/api/projects/{ident}/versions/{numero}")
def version(ident: str, numero: str, request: Request, session: Session = Depends(get_session)) -> Response:
    p = _proyecto(session, ident, _usuario(request, session))
    if not re.fullmatch(r"[1-9]\d{0,8}", numero):
        raise ErrorCompartir(404, "Versión no encontrada.")
    return _enviar_version(request, session, p, int(numero), False)


@_lectura("/{usuario}/{slug}.geolibre.json")
def ultimo(usuario: str, slug: str, request: Request, session: Session = Depends(get_session)) -> Response:
    p = _por_ruta(session, usuario, slug, _usuario(request, session))
    return _enviar_version(request, session, p, p.last_version, request.method == "GET")


@router.api_route("/api/{resto:path}", methods=METODOS, include_in_schema=False)
def api_restante(resto: str, request: Request) -> Response:
    """Colecciones (3.9: vacías), rutas opcionales del contrato (404), métodos no previstos (405) y desconocidas (404)."""
    lectura = request.method in LECTURA
    if resto == "collections/browse" and lectura:
        return _json({"collections": []})
    if re.fullmatch(r"collections/[^/]+/[^/]+", resto) and lectura:
        raise ErrorCompartir(404, "Colección no encontrada.")
    if OPCIONALES.match(resto):
        raise ErrorCompartir(404, "Esta función de GeoLibre no está disponible en el servicio de compartir del geoportal.")
    if RUTAS_API.match(resto):
        raise ErrorCompartir(405, "Método no permitido.")
    raise ErrorCompartir(404, "Recurso no encontrado.")


@_lectura("/settings")
def ajustes_cuenta(request: Request) -> Response:
    """«Obtener token de API» de GeoLibre abre ${shareUrl}/settings: los tokens se emiten en «Mi cuenta» del administrador."""
    destino = f"{request_settings(request).public_base_url}/admin/#cuenta"
    return Response(status_code=302, headers={"Location": destino, "Cache-Control": "no-store"})


@_lectura("/{usuario}/{slug}")
def pagina(usuario: str, slug: str, request: Request, session: Session = Depends(get_session)) -> Response:
    p = _por_ruta(session, usuario, slug, _usuario(request, session))
    destino = url_proyecto_compartido(request_settings(request).public_base_url, usuario, slug)
    return Response(status_code=302, headers={"Location": destino, "Cache-Control": "private, no-store" if p.visibility == "private" else "no-cache"})


@router.api_route("", methods=METODOS, include_in_schema=False)
@router.api_route("/{resto:path}", methods=METODOS, include_in_schema=False)
def restante(request: Request) -> Response:
    """Lectura del proyecto o su página con otro método (405); cualquier otra ruta, 404."""
    resto = request.path_params.get("resto", "")
    if resto == "settings" or resto.startswith("settings/"):  # como la edición PHP
        if request.method in LECTURA:
            return ajustes_cuenta(request)
        raise ErrorCompartir(405, "Método no permitido.")
    if re.fullmatch(r"[^/]+/[^/]+", resto) and request.method not in LECTURA:
        raise ErrorCompartir(405, "Método no permitido.")
    raise ErrorCompartir(404, "Recurso no encontrado.")
