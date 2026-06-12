"""Capa unificada de lectura para TestQreator."""

from __future__ import annotations

from typing import Any, Iterable

from .config import DATA_SOURCE
from . import database as sqlite_repository
import firebase_repository as firestore_repository


def _usar_firestore() -> bool:
    return DATA_SOURCE == "firestore"


def _normalizar_id(valor: Any) -> str:
    return str(valor).strip()


def _es_entero(valor: Any) -> bool:
    try:
        int(str(valor).strip())
        return True
    except Exception:
        return False


def _filtrar_por_texto(items: Iterable[dict[str, Any]], busqueda: str = "", perfil: str = "") -> list[dict[str, Any]]:
    busqueda_normalizada = busqueda.strip().lower()
    perfil_normalizado = perfil.strip().lower()
    filtrados: list[dict[str, Any]] = []

    for item in items:
        nombre = str(item.get("nombre", "")).lower()
        correo = str(item.get("correo", "")).lower()
        perfil_principal = str(item.get("perfil_principal", "")).lower()
        perfil_secundario = str(item.get("perfil_secundario", "")).lower()
        formulario_nombre = str(item.get("formulario_nombre", "")).lower()

        if busqueda_normalizada:
            coincide_busqueda = any(
                termino in campo
                for campo in (nombre, correo, perfil_principal, perfil_secundario, formulario_nombre)
                for termino in [busqueda_normalizada]
            )
            if not coincide_busqueda:
                continue

        if perfil_normalizado:
            coincide_perfil = perfil_normalizado in (perfil_principal, perfil_secundario)
            if not coincide_perfil:
                continue

        filtrados.append(item)

    return filtrados


