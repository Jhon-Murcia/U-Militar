# google_forms.py

import gspread
from google.oauth2.service_account import Credentials
from config import ARCHIVO_CREDENCIALES, SCOPES


def conectar_google():

    credenciales = Credentials.from_service_account_file(
        ARCHIVO_CREDENCIALES,
        scopes=SCOPES
    )

    cliente = gspread.authorize(credenciales)

    return cliente


def obtener_respuestas():

    cliente = conectar_google()

    hojas = cliente.openall()

    if len(hojas) == 0:
        print("No se encontraron hojas disponibles.")
        return []

    archivo = hojas[0]

    print(f"Hoja encontrada: {archivo.title}")

    hoja = archivo.sheet1

    respuestas = hoja.get_all_records()

    return respuestas