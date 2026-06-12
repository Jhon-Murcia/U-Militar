"""Integracion con Google Sheets para obtener respuestas de formularios."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gspread
from google.auth import default as google_auth_default
from google.oauth2.service_account import Credentials

from .config import (
    ARCHIVO_CREDENCIALES,
    FORMULARIOS_EJEMPLO,
    SCOPES,
    SPREADSHEET_NAME,
    USAR_DATOS_EJEMPLO,
    WORKSHEET_NAME,
)
from .google_credentials import cargar_service_account


logger = logging.getLogger(__name__)


def _limpiar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _normalizar_registro(registro: dict[str, Any]) -> dict[str, Any]:
    nombre = ""
    correo = ""
    fecha_respuesta = ""
    respuestas: dict[str, str] = {}

    for clave, valor in registro.items():
        clave_texto = _limpiar_texto(clave)
        valor_texto = _limpiar_texto(valor)
        clave_baja = clave_texto.lower()

        if "nombre" in clave_baja or "estudiante" in clave_baja:
            nombre = nombre or valor_texto
            continue
        if "correo" in clave_baja or "email" in clave_baja:
            correo = correo or valor_texto
            continue
        if "fecha" in clave_baja or "timestamp" in clave_baja or "marca temporal" in clave_baja:
            fecha_respuesta = fecha_respuesta or valor_texto
            continue
        if valor_texto:
            respuestas[clave_texto] = valor_texto

    nombre = nombre or "Estudiante sin nombre"
    correo = correo or f"{nombre.lower().replace(' ', '_')}@sin-correo.local"
    fecha_respuesta = fecha_respuesta or "sin fecha"

    return {
        "nombre": nombre,
        "correo": correo,
        "fecha_respuesta": fecha_respuesta,
        "respuestas": respuestas,
    }


def _normalizar_formulario(
    clave_formulario: str,
    nombre_formulario: str,
    worksheet_nombre: str,
    registros: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "clave_formulario": clave_formulario,
        "nombre": nombre_formulario,
        "worksheet_nombre": worksheet_nombre,
        "respuestas": [_normalizar_registro(registro) for registro in registros],
    }


def conectar_google() -> gspread.Client:
    credenciales_origen = cargar_service_account(
        json_env="TESTQREATOR_GOOGLE_CREDENTIALS_JSON",
        base64_env="TESTQREATOR_GOOGLE_CREDENTIALS_BASE64",
        file_env="TESTQREATOR_CREDENTIALS",
        default_path=Path(ARCHIVO_CREDENCIALES),
    )

    if isinstance(credenciales_origen, dict):
        credenciales = Credentials.from_service_account_info(credenciales_origen, scopes=SCOPES)
    elif isinstance(credenciales_origen, str):
        credenciales = Credentials.from_service_account_file(credenciales_origen, scopes=SCOPES)
    else:
        credenciales, _ = google_auth_default(scopes=SCOPES)

    return gspread.authorize(credenciales)


def obtener_formularios() -> list[dict[str, Any]]:
    """Obtiene todos los formularios accesibles desde Google Sheets o usa ejemplos."""

    try:
        cliente = conectar_google()
        formularios: list[dict[str, Any]] = []

        if SPREADSHEET_NAME:
            libros = [cliente.open(SPREADSHEET_NAME)]
        else:
            libros = cliente.openall()

        if not libros:
            raise RuntimeError("No se encontraron formularios disponibles en Google Sheets.")

        for libro in libros:
            hoja = libro.worksheet(WORKSHEET_NAME) if WORKSHEET_NAME else libro.sheet1
            registros = hoja.get_all_records()
            formularios.append(
                _normalizar_formulario(
                    clave_formulario=str(getattr(libro, "id", libro.title)),
                    nombre_formulario=libro.title,
                    worksheet_nombre=hoja.title,
                    registros=registros,
                )
            )

        return formularios
    except Exception as error:  # pragma: no cover - la ruta de fallback depende del entorno
        logger.warning("No fue posible leer Google Sheets: %s", error)
        if USAR_DATOS_EJEMPLO:
            return FORMULARIOS_EJEMPLO
        return []


def obtener_respuestas() -> list[dict[str, Any]]:
    """Compatibilidad: devuelve todas las respuestas planas de todos los formularios."""

    formularios = obtener_formularios()
    respuestas: list[dict[str, Any]] = []
    for formulario in formularios:
        for respuesta in formulario.get("respuestas", []):
            respuesta_plana = dict(respuesta)
            respuesta_plana["formulario"] = formulario.get("nombre", "Formulario")
            respuesta_plana["formulario_clave"] = formulario.get("clave_formulario", "")
            respuestas.append(respuesta_plana)
    return respuestas
