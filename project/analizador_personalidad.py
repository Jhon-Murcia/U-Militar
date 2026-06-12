"""Motor de análisis de respuestas para TestQreator."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Mapping

from .config import DIMENSIONES, REGLAS_PUNTUACION


def _normalizar_texto(texto: str) -> str:
    texto_normalizado = unicodedata.normalize("NFKD", texto.lower())
    texto_sin_acentos = "".join(
        caracter for caracter in texto_normalizado if not unicodedata.combining(caracter)
    )
    return re.sub(r"\s+", " ", texto_sin_acentos).strip()


@dataclass(frozen=True)
class ReglaPuntuacion:
    """Regla configurable de puntuación."""

    nombre: str
    palabras_clave: tuple[str, ...]
    puntajes: dict[str, int]


@dataclass
class ResultadoAnalisis:
    """Resultado agregado del análisis de respuestas."""

    puntajes: dict[str, int]
    evidencias: list[str]

    @property
    def puntaje_total(self) -> int:
        return sum(self.puntajes.values())


class AnalizadorPersonalidad:
    """Calcula puntajes psicológicos a partir de respuestas textuales."""

    def __init__(self, reglas: list[dict[str, Any]] | None = None) -> None:
        reglas_config = reglas or REGLAS_PUNTUACION
        self._reglas = [
            ReglaPuntuacion(
                nombre=regla["nombre"],
                palabras_clave=tuple(
                    _normalizar_texto(palabra) for palabra in regla["palabras_clave"]
                ),
                puntajes=dict(regla["puntajes"]),
            )
            for regla in reglas_config
        ]

    def analizar_respuestas(self, respuestas: Mapping[str, Any]) -> ResultadoAnalisis:
        """Analiza un diccionario pregunta -> respuesta y devuelve puntajes agregados."""

        puntajes = {dimension: 0 for dimension in DIMENSIONES}
        evidencias: list[str] = []

        for pregunta, respuesta in respuestas.items():
            texto = _normalizar_texto(f"{pregunta} {respuesta}")
            if not texto:
                continue

            for regla in self._reglas:
                if any(palabra in texto for palabra in regla.palabras_clave):
                    for dimension, valor in regla.puntajes.items():
                        puntajes[dimension] = puntajes.get(dimension, 0) + valor
                    evidencias.append(regla.nombre)

        return ResultadoAnalisis(puntajes=puntajes, evidencias=evidencias)
