"""Construye perfiles de personalidad a partir de los puntajes del análisis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .config import DESCRIPCIONES_FAMILIA, FAMILIAS_PERFIL


@dataclass(frozen=True)
class ResultadoPerfil:
    """Perfil predominante y descripción automática."""

    perfil_principal: str
    perfil_secundario: str
    descripcion: str
    familias_ordenadas: list[tuple[str, int]]


class Perfilador:
    """Agrupa dimensiones en familias de personalidad y genera la narración final."""

    def __init__(self) -> None:
        self._familias = list(FAMILIAS_PERFIL.items())

    def calcular_perfil(self, puntajes: Mapping[str, int]) -> ResultadoPerfil:
        """Determina el perfil principal y secundario a partir de los puntajes."""

        puntajes_familia: list[tuple[str, int]] = []
        for familia, dimensiones in self._familias:
            puntaje = sum(int(puntajes.get(dimension, 0)) for dimension in dimensiones)
            puntajes_familia.append((familia, puntaje))

        puntajes_familia.sort(key=lambda item: (-item[1], self._indice_familia(item[0])))

        perfil_principal = puntajes_familia[0][0] if puntajes_familia else "Equilibrado"
        perfil_secundario = (
            puntajes_familia[1][0]
            if len(puntajes_familia) > 1
            else "Equilibrado"
        )
        descripcion = self.generar_descripcion(perfil_principal, perfil_secundario, puntajes)

        return ResultadoPerfil(
            perfil_principal=perfil_principal,
            perfil_secundario=perfil_secundario,
            descripcion=descripcion,
            familias_ordenadas=puntajes_familia,
        )

    def generar_descripcion(
        self,
        perfil_principal: str,
        perfil_secundario: str,
        puntajes: Mapping[str, int],
    ) -> str:
        """Genera una descripción legible basada en los perfiles más fuertes."""

        descripcion_principal = DESCRIPCIONES_FAMILIA.get(
            perfil_principal,
            "mantiene un comportamiento equilibrado y adaptable",
        )
        descripcion_secundaria = DESCRIPCIONES_FAMILIA.get(
            perfil_secundario,
            "complementa su estilo con rasgos adicionales en desarrollo",
        )

        puntuaciones_ordenadas = sorted(
            ((dimension, int(valor)) for dimension, valor in puntajes.items()),
            key=lambda item: (-item[1], item[0]),
        )
        rasgos_destacados = [
            dimension.lower()
            for dimension, valor in puntuaciones_ordenadas[:3]
            if valor > 0
        ]

        if rasgos_destacados:
            lista_rasgos = ", ".join(rasgos_destacados)
            return (
                f"El estudiante presenta un perfil predominantemente {perfil_principal.lower()} "
                f"y {perfil_secundario.lower()}. Tiende a {descripcion_principal}, "
                f"con fortalezas complementarias en {descripcion_secundaria}. "
                f"Las dimensiones más visibles son: {lista_rasgos}."
            )

        return (
            f"El estudiante muestra un perfil en desarrollo con énfasis en {perfil_principal.lower()} "
            f"y {perfil_secundario.lower()}, con una distribución equilibrada de sus respuestas."
        )

    def _indice_familia(self, familia: str) -> int:
        return list(FAMILIAS_PERFIL.keys()).index(familia)
