# Despliegue de TestQreator

## Plataforma recomendada

La opcion recomendada es **Cloud Run**. TestQreator ya depende de Firestore y Google Sheets, por lo que Cloud Run encaja mejor que Render o Railway: usa infraestructura de Google, permite autenticar con service accounts sin archivos locales, escala automaticamente y publica una URL HTTPS estable.

## Archivos incluidos para produccion

- `requirements.txt`: dependencias Python, incluido `gunicorn`.
- `Procfile`: comando web compatible con buildpacks.
- `gunicorn.conf.py`: configuracion WSGI.
- `Dockerfile`: despliegue reproducible en Cloud Run.
- `.dockerignore`: evita copiar credenciales, caches y SQLite a la imagen.
- `.gitignore`: evita versionar secretos y artefactos locales.
- `.env.example`: plantilla de variables de entorno.

## Variables de entorno requeridas

Configura estas variables en Cloud Run:

```env
DATA_SOURCE=firestore
TESTQREATOR_USAR_EJEMPLOS=0
TESTQREATOR_SECRET_KEY=valor-largo-aleatorio
TESTQREATOR_LOGIN_USER=tu_usuario_admin
TESTQREATOR_LOGIN_PASSWORD=tu_password_admin
TESTQREATOR_SPREADSHEET=Nombre exacto del Google Sheet
TESTQREATOR_WORKSHEET=Nombre exacto de la hoja
TESTQREATOR_FIREBASE_PROJECT_ID=id-del-proyecto-firebase
```

Para credenciales, usa una de estas opciones:

- Recomendado en Cloud Run: asigna un service account con permisos sobre Firestore y Google Sheets/Drive, y no configures JSON local.
- Alternativa: define `TESTQREATOR_FIREBASE_CREDENTIALS_JSON` y `TESTQREATOR_GOOGLE_CREDENTIALS_JSON` con el contenido JSON completo del service account.
- Alternativa para consolas que manejan mejor texto plano: define `TESTQREATOR_FIREBASE_CREDENTIALS_BASE64` y `TESTQREATOR_GOOGLE_CREDENTIALS_BASE64` con el JSON codificado en Base64.

El service account debe tener acceso al Google Sheet. Comparte el archivo de Google Sheets con el email `client_email` del service account.

## Pasos para desplegar en Cloud Run

1. Sube el proyecto a GitHub excluyendo los archivos indicados en `.gitignore`.
2. En Google Cloud, selecciona el proyecto de Firebase.
3. Habilita Cloud Run, Cloud Build, Artifact Registry, Firestore API, Google Sheets API y Google Drive API.
4. Crea o selecciona un service account para la aplicacion.
5. Dale permisos suficientes para Firestore, por ejemplo `Cloud Datastore User`.
6. Comparte el Google Sheet con el email del service account.
7. En Cloud Run, crea un servicio nuevo desde el repositorio de GitHub o desde una imagen construida con el `Dockerfile`.
8. Configura el puerto del contenedor como `8080`.
9. Agrega las variables de entorno listadas arriba.
10. Permite invocaciones publicas si quieres que la URL sea accesible en Internet.
11. Despliega el servicio.
12. Abre la URL publica de Cloud Run e inicia sesion con `TESTQREATOR_LOGIN_USER` y `TESTQREATOR_LOGIN_PASSWORD`.

## Despliegue con gcloud

Desde una terminal autenticada:

```bash
gcloud run deploy testqreator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars DATA_SOURCE=firestore,TESTQREATOR_USAR_EJEMPLOS=0,TESTQREATOR_FIREBASE_PROJECT_ID=TU_PROYECTO
```

Despues agrega en la consola de Cloud Run las variables sensibles (`TESTQREATOR_SECRET_KEY`, usuario, password y credenciales si no usas ADC).

## Verificacion local con Gunicorn

Instala dependencias:

```bash
pip install -r requirements.txt
```

Ejecuta:

```bash
gunicorn main:app --config gunicorn.conf.py
```

En Windows, Gunicorn no es compatible de forma nativa. Para verificar localmente usa WSL/Linux, Docker o despliega en Cloud Run. En Windows puedes validar importacion con:

```bash
python -c "from main import app; print(app.name)"
```

## Que subir a GitHub

Sube:

- `main.py`
- `config.py`
- `google_forms.py`
- `firebase_config.py`
- `firebase_repository.py`
- `requirements.txt`
- `Procfile`
- `gunicorn.conf.py`
- `Dockerfile`
- `.dockerignore`
- `.gitignore`
- `.env.example`
- `DESPLIEGUE.md`
- carpeta `project/`
- carpeta `web/`

No subas:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `testqreator.db`
- `*.sqlite`
- `*.sqlite3`
- `credentials/`
- `credenciales.json`
- `respuestas/`
- `.env`
- archivos `.log`

## Notas de produccion

Firestore queda como fuente principal con `DATA_SOURCE=firestore`.
SQLite permanece como respaldo temporal, pero la base local no debe versionarse ni incluirse en la imagen.
Las credenciales sensibles no deben existir como archivos hardcodeados en produccion.
