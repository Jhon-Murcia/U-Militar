"""Persistencia SQLite para estudiantes, resultados y respuestas."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH, FAMILIAS_PERFIL


def obtener_conexion() -> sqlite3.Connection:
    conexion = sqlite3.connect(DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _columna_existe(conexion: sqlite3.Connection, tabla: str, columna: str) -> bool:
    filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    return any(fila[1] == columna for fila in filas)


def _asegurar_columna(conexion: sqlite3.Connection, tabla: str, definicion: str, columna: str) -> None:
    if not _columna_existe(conexion, tabla, columna):
        conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {definicion}")


def inicializar_base_datos() -> None:
    """Crea las tablas necesarias si todavía no existen."""

    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    with obtener_conexion() as conexion:
        conexion.executescript(
            """
            CREATE TABLE IF NOT EXISTS formularios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave_formulario TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                worksheet_nombre TEXT NOT NULL DEFAULT '',
                total_estudiantes INTEGER NOT NULL DEFAULT 0,
                promedio_creatividad REAL NOT NULL DEFAULT 0,
                promedio_originalidad REAL NOT NULL DEFAULT 0,
                promedio_curiosidad REAL NOT NULL DEFAULT 0,
                ultima_sincronizacion TEXT,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS estudiantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                formulario_id INTEGER,
                fecha_respuesta TEXT NOT NULL,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL,
                respuestas_json TEXT NOT NULL,
                perfil_principal TEXT NOT NULL,
                perfil_secundario TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                puntaje_total INTEGER NOT NULL DEFAULT 0,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(correo, fecha_respuesta)
            );

            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                creatividad INTEGER NOT NULL DEFAULT 0,
                originalidad INTEGER NOT NULL DEFAULT 0,
                curiosidad INTEGER NOT NULL DEFAULT 0,
                fluidez_ideas INTEGER NOT NULL DEFAULT 0,
                iniciativa INTEGER NOT NULL DEFAULT 0,
                liderazgo INTEGER NOT NULL DEFAULT 0,
                organizacion INTEGER NOT NULL DEFAULT 0,
                disciplina INTEGER NOT NULL DEFAULT 0,
                reflexion INTEGER NOT NULL DEFAULT 0,
                sensibilidad INTEGER NOT NULL DEFAULT 0,
                desinhibicion INTEGER NOT NULL DEFAULT 0,
                puntaje_total INTEGER NOT NULL DEFAULT 0,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS respuestas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                pregunta TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_estudiantes_nombre ON estudiantes(nombre);
            CREATE INDEX IF NOT EXISTS idx_estudiantes_correo ON estudiantes(correo);
            CREATE INDEX IF NOT EXISTS idx_resultados_estudiante ON resultados(estudiante_id);
            CREATE INDEX IF NOT EXISTS idx_respuestas_estudiante ON respuestas(estudiante_id);
            """
        )

        _asegurar_columna(conexion, "estudiantes", "formulario_id INTEGER", "formulario_id")
        conexion.execute("CREATE INDEX IF NOT EXISTS idx_estudiantes_formulario ON estudiantes(formulario_id)")
        conexion.commit()


def limpiar_datos_analizados() -> None:
    """Elimina el contenido analizado antes de una sincronización nueva."""

    with obtener_conexion() as conexion:
        conexion.execute("DELETE FROM respuestas")
        conexion.execute("DELETE FROM resultados")
        conexion.execute("DELETE FROM estudiantes")
        conexion.commit()


def guardar_formulario(formulario: dict[str, Any]) -> int:
    """Inserta o actualiza un formulario detectado en Google Sheets."""

    inicializar_base_datos()

    clave_formulario = str(formulario.get("clave_formulario", "")).strip() or "formulario-desconocido"
    nombre = str(formulario.get("nombre", "Formulario sin nombre")).strip() or "Formulario sin nombre"
    worksheet_nombre = str(formulario.get("worksheet_nombre", "")).strip()

    with obtener_conexion() as conexion:
        fila_existente = conexion.execute(
            "SELECT id FROM formularios WHERE clave_formulario = ?",
            (clave_formulario,),
        ).fetchone()

        if fila_existente is None:
            cursor = conexion.execute(
                """
                INSERT INTO formularios (clave_formulario, nombre, worksheet_nombre, ultima_sincronizacion)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (clave_formulario, nombre, worksheet_nombre),
            )
            formulario_id = int(cursor.lastrowid)
        else:
            formulario_id = int(fila_existente["id"])
            conexion.execute(
                """
                UPDATE formularios
                SET nombre = ?, worksheet_nombre = ?, ultima_sincronizacion = CURRENT_TIMESTAMP,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (nombre, worksheet_nombre, formulario_id),
            )

        conexion.commit()

    return formulario_id


def actualizar_resumen_formulario(formulario_id: int) -> None:
    """Calcula el resumen agregado de un formulario específico."""

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                COUNT(s.id) AS total_estudiantes,
                COALESCE(AVG(r.creatividad), 0) AS promedio_creatividad,
                COALESCE(AVG(r.originalidad), 0) AS promedio_originalidad,
                COALESCE(AVG(r.curiosidad), 0) AS promedio_curiosidad
            FROM estudiantes s
            LEFT JOIN resultados r ON r.estudiante_id = s.id
            WHERE s.formulario_id = ?
            """,
            (formulario_id,),
        ).fetchone()

        conexion.execute(
            """
            UPDATE formularios
            SET total_estudiantes = ?, promedio_creatividad = ?, promedio_originalidad = ?,
                promedio_curiosidad = ?, actualizado_en = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(fila["total_estudiantes"] or 0),
                round(float(fila["promedio_creatividad"] or 0), 2),
                round(float(fila["promedio_originalidad"] or 0), 2),
                round(float(fila["promedio_curiosidad"] or 0), 2),
                formulario_id,
            ),
        )
        conexion.commit()


def recalcular_resumen_formularios() -> None:
    """Recalcula los resúmenes de todos los formularios existentes."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        formularios = conexion.execute("SELECT id FROM formularios ORDER BY id ASC").fetchall()

    for formulario in formularios:
        actualizar_resumen_formulario(int(formulario["id"]))


def _mapear_puntajes(puntajes: dict[str, int]) -> dict[str, int]:
    return {
        "creatividad": int(puntajes.get("Creatividad", 0)),
        "originalidad": int(puntajes.get("Originalidad", 0)),
        "curiosidad": int(puntajes.get("Curiosidad", 0)),
        "fluidez_ideas": int(puntajes.get("Fluidez de ideas", 0)),
        "iniciativa": int(puntajes.get("Iniciativa", 0)),
        "liderazgo": int(puntajes.get("Liderazgo", 0)),
        "organizacion": int(puntajes.get("Organización", 0)),
        "disciplina": int(puntajes.get("Disciplina", 0)),
        "reflexion": int(puntajes.get("Reflexión", 0)),
        "sensibilidad": int(puntajes.get("Sensibilidad", 0)),
        "desinhibicion": int(puntajes.get("Desinhibición", 0)),
    }


def guardar_estudiante(analisis: dict[str, Any]) -> int:
    """Inserta o actualiza un estudiante analizado junto con su detalle."""

    inicializar_base_datos()

    formulario_id = int(analisis.get("formulario_id", 0) or 0)
    nombre = str(analisis.get("nombre", "Estudiante sin nombre")).strip() or "Estudiante sin nombre"
    correo = str(analisis.get("correo", "")).strip() or f"{nombre.lower().replace(' ', '_')}@sin-correo.local"
    fecha_respuesta = str(analisis.get("fecha_respuesta", "sin fecha")).strip() or "sin fecha"
    respuestas = analisis.get("respuestas", {}) or {}
    puntajes = analisis.get("puntajes", {}) or {}
    perfil_principal = str(analisis.get("perfil_principal", "Equilibrado")).strip() or "Equilibrado"
    perfil_secundario = str(analisis.get("perfil_secundario", "Equilibrado")).strip() or "Equilibrado"
    descripcion = str(analisis.get("descripcion", "")).strip() or "Sin descripción disponible."
    puntaje_total = int(analisis.get("puntaje_total", 0))

    puntajes_sql = _mapear_puntajes(dict(puntajes))
    respuestas_json = json.dumps(respuestas, ensure_ascii=False)

    with obtener_conexion() as conexion:
        fila_existente = conexion.execute(
            "SELECT id FROM estudiantes WHERE formulario_id = ? AND correo = ? AND fecha_respuesta = ?",
            (formulario_id, correo, fecha_respuesta),
        ).fetchone()

        if fila_existente is None:
            cursor = conexion.execute(
                """
                INSERT INTO estudiantes (
                    formulario_id, fecha_respuesta, nombre, correo, respuestas_json,
                    perfil_principal, perfil_secundario, descripcion, puntaje_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    formulario_id,
                    fecha_respuesta,
                    nombre,
                    correo,
                    respuestas_json,
                    perfil_principal,
                    perfil_secundario,
                    descripcion,
                    puntaje_total,
                ),
            )
            estudiante_id = int(cursor.lastrowid)
        else:
            estudiante_id = int(fila_existente["id"])
            conexion.execute("DELETE FROM resultados WHERE estudiante_id = ?", (estudiante_id,))
            conexion.execute("DELETE FROM respuestas WHERE estudiante_id = ?", (estudiante_id,))
            conexion.execute(
                """
                UPDATE estudiantes
                SET formulario_id = ?, nombre = ?, correo = ?, respuestas_json = ?, perfil_principal = ?,
                    perfil_secundario = ?, descripcion = ?, puntaje_total = ?, actualizado_en = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    formulario_id,
                    nombre,
                    correo,
                    respuestas_json,
                    perfil_principal,
                    perfil_secundario,
                    descripcion,
                    puntaje_total,
                    estudiante_id,
                ),
            )

        conexion.execute(
            """
            INSERT INTO resultados (
                estudiante_id, creatividad, originalidad, curiosidad, fluidez_ideas,
                iniciativa, liderazgo, organizacion, disciplina, reflexion,
                sensibilidad, desinhibicion, puntaje_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estudiante_id,
                puntajes_sql["creatividad"],
                puntajes_sql["originalidad"],
                puntajes_sql["curiosidad"],
                puntajes_sql["fluidez_ideas"],
                puntajes_sql["iniciativa"],
                puntajes_sql["liderazgo"],
                puntajes_sql["organizacion"],
                puntajes_sql["disciplina"],
                puntajes_sql["reflexion"],
                puntajes_sql["sensibilidad"],
                puntajes_sql["desinhibicion"],
                puntaje_total,
            ),
        )

        for pregunta, respuesta in respuestas.items():
            conexion.execute(
                """
                INSERT INTO respuestas (estudiante_id, pregunta, respuesta)
                VALUES (?, ?, ?)
                """,
                (estudiante_id, str(pregunta), str(respuesta)),
            )

        conexion.commit()

    print(f"[SQLITE] Registro guardado: estudiante_id={estudiante_id}")

    return estudiante_id


def obtener_resultado_por_estudiante_id(estudiante_id: int) -> dict[str, Any] | None:
    """Devuelve el resultado agregado más reciente de un estudiante."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                id,
                estudiante_id,
                creatividad,
                originalidad,
                curiosidad,
                fluidez_ideas,
                iniciativa,
                liderazgo,
                organizacion,
                disciplina,
                reflexion,
                sensibilidad,
                desinhibicion,
                puntaje_total,
                creado_en
            FROM resultados
            WHERE estudiante_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (estudiante_id,),
        ).fetchone()

    return dict(fila) if fila else None


