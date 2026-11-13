"""Errores de la API en JSON y en español, con la forma de la edición PHP: ``{"detail": "texto"}``.

FastAPI responde por defecto los errores de validación como una lista en inglés con detalles
internos de pydantic, y los 404/405/500 del enrutador como «Not Found», «Method Not Allowed» o
texto plano. La interfaz (idéntica para las dos ediciones) muestra ``detail`` al usuario.
"""

from __future__ import annotations

import logging
import re
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("geoportal")

CUERPO_NO_JSON = "El cuerpo de la petición debe ser JSON."
CUERPO_NO_OBJETO = "El cuerpo de la petición debe ser un objeto JSON."

# Mensajes por defecto del enrutador (inglés) → español, como en la edición PHP
MENSAJES_HTTP = {
    400: "Petición no válida.",
    401: "Debe iniciar sesión.",
    403: "Acceso denegado.",
    404: "Recurso no encontrado.",
    405: "Método no permitido.",
    413: "La petición supera el tamaño permitido.",
    500: "Error interno del servidor.",
}

_ORIGENES = {"body", "query", "path", "header", "cookie", "form", "file"}


def _numero(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def _mensaje(error: dict[str, Any]) -> str:
    tipo = error.get("type", "")
    ctx = error.get("ctx") or {}
    if tipo == "missing":
        return "es obligatorio"
    if tipo == "string_too_short":
        return f"debe tener al menos {ctx.get('min_length')} caracteres"
    if tipo == "string_too_long":
        return f"admite como máximo {ctx.get('max_length')} caracteres"
    if tipo == "string_pattern_mismatch":
        return "tiene un formato no válido"
    if tipo in ("int_parsing", "int_type", "int_from_float", "int_parsing_size"):
        return "debe ser un número entero"
    if tipo in ("float_parsing", "float_type", "finite_number"):
        return "debe ser un número"
    if tipo in ("bool_parsing", "bool_type"):
        return "debe ser verdadero o falso"
    if tipo == "greater_than_equal":
        return f"debe ser mayor o igual que {_numero(ctx.get('ge'))}"
    if tipo == "less_than_equal":
        return f"debe ser menor o igual que {_numero(ctx.get('le'))}"
    if tipo == "greater_than":
        return f"debe ser mayor que {_numero(ctx.get('gt'))}"
    if tipo == "less_than":
        return f"debe ser menor que {_numero(ctx.get('lt'))}"
    if tipo == "list_type":
        return "debe ser una lista"
    if tipo in ("dict_type", "model_type", "model_attributes_type"):
        return "debe ser un objeto JSON"
    if tipo == "string_type":
        return "debe ser texto"
    if tipo == "value_error":
        # Nuestros validadores ya escriben el mensaje en español
        return str(ctx.get("error") or error.get("msg", "")).removeprefix("Value error, ").rstrip(".")
    return "valor no válido"


def texto_validacion(errores: list[dict[str, Any]] | tuple) -> str:
    """Convierte los errores de pydantic en un texto corto en español («campo: mensaje.»)."""
    partes: list[str] = []
    for e in errores:
        loc = [str(x) for x in e.get("loc", ())]
        if loc and loc[0] in _ORIGENES:
            origen, loc = loc[0], loc[1:]
        else:
            origen = ""
        if e.get("type") == "json_invalid":
            partes.append(CUERPO_NO_JSON)
            continue
        if origen == "body" and not loc:
            partes.append(CUERPO_NO_JSON if e.get("type") == "missing" else CUERPO_NO_OBJETO)
            continue
        campo = ".".join(loc)
        mensaje = _mensaje(e)
        if e.get("type") == "value_error" and re.match(r"^\w+: ", mensaje):
            partes.append(mensaje + ".")  # el validador ya nombra el campo («fillColor: color hexadecimal no válido»)
        elif campo:
            partes.append(f"{campo}: {mensaje[:1].lower() + mensaje[1:]}.")
        else:
            partes.append(mensaje[:1].upper() + mensaje[1:] + ".")
    return " · ".join(dict.fromkeys(partes)) or "Datos no válidos."


def instalar(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacion(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": texto_validacion(exc.errors())}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        try:
            frase = HTTPStatus(exc.status_code).phrase
        except ValueError:
            frase = None
        if exc.detail == frase and exc.status_code in MENSAJES_HTTP:
            exc = StarletteHTTPException(exc.status_code, MENSAJES_HTTP[exc.status_code], headers=exc.headers)
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _interno(request: Request, exc: Exception) -> JSONResponse:
        # Sin trazas ni rutas internas en la respuesta; el detalle queda en el registro del servidor
        log.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse({"detail": MENSAJES_HTTP[500]}, status_code=500)
