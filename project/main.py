"""Aplicación web principal de TestQreator."""

from __future__ import annotations

import logging
import os
import secrets
import time
from functools import wraps
from typing import Callable, TypeVar

from flask import Flask, abort, redirect, render_template, request, session, url_for

from .analizador_personalidad import AnalizadorPersonalidad
from .config import APP_TITLE, BASE_DIR, DATA_SOURCE, LOGIN_CONTRASENA, LOGIN_USUARIO
from .database import (
    guardar_estudiante,
    guardar_formulario,
    inicializar_base_datos,
    limpiar_datos_analizados,
    obtener_resultado_por_estudiante_id,
    obtener_respuestas_por_estudiante_id,
    recalcular_resumen_formularios,
    actualizar_resumen_formulario,
)
from .data_repository import (
    listar_estudiantes,
    listar_formularios,
    obtener_estudiante_por_id,
    obtener_formulario_por_id,
    obtener_metricas,
    obtener_perfiles_disponibles,
)
from .google_forms import obtener_formularios
from .perfilador import Perfilador

from firebase_repository import (
    guardar_estudiante as guardar_estudiante_firestore,
    guardar_formulario as guardar_formulario_firestore,
    guardar_resultados as guardar_resultados_firestore,
    guardar_respuesta as guardar_respuesta_firestore,
)


logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "web" / "templates"),
    static_folder=str(BASE_DIR / "web" / "static"),
)
app.config["JSON_AS_ASCII"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.secret_key = os.getenv("TESTQREATOR_SECRET_KEY") or secrets.token_hex(32)

_ULTIMA_SINCRONIZACION = 0.0
_INTERVALO_SINCRONIZACION = 60.0
_VistaFunc = TypeVar("_VistaFunc", bound=Callable[..., str])


def login_requerido(funcion: _VistaFunc) -> _VistaFunc:
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        if not session.get("usuario_autenticado"):
            return redirect(url_for("login"))
        return funcion(*args, **kwargs)

    return envoltura  # type: ignore[return-value]


def _credenciales_validas(usuario: str, contrasena: str) -> bool:
    if not LOGIN_USUARIO or not LOGIN_CONTRASENA:
        return False
    return usuario == LOGIN_USUARIO and contrasena == LOGIN_CONTRASENA


def sincronizar_datos(force: bool = False) -> int:
    """Lee Google Sheets, analiza cada formulario y guarda los resultados."""

    global _ULTIMA_SINCRONIZACION

    ahora = time.time()
    if not force and ahora - _ULTIMA_SINCRONIZACION < _INTERVALO_SINCRONIZACION:
        return 0

    inicializar_base_datos()
    formularios_entrada = obtener_formularios()
    if not formularios_entrada:
        return 0

    limpiar_datos_analizados()

    analizador = AnalizadorPersonalidad()
    perfilador = Perfilador()
    cantidad_guardada = 0

    for formulario in formularios_entrada:
        formulario_id = guardar_formulario(formulario)
        formulario_doc_id = guardar_formulario_firestore(
            {
                **formulario,
                "legacy_sqlite_id": formulario_id,
                "total_estudiantes": 0,
                "promedio_creatividad": 0,
                "promedio_originalidad": 0,
                "promedio_curiosidad": 0,
            },
            legacy_sqlite_id=formulario_id,
        ) or str(formulario.get("clave_formulario", formulario_id))
        respuestas_formulario = formulario.get("respuestas", []) or []

        for registro in respuestas_formulario:
            respuestas = registro.get("respuestas", {}) or {}
            analisis = analizador.analizar_respuestas(respuestas)
            perfil = perfilador.calcular_perfil(analisis.puntajes)
            estudiante_payload = {
                "formulario_id": formulario_id,
                "nombre": registro.get("nombre", "Estudiante sin nombre"),
                "correo": registro.get("correo", ""),
                "fecha_respuesta": registro.get("fecha_respuesta", "sin fecha"),
                "respuestas": respuestas,
                "puntajes": analisis.puntajes,
                "perfil_principal": perfil.perfil_principal,
                "perfil_secundario": perfil.perfil_secundario,
                "descripcion": perfil.descripcion,
                "puntaje_total": analisis.puntaje_total,
            }
            estudiante_id = guardar_estudiante(estudiante_payload)
            resultado_sqlite = obtener_resultado_por_estudiante_id(estudiante_id)
            respuestas_sqlite = obtener_respuestas_por_estudiante_id(estudiante_id)

            guardar_estudiante_firestore(
                {
                    **estudiante_payload,
                    "formulario_doc_id": formulario_doc_id,
                },
                legacy_sqlite_id=estudiante_id,
                formulario_legacy_sqlite_id=formulario_id,
            )

            if resultado_sqlite is not None:
                guardar_resultados_firestore(
                    {
                        **resultado_sqlite,
                        "estudiante_doc_id": f"{formulario_doc_id}__{str(estudiante_payload['correo']).strip().lower().replace('@', '_').replace('.', '_')}__{str(estudiante_payload['fecha_respuesta']).strip().lower().replace(' ', '_').replace(':', '_').replace('-', '_')}",
                    },
                    legacy_sqlite_id=resultado_sqlite.get("id"),
                    estudiante_legacy_sqlite_id=estudiante_id,
                    formulario_legacy_sqlite_id=formulario_id,
                )

            estudiante_doc_id = f"{formulario_doc_id}__{str(estudiante_payload['correo']).strip().lower().replace('@', '_').replace('.', '_')}__{str(estudiante_payload['fecha_respuesta']).strip().lower().replace(' ', '_').replace(':', '_').replace('-', '_')}"

            for orden, respuesta_sqlite in enumerate(respuestas_sqlite, start=1):
                guardar_respuesta_firestore(
                    {
                        **respuesta_sqlite,
                        "estudiante_doc_id": estudiante_doc_id,
                    },
                    legacy_sqlite_id=respuesta_sqlite.get("id"),
                    estudiante_legacy_sqlite_id=estudiante_id,
                    formulario_legacy_sqlite_id=formulario_id,
                    orden=orden,
                )

            cantidad_guardada += 1

        actualizar_resumen_formulario(formulario_id)

        formulario_actualizado = obtener_formulario_por_id(formulario_id) or {}
        formulario_actualizado.update(obtener_metricas(formulario_id=formulario_id))
        formulario_actualizado.setdefault("clave_formulario", formulario.get("clave_formulario"))
        formulario_actualizado.setdefault("nombre", formulario.get("nombre"))
        formulario_actualizado.setdefault("worksheet_nombre", formulario.get("worksheet_nombre"))
        guardar_formulario_firestore(
            {
                **formulario_actualizado,
                "legacy_sqlite_id": formulario_id,
                "total_estudiantes": formulario_actualizado.get("total_estudiantes", 0),
                "promedio_creatividad": formulario_actualizado.get("promedio_creatividad", 0),
                "promedio_originalidad": formulario_actualizado.get("promedio_originalidad", 0),
                "promedio_curiosidad": formulario_actualizado.get("promedio_curiosidad", 0),
            },
            legacy_sqlite_id=formulario_id,
        )

    recalcular_resumen_formularios()
    _ULTIMA_SINCRONIZACION = ahora
    logger.info("Sincronización completada: %s respuestas procesadas.", cantidad_guardada)
    return cantidad_guardada


@app.route("/")
def index() -> str:
    if not session.get("usuario_autenticado"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    error = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "").strip()

        if _credenciales_validas(usuario, contrasena):
            session["usuario_autenticado"] = True
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))

        error = "Credenciales inválidas. Intenta nuevamente."

    return render_template("login.html", error=error, app_title=APP_TITLE)