def obtener_respuestas_por_estudiante_id(estudiante_id: int) -> list[dict[str, Any]]:
    """Devuelve las respuestas individuales de un estudiante ordenadas por inserción."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT
                id,
                estudiante_id,
                pregunta,
                respuesta,
                creado_en
            FROM respuestas
            WHERE estudiante_id = ?
            ORDER BY id ASC
            """,
            (estudiante_id,),
        ).fetchall()

    return [dict(fila) for fila in filas]


def listar_formularios() -> list[dict[str, Any]]:
    """Devuelve la lista de formularios aplicados con sus resúmenes."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        filas = conexion.execute(
            """
            SELECT
                id,
                clave_formulario,
                nombre,
                worksheet_nombre,
                total_estudiantes,
                promedio_creatividad,
                promedio_originalidad,
                promedio_curiosidad,
                ultima_sincronizacion,
                creado_en,
                actualizado_en
            FROM formularios
            ORDER BY actualizado_en DESC, nombre ASC
            """
        ).fetchall()

    return [dict(fila) for fila in filas]


def obtener_formulario_por_id(formulario_id: int) -> dict[str, Any] | None:
    """Devuelve un formulario por su identificador interno."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                id,
                clave_formulario,
                nombre,
                worksheet_nombre,
                total_estudiantes,
                promedio_creatividad,
                promedio_originalidad,
                promedio_curiosidad,
                ultima_sincronizacion,
                creado_en,
                actualizado_en
            FROM formularios
            WHERE id = ?
            """,
            (formulario_id,),
        ).fetchone()

    return dict(fila) if fila else None


def listar_estudiantes(
    busqueda: str = "",
    perfil: str = "",
    formulario_id: int | None = None,
) -> list[dict[str, Any]]:
    """Lista estudiantes con filtros opcionales por texto y perfil."""

    inicializar_base_datos()

    consulta = [
        """
        SELECT
            s.id,
            s.formulario_id,
            s.fecha_respuesta,
            s.nombre,
            s.correo,
            s.perfil_principal,
            s.perfil_secundario,
            s.descripcion,
            s.puntaje_total,
            f.nombre AS formulario_nombre,
            r.creatividad,
            r.originalidad,
            r.curiosidad,
            r.fluidez_ideas,
            r.iniciativa,
            r.liderazgo,
            r.organizacion,
            r.disciplina,
            r.reflexion,
            r.sensibilidad,
            r.desinhibicion
        FROM estudiantes s
        LEFT JOIN formularios f ON f.id = s.formulario_id
        LEFT JOIN resultados r ON r.estudiante_id = s.id
        WHERE 1 = 1
        """
    ]
    parametros: list[Any] = []

    if formulario_id is not None:
        consulta.append(" AND s.formulario_id = ?")
        parametros.append(formulario_id)

    if busqueda:
        consulta.append(
            """
            AND (
                s.nombre LIKE ? OR
                s.correo LIKE ? OR
                s.perfil_principal LIKE ? OR
                s.perfil_secundario LIKE ?
            )
            """
        )
        patron = f"%{busqueda}%"
        parametros.extend([patron, patron, patron, patron])

    if perfil:
        consulta.append(" AND (s.perfil_principal = ? OR s.perfil_secundario = ?)")
        parametros.extend([perfil, perfil])

    consulta.append(" ORDER BY s.id DESC")

    with obtener_conexion() as conexion:
        filas = conexion.execute("".join(consulta), parametros).fetchall()

    return [dict(fila) for fila in filas]


def obtener_metricas_formulario(formulario_id: int) -> dict[str, float | int]:
    """Calcula métricas agregadas para un formulario específico."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                COUNT(*) AS total_estudiantes,
                COALESCE(AVG(r.creatividad), 0) AS promedio_creatividad,
                COALESCE(AVG(r.originalidad), 0) AS promedio_originalidad,
                COALESCE(AVG(r.curiosidad), 0) AS promedio_curiosidad
            FROM estudiantes s
            LEFT JOIN resultados r ON r.estudiante_id = s.id
            WHERE s.formulario_id = ?
            """,
            (formulario_id,),
        ).fetchone()

    return {
        "total_estudiantes": int(fila["total_estudiantes"] or 0),
        "promedio_creatividad": round(float(fila["promedio_creatividad"] or 0), 2),
        "promedio_originalidad": round(float(fila["promedio_originalidad"] or 0), 2),
        "promedio_curiosidad": round(float(fila["promedio_curiosidad"] or 0), 2),
    }


def obtener_metricas() -> dict[str, float | int]:
    """Calcula métricas globales del panel principal."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                COUNT(*) AS total_estudiantes,
                COALESCE(AVG(r.creatividad), 0) AS promedio_creatividad,
                COALESCE(AVG(r.originalidad), 0) AS promedio_originalidad,
                COALESCE(AVG(r.curiosidad), 0) AS promedio_curiosidad
            FROM estudiantes s
            LEFT JOIN resultados r ON r.estudiante_id = s.id
            """
        ).fetchone()

    return {
        "total_estudiantes": int(fila["total_estudiantes"] or 0),
        "promedio_creatividad": round(float(fila["promedio_creatividad"] or 0), 2),
        "promedio_originalidad": round(float(fila["promedio_originalidad"] or 0), 2),
        "promedio_curiosidad": round(float(fila["promedio_curiosidad"] or 0), 2),
    }


def obtener_estudiante_por_id(estudiante_id: int) -> dict[str, Any] | None:
    """Devuelve el detalle completo de un estudiante."""

    inicializar_base_datos()

    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                s.id,
                s.formulario_id,
                s.fecha_respuesta,
                s.nombre,
                s.correo,
                s.respuestas_json,
                s.perfil_principal,
                s.perfil_secundario,
                s.descripcion,
                s.puntaje_total,
                f.nombre AS formulario_nombre,
                r.creatividad,
                r.originalidad,
                r.curiosidad,
                r.fluidez_ideas,
                r.iniciativa,
                r.liderazgo,
                r.organizacion,
                r.disciplina,
                r.reflexion,
                r.sensibilidad,
                r.desinhibicion
            FROM estudiantes s
            LEFT JOIN formularios f ON f.id = s.formulario_id
            LEFT JOIN resultados r ON r.estudiante_id = s.id
            WHERE s.id = ?
            """,
            (estudiante_id,),
        ).fetchone()

        if fila is None:
            return None

        respuestas = conexion.execute(
            """
            SELECT pregunta, respuesta
            FROM respuestas
            WHERE estudiante_id = ?
            ORDER BY id ASC
            """,
            (estudiante_id,),
        ).fetchall()

    detalle = dict(fila)
    detalle["respuestas"] = [dict(respuesta) for respuesta in respuestas]
    detalle["puntajes"] = {
        "Creatividad": detalle.pop("creatividad", 0) or 0,
        "Originalidad": detalle.pop("originalidad", 0) or 0,
        "Curiosidad": detalle.pop("curiosidad", 0) or 0,
        "Fluidez de ideas": detalle.pop("fluidez_ideas", 0) or 0,
        "Iniciativa": detalle.pop("iniciativa", 0) or 0,
        "Liderazgo": detalle.pop("liderazgo", 0) or 0,
        "Organización": detalle.pop("organizacion", 0) or 0,
        "Disciplina": detalle.pop("disciplina", 0) or 0,
        "Reflexión": detalle.pop("reflexion", 0) or 0,
        "Sensibilidad": detalle.pop("sensibilidad", 0) or 0,
        "Desinhibición": detalle.pop("desinhibicion", 0) or 0,
    }
    return detalle


def obtener_perfiles_disponibles() -> list[str]:
    return list(FAMILIAS_PERFIL.keys())
