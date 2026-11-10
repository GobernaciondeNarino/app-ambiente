"""API del administrador: autenticación, carga y gestión de geodatos.

Roles:

* **editor** — carga geodatos, edita metadatos y simbología.
* **administrador** — además publica/retira capas, elimina, gestiona
  categorías y usuarios, y consulta la bitácora.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import get_session
from ..models import AuditLog, Category, Layer, User
from ..schemas import (
    AuditOut,
    CategoryIn,
    CategoryOut,
    LayerMetaIn,
    LayerOut,
    LoginIn,
    PasswordChange,
    TokenOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from ..security import (
    create_token,
    current_user,
    hash_password,
    require_admin,
    validate_password_strength,
    verify_password,
)
from ..services.ingest import ACCEPTED_EXTENSIONS, IngestError, IngestOptions, ingest_file, read_geojson_head, render_raster_preview
from ..services.layers import (
    audit,
    category_out,
    get_layer_or_404,
    layer_dirs,
    layer_out,
    remove_layer_files,
    safe_filename,
    save_upload,
    unique_slug,
)

auth_router = APIRouter(prefix="/api/auth", tags=["autenticación"])
router = APIRouter(prefix="/api/admin", tags=["administración"])

DEFAULT_VECTOR_STYLE = {
    "fillColor": "#10A13B",
    "strokeColor": "#0B6E28",
    "strokeWidth": 1.5,
    "fillOpacity": 0.5,
    "circleRadius": 6,
}
DEFAULT_RASTER_STYLE = {"colorRamp": "terreno"}

# Paleta derivada de los colores institucionales para asignar colores por defecto
PALETTE = ["#10A13B", "#0E7FC0", "#F2A900", "#2E7D32", "#00897B", "#6D8B1E", "#8D6E63", "#1565C0"]


# --------------------------------------------------------------------------
# Autenticación
# --------------------------------------------------------------------------


@auth_router.post("/ingresar", response_model=TokenOut)
def login(data: LoginIn, session: Session = Depends(get_session)) -> TokenOut:
    user = session.scalar(select(User).where(User.username == data.username.strip()))
    if user is None or not user.active or not verify_password(data.password, user.password_hash):
        audit(session, data.username[:80], "ingreso_fallido")
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos.")
    user.last_login = datetime.now(timezone.utc)
    audit(session, user.username, "ingreso")
    session.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@auth_router.get("/yo", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@auth_router.post("/cambiar-clave")
def change_password(
    data: PasswordChange, user: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta.")
    validate_password_strength(data.new_password)
    user.password_hash = hash_password(data.new_password)
    audit(session, user.username, "cambio_clave", user.username)
    session.commit()
    return {"mensaje": "Contraseña actualizada."}


# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------


@router.get("/resumen")
def summary(user: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    total = session.scalar(select(func.count(Layer.id))) or 0
    published = session.scalar(select(func.count(Layer.id)).where(Layer.published.is_(True))) or 0
    vectors = session.scalar(select(func.count(Layer.id)).where(Layer.kind == "vector")) or 0
    size = session.scalar(select(func.coalesce(func.sum(Layer.file_size), 0))) or 0
    cats = session.scalar(select(func.count(Category.id))) or 0
    recent = session.scalars(select(AuditLog).order_by(AuditLog.at.desc()).limit(8)).all()
    return {
        "capas": total,
        "publicadas": published,
        "borradores": total - published,
        "vectoriales": vectors,
        "raster": total - vectors,
        "categorias": cats,
        "almacenamiento_bytes": int(size),
        "actividad": [AuditOut.model_validate(a).model_dump(mode="json") for a in recent],
        "formatos": sorted(ACCEPTED_EXTENSIONS),
    }


# --------------------------------------------------------------------------
# Capas
# --------------------------------------------------------------------------


def _load_layer(session: Session, layer_id: int) -> Layer:
    layer = session.scalar(select(Layer).options(selectinload(Layer.category)).where(Layer.id == layer_id))
    if layer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capa no encontrada.")
    return layer


def _parse_meta(raw: str | None) -> LayerMetaIn:
    if not raw:
        return LayerMetaIn()
    try:
        return LayerMetaIn.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(422, f"Metadatos no válidos: {exc}") from exc


def _apply_meta(layer: Layer, meta: LayerMetaIn, session: Session, user: User) -> list[str]:
    changed: list[str] = []
    data = meta.model_dump(exclude_unset=True)
    if "published" in data and user.role != "administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo un administrador puede publicar o retirar capas.")
    if "category_id" in data and data["category_id"] is not None and session.get(Category, data["category_id"]) is None:
        raise HTTPException(422, "La categoría indicada no existe.")
    if "style" in data and data["style"] is not None:
        data["style"] = {**(layer.style or {}), **data["style"]}
    if "popup_fields" in data and data["popup_fields"] is not None:
        valid = {a["name"] for a in (layer.attributes or [])}
        data["popup_fields"] = [f for f in data["popup_fields"] if not valid or f in valid][:40]
    nullable = {"category_id"}
    for key, value in data.items():
        if value is None and key not in nullable:
            continue  # campo enviado vacío: se conserva el valor actual
        if getattr(layer, key) != value:
            setattr(layer, key, value)
            changed.append(key)
    layer.updated_by = user.username
    return changed


def _apply_ingest(layer: Layer, result, original: Path, original_name: str, size: int) -> None:
    layer.kind = result.kind
    layer.source_format = result.source_format
    layer.original_filename = original_name
    layer.original_path = str(original)
    layer.processed_path = str(result.processed_path)
    layer.preview_path = str(result.preview_path or "")
    layer.file_size = size
    layer.geometry_type = result.geometry_type
    layer.feature_count = result.feature_count
    layer.bbox = result.bbox
    layer.source_crs = result.source_crs
    layer.attributes = result.attributes
    layer.raster_info = result.raster_info


async def _run_ingest(settings: Settings, layer: Layer, upload: UploadFile, opts: IngestOptions):
    filename = safe_filename(upload.filename or "archivo")
    ext = Path(filename).suffix.lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            422,
            f"Formato «{ext or 'desconocido'}» no admitido. Formatos válidos: " + ", ".join(sorted(ACCEPTED_EXTENSIONS)),
        )
    originals, processed = layer_dirs(settings, layer.id)
    staging_orig = settings.tmp_dir / f"{layer.id}-{datetime.now().timestamp():.0f}"
    staging_out = staging_orig.with_name(staging_orig.name + "-out")
    staged_file = staging_orig / filename
    try:
        size = await save_upload(upload, staged_file, settings.max_upload_mb * 1024**2)
        try:
            result = await run_in_threadpool(ingest_file, staged_file, staging_out, opts)
        except IngestError as exc:
            raise HTTPException(422, str(exc)) from exc
        # Reemplazo atómico de los archivos de la capa
        shutil.rmtree(originals, ignore_errors=True)
        shutil.rmtree(processed, ignore_errors=True)
        originals.parent.mkdir(parents=True, exist_ok=True)
        processed.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_orig), originals)
        shutil.move(str(staging_out), processed)
        result.processed_path = processed / result.processed_path.name
        if result.preview_path:
            result.preview_path = processed / result.preview_path.name
        _apply_ingest(layer, result, originals / filename, upload.filename or filename, size)
        return result
    finally:
        shutil.rmtree(staging_orig, ignore_errors=True)
        shutil.rmtree(staging_out, ignore_errors=True)


@router.get("/capas", response_model=list[LayerOut])
def admin_list_layers(
    q: str | None = Query(default=None, max_length=120),
    estado: str | None = Query(default=None, pattern="^(publicadas|borradores)$"),
    categoria_id: int | None = None,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[LayerOut]:
    query = select(Layer).options(selectinload(Layer.category))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Layer.title.ilike(like), Layer.description.ilike(like), Layer.original_filename.ilike(like)))
    if estado == "publicadas":
        query = query.where(Layer.published.is_(True))
    elif estado == "borradores":
        query = query.where(Layer.published.is_(False))
    if categoria_id:
        query = query.where(Layer.category_id == categoria_id)
    layers = session.scalars(query.order_by(Layer.updated_at.desc())).all()
    return [layer_out(layer, settings) for layer in layers]


@router.get("/capas/{layer_id}", response_model=LayerOut)
def admin_get_layer(
    layer_id: int,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LayerOut:
    return layer_out(_load_layer(session, layer_id), settings)


@router.post("/capas", status_code=status.HTTP_201_CREATED)
async def admin_create_layer(
    archivo: UploadFile = File(..., description="Geodato a cargar"),
    metadatos: str | None = Form(default=None, description="JSON con los metadatos (LayerMetaIn)"),
    epsg: int | None = Form(default=None, description="EPSG de origen si el archivo no lo declara"),
    capa_interna: str | None = Form(default=None),
    columna_lon: str | None = Form(default=None),
    columna_lat: str | None = Form(default=None),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    meta = _parse_meta(metadatos)
    if user.role != "administrador" and "published" in meta.model_fields_set:
        # Un editor carga siempre como borrador; la publicación la hace un administrador
        meta = LayerMetaIn.model_validate(meta.model_dump(exclude_unset=True, exclude={"published"}))
    title = meta.title or Path(archivo.filename or "Capa").stem.replace("_", " ").strip().capitalize()
    count = session.scalar(select(func.count(Layer.id))) or 0
    layer = Layer(
        title=title,
        slug=unique_slug(session, Layer, title),
        created_by=user.username,
        updated_by=user.username,
        style={},
        position=int(count),
    )
    session.add(layer)
    session.flush()  # obtiene el id para las carpetas

    opts = IngestOptions(
        source_epsg=epsg,
        layer_name=capa_interna or None,
        csv_lon=columna_lon or None,
        csv_lat=columna_lat or None,
        coordinate_precision=settings.coordinate_precision,
    )
    try:
        result = await _run_ingest(settings, layer, archivo, opts)
    except Exception:
        session.rollback()
        remove_layer_files(settings, layer.id)
        raise

    base_style = DEFAULT_RASTER_STYLE if layer.kind == "raster" else {**DEFAULT_VECTOR_STYLE, "fillColor": PALETTE[count % len(PALETTE)]}
    layer.style = dict(base_style)
    if layer.kind == "vector" and layer.attributes:
        # Por defecto: etiqueta con el primer campo de texto que parezca un nombre
        names = [a["name"] for a in layer.attributes]
        label = next((n for n in names if n.lower() in {"nombre", "name", "nombre_geo", "nom", "nombre_1"}), "")
        layer.label_field = label
        layer.popup_fields = names[:12]
    _apply_meta(layer, meta, session, user)
    if meta.style and layer.kind == "raster" and layer.preview_path:
        await run_in_threadpool(render_raster_preview, Path(layer.processed_path), Path(layer.preview_path), layer.raster_info or {}, layer.style)
    audit(session, user.username, "carga", layer.slug, f"{layer.source_format} · {layer.feature_count} entidades")
    session.commit()
    layer = _load_layer(session, layer.id)
    return {"capa": layer_out(layer, settings).model_dump(mode="json"), "advertencias": result.warnings, "capas_internas": result.sublayers}


@router.put("/capas/{layer_id}", response_model=LayerOut)
async def admin_update_layer(
    layer_id: int,
    meta: LayerMetaIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LayerOut:
    layer = _load_layer(session, layer_id)
    changed = _apply_meta(layer, meta, session, user)
    if "title" in changed:
        layer.slug = unique_slug(session, Layer, layer.title, exclude_id=layer.id) if not layer.published else layer.slug
    if "style" in changed and layer.kind == "raster" and layer.preview_path:
        await run_in_threadpool(render_raster_preview, Path(layer.processed_path), Path(layer.preview_path), layer.raster_info or {}, layer.style)
    if changed:
        audit(session, user.username, "edicion", layer.slug, ", ".join(changed))
    session.commit()
    return layer_out(_load_layer(session, layer_id), settings)


@router.post("/capas/{layer_id}/archivo")
async def admin_replace_file(
    layer_id: int,
    archivo: UploadFile = File(...),
    epsg: int | None = Form(default=None),
    capa_interna: str | None = Form(default=None),
    columna_lon: str | None = Form(default=None),
    columna_lat: str | None = Form(default=None),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Actualiza el geodato de una capa existente conservando sus metadatos."""
    layer = _load_layer(session, layer_id)
    previous_kind = layer.kind
    opts = IngestOptions(
        source_epsg=epsg,
        layer_name=capa_interna or None,
        csv_lon=columna_lon or None,
        csv_lat=columna_lat or None,
        coordinate_precision=settings.coordinate_precision,
    )
    result = await _run_ingest(settings, layer, archivo, opts)
    if layer.kind != previous_kind:
        layer.style = dict(DEFAULT_RASTER_STYLE if layer.kind == "raster" else DEFAULT_VECTOR_STYLE)
    names = {a["name"] for a in layer.attributes or []}
    layer.popup_fields = [f for f in layer.popup_fields or [] if f in names]
    if layer.label_field not in names:
        layer.label_field = ""
    layer.updated_by = user.username
    audit(session, user.username, "actualizacion_archivo", layer.slug, layer.original_filename)
    session.commit()
    return {"capa": layer_out(_load_layer(session, layer_id), settings).model_dump(mode="json"), "advertencias": result.warnings}


