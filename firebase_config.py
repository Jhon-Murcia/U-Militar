"""Inicializacion global de Firebase Admin SDK y Firestore."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from google.auth.exceptions import DefaultCredentialsError

from project.google_credentials import cargar_service_account


logger = logging.getLogger(__name__)

_FIREBASE_APP: Any | None = None
_FIRESTORE_DB: firestore.Client | None = None


def _obtener_credenciales() -> dict[str, Any] | str | None:
    return cargar_service_account(
        json_env="TESTQREATOR_FIREBASE_CREDENTIALS_JSON",
        base64_env="TESTQREATOR_FIREBASE_CREDENTIALS_BASE64",
        file_env="TESTQREATOR_FIREBASE_CREDENTIALS",
        default_path=Path(__file__).resolve().parent / "credentials" / "firebase.json",
    )


def _crear_credenciales() -> credentials.Base:
    credenciales_origen = _obtener_credenciales()
    if isinstance(credenciales_origen, dict):
        return credentials.Certificate(credenciales_origen)
    if isinstance(credenciales_origen, str):
        return credentials.Certificate(credenciales_origen)

    try:
        return credentials.ApplicationDefault()
    except DefaultCredentialsError as error:
        raise RuntimeError(
            "No se encontraron credenciales de Firebase. Configura "
            "TESTQREATOR_FIREBASE_CREDENTIALS_JSON, "
            "TESTQREATOR_FIREBASE_CREDENTIALS_BASE64 o credenciales ADC."
        ) from error


def inicializar_firebase() -> firestore.Client | None:
    """Inicializa Firebase Admin SDK y devuelve el cliente de Firestore."""

    global _FIREBASE_APP, _FIRESTORE_DB

    if _FIRESTORE_DB is not None:
        return _FIRESTORE_DB

    try:
        if not firebase_admin._apps:
            opciones: dict[str, Any] = {}
            project_id = (
                os.getenv("TESTQREATOR_FIREBASE_PROJECT_ID", "").strip()
                or os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
            )
            if project_id:
                opciones["projectId"] = project_id

            _FIREBASE_APP = firebase_admin.initialize_app(
                _crear_credenciales(),
                opciones or None,
            )
        else:
            _FIREBASE_APP = firebase_admin.get_app()

        _FIRESTORE_DB = firestore.client(app=_FIREBASE_APP)
        logger.info("[FIRESTORE] Cliente inicializado correctamente")
    except Exception as error:  # pragma: no cover - depende del entorno de despliegue
        _FIRESTORE_DB = None
        logger.exception("[FIRESTORE] Error inicializando Firebase: %s", error)

    return _FIRESTORE_DB


def obtener_firestore() -> firestore.Client | None:
    """Devuelve el cliente global de Firestore, inicializandolo si es necesario."""

    return inicializar_firebase()
