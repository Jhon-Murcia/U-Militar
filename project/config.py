"""Configuración central del proyecto TestQreator."""

from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

APP_TITLE = "TestQreator"

ARCHIVO_CREDENCIALES = os.getenv(
    "TESTQREATOR_CREDENTIALS",
    str(BASE_DIR / "credenciales.json"),
)

DATABASE_PATH = os.getenv(
    "TESTQREATOR_DATABASE",
    str(BASE_DIR / "testqreator.db"),
)

SPREADSHEET_NAME = os.getenv("TESTQREATOR_SPREADSHEET", "").strip()
WORKSHEET_NAME = os.getenv("TESTQREATOR_WORKSHEET", "").strip()
USAR_DATOS_EJEMPLO = os.getenv("TESTQREATOR_USAR_EJEMPLOS", "0").lower() not in {
    "0",
    "false",
    "no",
}

LOGIN_USUARIO = os.getenv("TESTQREATOR_LOGIN_USER", "").strip()
LOGIN_CONTRASENA = os.getenv("TESTQREATOR_LOGIN_PASSWORD", "").strip()

DATA_SOURCE = os.getenv("DATA_SOURCE", "firestore").strip().lower()
if DATA_SOURCE not in {"firestore", "sqlite"}:
    DATA_SOURCE = "firestore"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIMENSIONES = [
    "Creatividad",
    "Originalidad",
    "Curiosidad",
    "Fluidez de ideas",
    "Iniciativa",
    "Liderazgo",
    "Organización",
    "Disciplina",
    "Reflexión",
    "Sensibilidad",
    "Desinhibición",
]

FAMILIAS_PERFIL = {
    "Creativo": ["Creatividad", "Originalidad", "Fluidez de ideas"],
    "Curioso": ["Curiosidad", "Reflexión"],
    "Proactivo": ["Iniciativa", "Desinhibición"],
    "Líder": ["Liderazgo"],
    "Organizado": ["Organización", "Disciplina"],
    "Reflexivo": ["Reflexión", "Sensibilidad"],
    "Expresivo": ["Desinhibición", "Fluidez de ideas"],
}

DESCRIPCIONES_FAMILIA = {
    "Creativo": "busca soluciones novedosas y genera ideas originales con facilidad",
    "Curioso": "pregunta, investiga y busca comprender a fondo los temas de interés",
    "Proactivo": "tiende a tomar la iniciativa y actuar sin esperar instrucciones constantes",
    "Líder": "puede coordinar a otros y orientar procesos con seguridad",
    "Organizado": "mantiene orden, planificación y constancia en sus tareas",
    "Reflexivo": "analiza con calma, considera distintos puntos de vista y actúa con sensibilidad",
    "Expresivo": "se comunica con soltura y muestra una baja inhibición para participar",
}