@router.post("/capas/{layer_id}/publicacion", response_model=LayerOut)
def admin_publish(
    layer_id: int,
    publicar: bool = Query(..., description="true para publicar, false para retirar"),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LayerOut:
    layer = _load_layer(session, layer_id)
    if publicar and not layer.processed_path:
        raise HTTPException(status.HTTP_409_CONFLICT, "La capa no tiene datos procesados.")
    layer.published = publicar
    layer.updated_by = user.username
    audit(session, user.username, "publicacion" if publicar else "retiro", layer.slug)
    session.commit()
    return layer_out(_load_layer(session, layer_id), settings)


@router.delete("/capas/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_layer(
    layer_id: int,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    layer = get_layer_or_404(session, layer_id)
    slug = layer.slug
    session.delete(layer)
    audit(session, user.username, "eliminacion", slug)
    session.commit()
    remove_layer_files(settings, layer_id)


@router.get("/capas/{layer_id}/muestra")
def admin_sample(
    layer_id: int,
    limite: int = Query(default=50, ge=1, le=500),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict:
    layer = get_layer_or_404(session, layer_id)
    if layer.kind != "vector" or not layer.processed_path:
        return {"type": "FeatureCollection", "features": []}
    return read_geojson_head(Path(layer.processed_path), limite)


@router.get("/capas/{layer_id}/datos")
def admin_data(layer_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)) -> FileResponse:
    """Datos procesados (también de borradores) para la vista previa del administrador."""
    layer = get_layer_or_404(session, layer_id)
    path = Path(layer.processed_path) if layer.processed_path else None
    if layer.kind == "raster":
        path = Path(layer.preview_path) if layer.preview_path else None
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sin datos procesados.")
    media = "image/png" if layer.kind == "raster" else "application/geo+json"
    return FileResponse(path, media_type=media, headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------------------
# Categorías
# --------------------------------------------------------------------------


@router.get("/categorias", response_model=list[CategoryOut])
def admin_list_categories(user: User = Depends(current_user), session: Session = Depends(get_session)) -> list[CategoryOut]:
    cats = session.scalars(select(Category).order_by(Category.position, Category.name)).all()
    return [category_out(session, c) for c in cats]


@router.post("/categorias", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def admin_create_category(
    data: CategoryIn, user: User = Depends(require_admin), session: Session = Depends(get_session)
) -> CategoryOut:
    cat = Category(**data.model_dump(), slug=unique_slug(session, Category, data.name))
    session.add(cat)
    audit(session, user.username, "categoria_creada", cat.slug)
    session.commit()
    return category_out(session, cat)


@router.put("/categorias/{cat_id}", response_model=CategoryOut)
def admin_update_category(
    cat_id: int, data: CategoryIn, user: User = Depends(require_admin), session: Session = Depends(get_session)
) -> CategoryOut:
    cat = session.get(Category, cat_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada.")
    for key, value in data.model_dump().items():
        setattr(cat, key, value)
    audit(session, user.username, "categoria_editada", cat.slug)
    session.commit()
    return category_out(session, cat)


@router.delete("/categorias/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_category(cat_id: int, user: User = Depends(require_admin), session: Session = Depends(get_session)) -> None:
    cat = session.get(Category, cat_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada.")
    in_use = session.scalar(select(func.count(Layer.id)).where(Layer.category_id == cat_id)) or 0
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"La categoría tiene {in_use} capa(s). Reasígnelas antes de eliminarla."
        )
    session.delete(cat)
    audit(session, user.username, "categoria_eliminada", cat.slug)
    session.commit()


# --------------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------------


@router.get("/usuarios", response_model=list[UserOut])
def admin_list_users(user: User = Depends(require_admin), session: Session = Depends(get_session)) -> list[User]:
    return list(session.scalars(select(User).order_by(User.username)).all())


@router.post("/usuarios", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(data: UserCreate, user: User = Depends(require_admin), session: Session = Depends(get_session)) -> User:
    if session.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese nombre.")
    validate_password_strength(data.password)
    new = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    session.add(new)
    audit(session, user.username, "usuario_creado", data.username, data.role)
    session.commit()
    return new


@router.put("/usuarios/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int, data: UserUpdate, user: User = Depends(require_admin), session: Session = Depends(get_session)
) -> User:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    changes = data.model_dump(exclude_unset=True)
    if target.id == user.id and (changes.get("active") is False or changes.get("role") == "editor"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puede desactivarse ni quitarse el rol de administrador a sí mismo.")
    if "password" in changes:
        password = changes.pop("password")
        if password:
            validate_password_strength(password)
            target.password_hash = hash_password(password)
    for key, value in changes.items():
        if value is not None:
            setattr(target, key, value)
    audit(session, user.username, "usuario_editado", target.username, ", ".join(data.model_dump(exclude_unset=True)))
    session.commit()
    return target


# --------------------------------------------------------------------------
# Bitácora
# --------------------------------------------------------------------------


@router.get("/bitacora", response_model=list[AuditOut])
def admin_audit(
    limite: int = Query(default=200, ge=1, le=2000),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).order_by(AuditLog.at.desc()).limit(limite)).all())
