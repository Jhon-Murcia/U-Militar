"""Persistencia dual para Firestore sin reemplazar SQLite."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Mapping

from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from firebase_config import obtener_firestore


logger = logging.getLogger(__name__)


def _slugificar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto or "sin_dato"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _base_doc_id_formulario(formulario: Mapping[str, Any]) -> str:
    clave = formulario.get("clave_formulario") or formulario.get("nombre") or formulario.get("worksheet_nombre")
    return _slugificar(clave)


def _base_doc_id_estudiante(estudiante: Mapping[str, Any]) -> str:
    formulario_doc_id = estudiante.get("formulario_doc_id") or estudiante.get("formulario_clave") or "formulario"
    correo = estudiante.get("correo") or estudiante.get("email") or estudiante.get("nombre") or "estudiante"
    fecha_respuesta = estudiante.get("fecha_respuesta") or estudiante.get("timestamp") or "sin_fecha"
    return f"{_slugificar(formulario_doc_id)}__{_slugificar(correo)}__{_slugificar(fecha_respuesta)}"


def _guardar_documento(coleccion: str, documento_id: str, datos: dict[str, Any]) -> str | None:
    db = obtener_firestore()
    if db is None:
        return None

    try:
        db.collection(coleccion).document(documento_id).set(datos, merge=True)
        print(f"[FIRESTORE] Registro guardado: {coleccion}/{documento_id}")
        return documento_id
    except Exception as error:  # pragma: no cover - depende de Firestore remoto
        logger.exception("[FIRESTORE] Error guardando %s/%s: %s", coleccion, documento_id, error)
        print(f"[FIRESTORE] Error guardando {coleccion}/{documento_id}: {error}")
        return None


def _listar_documentos(
    coleccion: str,
    filtro: tuple[str, str, Any] | None = None,
    propagar_error: bool = False,
) -> list[dict[str, Any]]:
    db = obtener_firestore()
    if db is None:
        return []

    try:
        consulta = db.collection(coleccion)
        if filtro is not None:
            campo, operador, valor = filtro
            consulta = consulta.where(filter=FieldFilter(campo, operador, valor))
        documentos = [documento.to_dict() | {"id": documento.id} for documento in consulta.stream()]
        return documentos
    except Exception as error:  # pragma: no cover - depende de Firestore remoto
        logger.exception("[FIRESTORE] Error leyendo %s: %s", coleccion, error)
        print(f"[FIRESTORE] Error leyendo {coleccion}: {error}")
        if propagar_error:
            raise
        return []


def _obtener_documento_por_id(
    coleccion: str,
    document_id: str,
    propagar_error: bool = False,
) -> dict[str, Any] | None:
    db = obtener_firestore()
    if db is None:
        return None

    try:
        documento = db.collection(coleccion).document(document_id).get()
        if documento.exists:
            return documento.to_dict() | {"id": documento.id}
        return None
    except Exception as error:  # pragma: no cover - depende de Firestore remoto
        logger.exception("[FIRESTORE] Error obteniendo %s/%s: %s", coleccion, document_id, error)
        print(f"[FIRESTORE] Error obteniendo {coleccion}/{document_id}: {error}")
        if propagar_error:
            raise
        return None


def guardar_formulario(formulario: Mapping[str, Any], legacy_sqlite_id: int | None = None) -> str | None:
    """Guarda un formulario en la colección formularios."""

    formulario_doc_id = _base_doc_id_formulario(formulario)
    datos = {
        "legacy_sqlite_id": legacy_sqlite_id,
        "clave_formulario": formulario.get("clave_formulario"),
        "nombre": formulario.get("nombre"),
        "worksheet_nombre": formulario.get("worksheet_nombre"),
        "total_estudiantes": int(formulario.get("total_estudiantes", 0) or 0),
        "promedio_creatividad": float(formulario.get("promedio_creatividad", 0) or 0),
        "promedio_originalidad": float(formulario.get("promedio_originalidad", 0) or 0),
        "promedio_curiosidad": float(formulario.get("promedio_curiosidad", 0) or 0),
        "ultima_sincronizacion": formulario.get("ultima_sincronizacion"),
        "created_at": formulario.get("created_at") or _ahora(),
        "updated_at": _ahora(),
    }
    return _guardar_documento("formularios", formulario_doc_id, datos)


def guardar_estudiante(
    estudiante: Mapping[str, Any],
    legacy_sqlite_id: int | None = None,
    formulario_legacy_sqlite_id: int | None = None,
) -> str | None:
    """Guarda el documento del estudiante en la colección estudiantes."""

    estudiante_doc_id = _base_doc_id_estudiante(estudiante)
    datos = {
        "legacy_sqlite_id": legacy_sqlite_id,
        "formulario_legacy_sqlite_id": formulario_legacy_sqlite_id,
        "formulario_doc_id": estudiante.get("formulario_doc_id"),
        "nombre": estudiante.get("nombre"),
        "correo": estudiante.get("correo"),
        "fecha_respuesta": estudiante.get("fecha_respuesta"),
        "respuestas": estudiante.get("respuestas", {}),
        "perfil_principal": estudiante.get("perfil_principal"),
        "perfil_secundario": estudiante.get("perfil_secundario"),
        "descripcion": estudiante.get("descripcion"),
        "puntaje_total": int(estudiante.get("puntaje_total", 0) or 0),
        "scores": dict(estudiante.get("puntajes", {})),
        "created_at": estudiante.get("created_at") or _ahora(),
        "updated_at": _ahora(),
    }
    return _guardar_documento("estudiantes", estudiante_doc_id, datos)


def guardar_resultados(
    resultados: Mapping[str, Any],
    legacy_sqlite_id: int | None = None,
    estudiante_legacy_sqlite_id: int | None = None,
    formulario_legacy_sqlite_id: int | None = None,
) -> str | None:
    """Guarda el resumen de puntajes en la colección resultados."""

    estudiante_doc_id = _slugificar(
        resultados.get("estudiante_doc_id")
        or resultados.get("estudiante_id")
        or resultados.get("legacy_sqlite_id")
        or "estudiante"
    )
    resultados_doc_id = estudiante_doc_id
    datos = {
        "legacy_sqlite_id": legacy_sqlite_id,
        "estudiante_legacy_sqlite_id": estudiante_legacy_sqlite_id,
        "formulario_legacy_sqlite_id": formulario_legacy_sqlite_id,
        "estudiante_doc_id": resultados.get("estudiante_doc_id"),
        "creatividad": int(resultados.get("creatividad", 0) or 0),
        "originalidad": int(resultados.get("originalidad", 0) or 0),
        "curiosidad": int(resultados.get("curiosidad", 0) or 0),
        "fluidez_ideas": int(resultados.get("fluidez_ideas", 0) or 0),
        "iniciativa": int(resultados.get("iniciativa", 0) or 0),
        "liderazgo": int(resultados.get("liderazgo", 0) or 0),
        "organizacion": int(resultados.get("organizacion", 0) or 0),
        "disciplina": int(resultados.get("disciplina", 0) or 0),
        "reflexion": int(resultados.get("reflexion", 0) or 0),
        "sensibilidad": int(resultados.get("sensibilidad", 0) or 0),
        "desinhibicion": int(resultados.get("desinhibicion", 0) or 0),
        "puntaje_total": int(resultados.get("puntaje_total", 0) or 0),
        "created_at": resultados.get("created_at") or _ahora(),
        "updated_at": _ahora(),
    }
    return _guardar_documento("resultados", resultados_doc_id, datos)


def guardar_respuesta(
    respuesta: Mapping[str, Any],
    legacy_sqlite_id: int | None = None,
    estudiante_legacy_sqlite_id: int | None = None,
    formulario_legacy_sqlite_id: int | None = None,
    orden: int | None = None,
) -> str | None:
    """Guarda una respuesta individual en la colección respuestas."""

    estudiante_doc_id = _slugificar(
        respuesta.get("estudiante_doc_id")
        or respuesta.get("estudiante_id")
        or respuesta.get("legacy_sqlite_id")
        or "estudiante"
    )
    pregunta = str(respuesta.get("pregunta", "pregunta_sin_nombre"))
    orden_texto = f"{int(orden or 0):03d}"
    respuesta_doc_id = f"{estudiante_doc_id}__{orden_texto}__{_slugificar(pregunta)}"
    datos = {
        "legacy_sqlite_id": legacy_sqlite_id,
        "estudiante_legacy_sqlite_id": estudiante_legacy_sqlite_id,
        "formulario_legacy_sqlite_id": formulario_legacy_sqlite_id,
        "estudiante_doc_id": respuesta.get("estudiante_doc_id"),
        "orden": orden,
        "pregunta": pregunta,
        "respuesta": respuesta.get("respuesta"),
        "created_at": respuesta.get("created_at") or _ahora(),
        "updated_at": _ahora(),
    }
    return _guardar_documento("respuestas", respuesta_doc_id, datos)


def obtener_formularios(propagar_error: bool = False) -> list[dict[str, Any]]:
    """Obtiene todos los formularios almacenados en Firestore."""

    formularios = _listar_documentos("formularios", propagar_error=propagar_error)
    formularios.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    return formularios


def obtener_estudiantes(
    formulario_legacy_sqlite_id: int | None = None,
    propagar_error: bool = False,
) -> list[dict[str, Any]]:
    """Obtiene estudiantes almacenados en Firestore, filtrando opcionalmente por formulario."""

    filtro = None
    if formulario_legacy_sqlite_id is not None:
        filtro = ("formulario_legacy_sqlite_id", "==", formulario_legacy_sqlite_id)
    estudiantes = _listar_documentos("estudiantes", filtro=filtro, propagar_error=propagar_error)
    estudiantes.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    return estudiantes


def obtener_estudiante(
    legacy_sqlite_id: int | None = None,
    document_id: str | None = None,
    propagar_error: bool = False,
) -> dict[str, Any] | None:
    """Obtiene un estudiante por ID de documento o por legacy_sqlite_id."""

    try:
        if document_id:
            documento = _obtener_documento_por_id("estudiantes", document_id, propagar_error=propagar_error)
            if documento is not None:
                return documento

        if legacy_sqlite_id is not None:
            documentos = _listar_documentos(
                "estudiantes",
                filtro=("legacy_sqlite_id", "==", legacy_sqlite_id),
                propagar_error=propagar_error,
            )
            for documento in documentos:
                return documento
    except Exception as error:  # pragma: no cover
        logger.exception("[FIRESTORE] Error obteniendo estudiante: %s", error)
        print(f"[FIRESTORE] Error obteniendo estudiante: {error}")
        if propagar_error:
            raise

    return None


def obtener_formulario(
    legacy_sqlite_id: int | None = None,
    document_id: str | None = None,
    propagar_error: bool = False,
) -> dict[str, Any] | None:
    """Obtiene un formulario por document_id o legacy_sqlite_id."""

    try:
        if document_id:
            formulario = _obtener_documento_por_id("formularios", document_id, propagar_error=propagar_error)
            if formulario is not None:
                return formulario

        if legacy_sqlite_id is not None:
            formularios = _listar_documentos(
                "formularios",
                filtro=("legacy_sqlite_id", "==", legacy_sqlite_id),
                propagar_error=propagar_error,
            )
            if formularios:
                return formularios[0]
    except Exception as error:  # pragma: no cover
        logger.exception("[FIRESTORE] Error obteniendo formulario: %s", error)
        print(f"[FIRESTORE] Error obteniendo formulario: {error}")
        if propagar_error:
            raise

    return None


def obtener_resultado(
    legacy_sqlite_id: int | None = None,
    estudiante_legacy_sqlite_id: int | None = None,
    document_id: str | None = None,
    propagar_error: bool = False,
) -> dict[str, Any] | None:
    """Obtiene un resultado agregado."""

    try:
        if document_id:
            resultado = _obtener_documento_por_id("resultados", document_id, propagar_error=propagar_error)
            if resultado is not None:
                return resultado

        filtro = None
        if legacy_sqlite_id is not None:
            filtro = ("legacy_sqlite_id", "==", legacy_sqlite_id)
        elif estudiante_legacy_sqlite_id is not None:
            filtro = ("estudiante_legacy_sqlite_id", "==", estudiante_legacy_sqlite_id)

        resultados = _listar_documentos("resultados", filtro=filtro, propagar_error=propagar_error)
        if resultados:
            return resultados[0]
    except Exception as error:  # pragma: no cover
        logger.exception("[FIRESTORE] Error obteniendo resultado: %s", error)
        print(f"[FIRESTORE] Error obteniendo resultado: {error}")
        if propagar_error:
            raise

    return None


def obtener_respuestas_estudiante(
    legacy_sqlite_id: int | None = None,
    estudiante_legacy_sqlite_id: int | None = None,
    document_id: str | None = None,
    propagar_error: bool = False,
) -> list[dict[str, Any]]:
    """Obtiene las respuestas asociadas a un estudiante."""

    try:
        if document_id:
            respuestas = _listar_documentos(
                "respuestas",
                filtro=("estudiante_doc_id", "==", document_id),
                propagar_error=propagar_error,
            )
        else:
            filtro = None
            if legacy_sqlite_id is not None:
                filtro = ("estudiante_legacy_sqlite_id", "==", legacy_sqlite_id)
            elif estudiante_legacy_sqlite_id is not None:
                filtro = ("estudiante_legacy_sqlite_id", "==", estudiante_legacy_sqlite_id)
            respuestas = _listar_documentos("respuestas", filtro=filtro, propagar_error=propagar_error)

        respuestas.sort(key=lambda item: int(item.get("orden") or 0))
        return respuestas
    except Exception as error:  # pragma: no cover
        logger.exception("[FIRESTORE] Error obteniendo respuestas: %s", error)
        print(f"[FIRESTORE] Error obteniendo respuestas: {error}")
        if propagar_error:
            raise

    return []