REGLAS_PUNTUACION = [
    {
        "nombre": "Soluciones novedosas",
        "palabras_clave": ["soluciones novedosas", "novedosa", "novedosas", "innovadora", "innovadoras"],
        "puntajes": {"Creatividad": 2, "Originalidad": 2},
    },
    {
        "nombre": "Ideas múltiples",
        "palabras_clave": ["gran número de ideas", "muchas ideas", "varias ideas", "diversas ideas"],
        "puntajes": {"Creatividad": 2, "Fluidez de ideas": 2},
    },
    {
        "nombre": "Exploración curiosa",
        "palabras_clave": ["curioso", "curiosa", "investigar", "aprender más", "conocer más", "pregunto"],
        "puntajes": {"Curiosidad": 2},
    },
    {
        "nombre": "Pensamiento original",
        "palabras_clave": ["original", "originales", "diferente", "distinto", "distinta"],
        "puntajes": {"Originalidad": 2},
    },
    {
        "nombre": "Toma de iniciativa",
        "palabras_clave": ["iniciativa", "propongo", "me adelanto", "tomo la iniciativa"],
        "puntajes": {"Iniciativa": 2},
    },
    {
        "nombre": "Orientación al liderazgo",
        "palabras_clave": ["lidero", "liderazgo", "coordino", "guío", "dirijo"],
        "puntajes": {"Liderazgo": 2},
    },
    {
        "nombre": "Planificación y orden",
        "palabras_clave": ["organizado", "organizada", "planifico", "ordenado", "ordenada"],
        "puntajes": {"Organización": 2, "Disciplina": 1},
    },
    {
        "nombre": "Constancia disciplinada",
        "palabras_clave": ["disciplina", "constante", "cumplo", "responsable"],
        "puntajes": {"Disciplina": 2},
    },
    {
        "nombre": "Reflexión profunda",
        "palabras_clave": ["reflexiono", "analizo", "pienso antes", "me detengo a pensar"],
        "puntajes": {"Reflexión": 2},
    },
    {
        "nombre": "Sensibilidad empática",
        "palabras_clave": ["empático", "empática", "sensible", "escucho a los demás", "comprendo sentimientos"],
        "puntajes": {"Sensibilidad": 2, "Reflexión": 1},
    },
    {
        "nombre": "Expresión desinhibida",
        "palabras_clave": ["me expreso", "hablo en público", "sin miedo", "desinhibido", "desinhibida", "me atrevo"],
        "puntajes": {"Desinhibición": 2, "Liderazgo": 1},
    },
    {
        "nombre": "Bloqueo creativo",
        "palabras_clave": ["no soy creativo", "me faltan ideas", "no suelo aportar ideas", "me cuesta ser original"],
        "puntajes": {"Creatividad": -2, "Fluidez de ideas": -2, "Originalidad": -1},
    },
    {
        "nombre": "Inhibición social",
        "palabras_clave": ["me da miedo hablar", "me cuesta hablar en público", "evito participar", "prefiero no intervenir"],
        "puntajes": {"Desinhibición": -2, "Liderazgo": -1, "Iniciativa": -1},
    },
    {
        "nombre": "Desorden y poca constancia",
        "palabras_clave": ["soy desorganizado", "soy desorganizada", "me cuesta organizarme", "no soy constante"],
        "puntajes": {"Organización": -2, "Disciplina": -2},
    },
]

FORMULARIOS_EJEMPLO = [
    {
        "clave_formulario": "formulario-creatividad",
        "nombre": "Formulario de Creatividad y Curiosidad",
        "worksheet_nombre": "Respuestas de formulario 1",
        "respuestas": [
            {
                "nombre": "Ana Pérez",
                "correo": "ana.perez@example.com",
                "fecha_respuesta": "2026-06-11 08:10:00",
                "respuestas": {
                    "Me gustan las soluciones novedosas": "Totalmente de acuerdo",
                    "Suelo dar un gran número de ideas": "Sí, con frecuencia",
                    "Soy muy curioso y deseo conocer más sobre algunos temas": "Sí",
                    "Me expreso con facilidad en clase": "Bastante",
                },
            },
            {
                "nombre": "María López",
                "correo": "maria.lopez@example.com",
                "fecha_respuesta": "2026-06-11 08:20:00",
                "respuestas": {
                    "Suelo reflexionar antes de actuar": "Siempre",
                    "Me interesa comprender cómo se sienten los demás": "Sí",
                    "Me cuesta hablar en público": "No mucho",
                    "Me gusta investigar temas nuevos": "Sí",
                },
            },
        ],
    },
    {
        "clave_formulario": "formulario-liderazgo",
        "nombre": "Formulario de Liderazgo y Organización",
        "worksheet_nombre": "Respuestas de formulario 2",
        "respuestas": [
            {
                "nombre": "Luis Gómez",
                "correo": "luis.gomez@example.com",
                "fecha_respuesta": "2026-06-11 08:15:00",
                "respuestas": {
                    "Me gusta planificar mis actividades": "Totalmente de acuerdo",
                    "Cumplo con mis tareas de forma constante": "Sí",
                    "Me gusta coordinar trabajos en grupo": "Sí",
                    "Prefiero seguir instrucciones claras": "Sí",
                },
            },
            {
                "nombre": "Sofía Ramírez",
                "correo": "sofia.ramirez@example.com",
                "fecha_respuesta": "2026-06-11 08:30:00",
                "respuestas": {
                    "Suele organizar sus actividades con anticipación": "Sí",
                    "Me gusta dirigir al grupo cuando es necesario": "Sí",
                    "Me considero constante con mis responsabilidades": "Sí",
                    "Me cuesta organizarme": "No",
                },
            },
        ],
    },
]
