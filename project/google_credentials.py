"""Helpers para cargar credenciales de Google desde entorno o archivo local."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any


def cargar_service_account(
    *,
    json_env: str,
    base64_env: str,
    file_env: str,
    default_path: str | Path | None = None,
) -> dict[str, Any] | str | None:
    """Devuelve credenciales como dict, ruta de archivo o None para ADC."""

    valor_json = os.getenv(json_env, "").strip()
    if valor_json:
        return json.loads(valor_json)

    valor_base64 = os.getenv(base64_env, "").strip()
    if valor_base64:
        contenido = base64.b64decode(valor_base64).decode("utf-8")
        return json.loads(contenido)

    ruta_env = os.getenv(file_env, "").strip()
    if ruta_env:
        return ruta_env

    google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if google_application_credentials:
        return google_application_credentials

    if default_path:
        ruta_default = Path(default_path)
        if ruta_default.exists():
            return str(ruta_default)

    return None