@app.route("/logout")
def logout() -> str:
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_requerido
def dashboard() -> str:
    """Vista principal con los formularios aplicados."""

    refresh = request.args.get("refresh", "0") == "1"
    sincronizar_datos(force=refresh)

    formularios = listar_formularios()
    metricas = obtener_metricas()

    return render_template(
        "dashboard.html",
        formularios=formularios,
        metricas=metricas,
        app_title=APP_TITLE,
        usuario=session.get("usuario", LOGIN_USUARIO),
    )


@app.route("/formulario/<formulario_id>")
@login_requerido
def detalle_formulario(formulario_id: str) -> str:
    """Muestra el detalle de un formulario aplicado y sus estudiantes."""

    sincronizar_datos()
    formulario = obtener_formulario_por_id(formulario_id)
    if formulario is None:
        abort(404)

    busqueda = request.args.get("q", "").strip()
    perfil = request.args.get("perfil", "").strip()

    estudiantes = listar_estudiantes(busqueda=busqueda, perfil=perfil, formulario_id=formulario_id)
    metricas_formulario = obtener_metricas(formulario_id=formulario_id)

    return render_template(
        "formulario_detalle.html",
        formulario=formulario,
        estudiantes=estudiantes,
        metricas=metricas_formulario,
        perfiles=obtener_perfiles_disponibles(),
        busqueda=busqueda,
        perfil_seleccionado=perfil,
        app_title=APP_TITLE,
        usuario=session.get("usuario", LOGIN_USUARIO),
    )


@app.route("/estudiante/<estudiante_id>")
@login_requerido
def detalle_estudiante(estudiante_id: str) -> str:
    """Muestra el detalle completo de un estudiante."""

    sincronizar_datos()
    estudiante = obtener_estudiante_por_id(estudiante_id)
    if estudiante is None:
        abort(404)

    return render_template(
        "detalle_estudiante.html",
        estudiante=estudiante,
        app_title=APP_TITLE,
        usuario=session.get("usuario", LOGIN_USUARIO),
    )


@app.errorhandler(404)
def not_found(_: Exception) -> tuple[str, int]:
    if not session.get("usuario_autenticado"):
        return render_template("login.html", error="La página solicitada no existe.", app_title=APP_TITLE), 404

    return (
        render_template(
            "dashboard.html",
            formularios=listar_formularios(),
            metricas=obtener_metricas(),
            app_title=APP_TITLE,
            usuario=session.get("usuario", LOGIN_USUARIO),
            error_404=True,
        ),
        404,
    )


def crear_app() -> Flask:
    """Permite usar la app con Flask CLI o con servidores WSGI."""

    return app
