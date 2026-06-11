# main.py

from google_forms import obtener_respuestas


def main():

    respuestas = obtener_respuestas()

    print("\nRESPUESTAS RECIBIDAS\n")

    for i, respuesta in enumerate(respuestas, start=1):

        print(f"\nPersona #{i}")

        for pregunta, valor in respuesta.items():

            print(f"{pregunta}")

            print(f"Respuesta: {valor}")

            print("-" * 50)


if __name__ == "__main__":
    main()