def _enriquecer_formularios_en_estudiantes(estudiantes: list[dict[str, Any]], formularios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapa_por_legacy = {formulario.get("legacy_sqlite_id"): formulario for formulario in formularios if formulario.get("legacy_sqlite_id") is not None}
    mapa_por_id = {formulario.get("id"): formulario for formulario in formularios if formulario.get("id") is not None}

    for estudiante in estudiantes:
        formulario_nombre = estudiante.get("formulario_nombre")
        if formulario_nombre:
            continue

        formulario_doc_id = estudiante.get("formulario_doc_id")
        formulario_legacy_id = estudiante.get("formulario_legacy_sqlite_id")
        formulario = mapa_por_id.get(formulario_doc_id) or mapa_por_legacy.get(formulario_legacy_id)
        if formulario is not None:
            estudiante["formulario_nombre"] = formulario.get("nombre")
            estudiante["formulario_id"] = formulario.get("id")

        if "puntajes" not in estudiante:
            estudiante["puntajes"] = dict(estudiante.get("scores", {}) or {})

    return estudiantes


def listar_formularios() -> list[dict[str, Any]]:
    if _usar_firestore():
        try:
            formularios = firestore_repository.obtener_formularios(propagar_error=True)
            return formularios
        except Exception:
            pass

    return sqlite_repository.listar_formularios()


def obtener_formulario_por_id(formulario_id: str | int) -> dict[str, Any] | None:
    if _usar_firestore():
        try:
            formulario = firestore_repository.obtener_formulario(
                legacy_sqlite_id=int(formulario_id) if _es_entero(formulario_id) else None,
                document_id=_normalizar_id(formulario_id),
                propagar_error=True,
            )
            if formulario is not None:
                return formulario
        except Exception:
            pass

    if _es_entero(formulario_id):
        return sqlite_repository.obtener_formulario_por_id(int(formulario_id))
    return None


def listar_estudiantes(
    busqueda: str = "",
    perfil: str = "",
    formulario_id: str | int | None = None,
) -> list[dict[str, Any]]:
    if _usar_firestore():
        try:
            estudiantes = firestore_repository.obtener_estudiantes(propagar_error=True)
            formularios = firestore_repository.obtener_formularios(propagar_error=True)
            estudiantes = _enriquecer_formularios_en_estudiantes(estudiantes, formularios)

            if formulario_id is not None:
                formulario_id_texto = _normalizar_id(formulario_id)
                formulario_id_entero = int(formulario_id_texto) if _es_entero(formulario_id_texto) else None
                estudiantes = [
                    estudiante
                    for estudiante in estudiantes
                    if str(estudiante.get("formulario_doc_id", "")) == formulario_id_texto
                    or (
                        formulario_id_entero is not None
                        and estudiante.get("formulario_legacy_sqlite_id") == formulario_id_entero
                    )
                ]

            estudiantes = _filtrar_por_texto(estudiantes, busqueda=busqueda, perfil=perfil)
            return estudiantes
        except Exception:
            pass

    formulario_id_sqlite = int(formulario_id) if formulario_id is not None and _es_entero(formulario_id) else None
    return sqlite_repository.listar_estudiantes(
        busqueda=busqueda,
        perfil=perfil,
        formulario_id=formulario_id_sqlite,
    )


def obtener_estudiante_por_id(estudiante_id: str | int) -> dict[str, Any] | None:
    if _usar_firestore():
        try:
            estudiante = firestore_repository.obtener_estudiante(
                legacy_sqlite_id=int(estudiante_id) if _es_entero(estudiante_id) else None,
                document_id=_normalizar_id(estudiante_id),
                propagar_error=True,
            )
            if estudiante is not None:
                formulario = obtener_formulario_por_id(
                    estudiante.get("formulario_doc_id") or estudiante.get("formulario_legacy_sqlite_id") or ""
                )
                if formulario is not None:
                    estudiante["formulario_nombre"] = formulario.get("nombre")
                    estudiante["formulario_id"] = formulario.get("id")

                resultado = firestore_repository.obtener_resultado(
                    estudiante_legacy_sqlite_id=estudiante.get("legacy_sqlite_id"),
                    document_id=_normalizar_id(estudiante_id),
                    propagar_error=True,
                )
                if resultado is not None:
                    estudiante["puntajes"] = {
                        "Creatividad": int(resultado.get("creatividad", 0) or 0),
                        "Originalidad": int(resultado.get("originalidad", 0) or 0),
                        "Curiosidad": int(resultado.get("curiosidad", 0) or 0),
                        "Fluidez de ideas": int(resultado.get("fluidez_ideas", 0) or 0),
                        "Iniciativa": int(resultado.get("iniciativa", 0) or 0),
                        "Liderazgo": int(resultado.get("liderazgo", 0) or 0),
                        "Organización": int(resultado.get("organizacion", 0) or 0),
                        "Disciplina": int(resultado.get("disciplina", 0) or 0),
                        "Reflexión": int(resultado.get("reflexion", 0) or 0),
                        "Sensibilidad": int(resultado.get("sensibilidad", 0) or 0),
                        "Desinhibición": int(resultado.get("desinhibicion", 0) or 0),
                    }
                elif "puntajes" not in estudiante:
                    estudiante["puntajes"] = dict(estudiante.get("scores", {}) or {})

                respuestas = firestore_repository.obtener_respuestas_estudiante(
                    estudiante_legacy_sqlite_id=estudiante.get("legacy_sqlite_id"),
                    document_id=_normalizar_id(estudiante_id),
                    propagar_error=True,
                )
                estudiante["respuestas"] = [
                    {"pregunta": respuesta.get("pregunta"), "respuesta": respuesta.get("respuesta")}
                    for respuesta in respuestas
                ]
                if "puntajes" not in estudiante:
                    estudiante["puntajes"] = {
                        "Creatividad": 0,
                        "Originalidad": 0,
                        "Curiosidad": 0,
                        "Fluidez de ideas": 0,
                        "Iniciativa": 0,
                        "Liderazgo": 0,
                        "Organización": 0,
                        "Disciplina": 0,
                        "Reflexión": 0,
                        "Sensibilidad": 0,
                        "Desinhibición": 0,
                    }
                return estudiante
        except Exception:
            pass

    if _es_entero(estudiante_id):
        return sqlite_repository.obtener_estudiante_por_id(int(estudiante_id))
    return None


def obtener_metricas(formulario_id: str | int | None = None) -> dict[str, float | int]:
    if _usar_firestore():
        try:
            estudiantes = listar_estudiantes(formulario_id=formulario_id)

            total_estudiantes = len(estudiantes)
            if total_estudiantes == 0:
                return {
                    "total_estudiantes": 0,
                    "promedio_creatividad": 0.0,
                    "promedio_originalidad": 0.0,
                    "promedio_curiosidad": 0.0,
                }

            suma_creatividad = 0.0
            suma_originalidad = 0.0
            suma_curiosidad = 0.0
            for estudiante in estudiantes:
                puntajes = estudiante.get("puntajes", {}) or estudiante.get("scores", {}) or {}
                suma_creatividad += float(puntajes.get("Creatividad", 0) or 0)
                suma_originalidad += float(puntajes.get("Originalidad", 0) or 0)
                suma_curiosidad += float(puntajes.get("Curiosidad", 0) or 0)

            return {
                "total_estudiantes": total_estudiantes,
                "promedio_creatividad": round(suma_creatividad / total_estudiantes, 2),
                "promedio_originalidad": round(suma_originalidad / total_estudiantes, 2),
                "promedio_curiosidad": round(suma_curiosidad / total_estudiantes, 2),
            }
        except Exception:
            pass

    if formulario_id is not None and _es_entero(formulario_id):
        return sqlite_repository.obtener_metricas_formulario(int(formulario_id))
    return sqlite_repository.obtener_metricas()


def obtener_perfiles_disponibles() -> list[str]:
    return sqlite_repository.obtener_perfiles_disponibles()
