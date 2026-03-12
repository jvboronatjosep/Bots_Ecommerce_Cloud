# Guía de Setup: Google Cloud desde Cero

Esta guía explica paso a paso cómo recrear toda la infraestructura del proyecto en Google Cloud Platform partiendo de cero.

**Tiempo estimado:** 45-60 minutos
**Proyecto GCP usado:** `botsecommerce`
**Región usada:** `europe-southwest1` (Madrid)

---
## Índice
1. [Requisitos previos](#1-requisitos-previos)
2. [Crear el proyecto en Google Cloud](#2-crear-el-proyecto-en-google-cloud)
3. [Activar los servicios necesarios](#3-activar-los-servicios-necesarios)
4. [Configurar Artifact Registry](#4-configurar-artifact-registry)
5. [Crear los Cloud Run services](#5-crear-los-cloud-run-services)
6. [Configurar el API Gateway](#6-configurar-el-api-gateway)
7. [Configurar Cloud Build (CI/CD)](#7-configurar-cloud-build-cicd)
8. [Configurar Cloud Scheduler](#8-configurar-cloud-scheduler)
9. [Verificar que todo funciona](#9-verificar-que-todo-funciona)
10. [Variables y valores que debes cambiar](#10-variables-y-valores-que-debes-cambiar)
---

## 1. Requisitos previos

### Instalar Google Cloud CLI (`gcloud`)

Descargar desde: https://cloud.google.com/sdk/docs/install

En Mac con Homebrew:
```bash
brew install --cask google-cloud-sdk
```

Verificar instalación:
```bash
gcloud --version
```

### Iniciar sesión
```bash
gcloud auth login
```

Esto abre el navegador para autenticarse con la cuenta de Google.

---

## 2. Crear el proyecto en Google Cloud

### 2.1 Crear el proyecto

Ir a https://console.cloud.google.com y crear un nuevo proyecto, o hacerlo por terminal:

```bash
gcloud projects create botsecommerce --name="Bots Ecommerce"
```

### 2.2 Establecer el proyecto como activo

```bash
gcloud config set project botsecommerce
```

Verificar:
```bash
gcloud config get-value project
# Debe mostrar: botsecommerce
```

### 2.3 Vincular una cuenta de facturación

Esto es obligatorio para usar Cloud Run y otros servicios de pago. Hacerlo desde la consola web:
`Facturación → Vincular cuenta de facturación`

---

## 3. Activar los servicios necesarios

Ejecutar todos estos comandos. Algunos tardan 1-2 minutos en activarse.

```bash
# Cloud Run
gcloud services enable run.googleapis.com

# Cloud Build (CI/CD)
gcloud services enable cloudbuild.googleapis.com

# Artifact Registry (registro de imágenes Docker)
gcloud services enable artifactregistry.googleapis.com

# API Gateway
gcloud services enable apigateway.googleapis.com
gcloud services enable servicemanagement.googleapis.com
gcloud services enable servicecontrol.googleapis.com

# Cloud Scheduler
gcloud services enable cloudscheduler.googleapis.com

# App Engine (necesario para Cloud Scheduler)
gcloud app create --region=europe-west
```

> **Nota:** `gcloud app create` solo hay que ejecutarlo una vez por proyecto. Si ya existe, dará error (ignorarlo).

---

## 4. Configurar Artifact Registry

Artifact Registry es donde se guardan las imágenes Docker que construye Cloud Build.

### 4.1 Crear el repositorio Docker

```bash
gcloud artifacts repositories create repo-bots \
  --repository-format=docker \
  --location=europe-southwest1 \
  --description="Imágenes Docker de los bots"
```

### 4.2 Verificar que se creó

```bash
gcloud artifacts repositories list --location=europe-southwest1
```

Debe aparecer `repo-bots` en la lista.

### 4.3 Dar permisos a Cloud Build para subir imágenes

```bash
# Obtener el número de proyecto
PROJECT_NUMBER=$(gcloud projects describe botsecommerce --format='value(projectNumber)')

# Dar permiso de escritura en Artifact Registry a la cuenta de servicio de Cloud Build
gcloud projects add-iam-policy-binding botsecommerce \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Dar permiso para desplegar en Cloud Run
gcloud projects add-iam-policy-binding botsecommerce \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Dar permiso para actuar como cuenta de servicio de Compute
gcloud iam service-accounts add-iam-policy-binding \
  ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## 5. Crear los Cloud Run services

### 5.1 Primer despliegue del backend (bot-service)

El primer despliegue hay que hacerlo manualmente con una imagen placeholder. Los siguientes los hará Cloud Build automáticamente.

```bash
# Construir la imagen localmente y subirla
cd /ruta/a/Bots_Ecommerce_Cloud

# Autenticar Docker con Artifact Registry
gcloud auth configure-docker europe-southwest1-docker.pkg.dev

# Construir la imagen
docker build -t europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1 .

# Subir la imagen
docker push europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1
```

Desplegar en Cloud Run con la configuración de producción:

```bash
gcloud run deploy bot-service \
  --image europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1 \
  --region europe-southwest1 \
  --cpu 4 \
  --memory 8Gi \
  --timeout 3600 \
  --no-cpu-throttling \
  --min-instances 1 \
  --allow-unauthenticated \
  --set-env-vars DEVICE_TOKEN=TU_TOKEN_SECRETO_AQUI \
  --project botsecommerce
```

> **DEVICE_TOKEN:** genera un token aleatorio largo. Por ejemplo:
> `python3 -c "import secrets; print(secrets.token_hex(32))"`

Anotar la URL que aparece al final, tiene el formato:
`https://bot-service-XXXXXXXXXX.europe-southwest1.run.app`

### 5.2 Ajustar el startup probe para que no reinicie durante ejecuciones largas

```bash
# Exportar la configuración actual
gcloud run services describe bot-service \
  --region europe-southwest1 \
  --format export > bot-service.yaml
```

Editar `bot-service.yaml` y localizar la sección `startupProbe`. Cambiar los valores:

```yaml
startupProbe:
  failureThreshold: 3      # era 1, aumentar a 3
  periodSeconds: 240       # periodo de 4 minutos
  tcpSocket:
    port: 8080
  timeoutSeconds: 240      # timeout de 4 minutos
```

Aplicar los cambios:
```bash
gcloud run services replace bot-service.yaml --region europe-southwest1
```

### 5.3 Primer despliegue del frontend (frontend-service)

```bash
cd /ruta/a/Bots_Ecommerce_Frontend

# Construir y subir la imagen del frontend
docker build -t europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1 .
docker push europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1

# Desplegar en Cloud Run (recursos mínimos, solo sirve HTML estático)
gcloud run deploy frontend-service \
  --image europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1 \
  --region europe-southwest1 \
  --cpu 1 \
  --memory 256Mi \
  --allow-unauthenticated \
  --project botsecommerce
```

Anotar la URL del frontend:
`https://frontend-service-XXXXXXXXXX.europe-southwest1.run.app`

### 5.4 Verificar los servicios

```bash
gcloud run services list --region europe-southwest1
```

Deben aparecer `bot-service` y `frontend-service`.

---

## 6. Configurar el API Gateway

### 6.1 Crear la API

```bash
gcloud api-gateway apis create bots-api \
  --project botsecommerce
```

### 6.2 Preparar el archivo openapi.yaml

El archivo `openapi.yaml` en la raíz del repositorio backend define las rutas del gateway. Antes de crear la configuración, **actualizar las URLs** del backend y frontend con las URLs reales de Cloud Run obtenidas en el paso 5.

En `openapi.yaml`, cambiar estas líneas con las URLs reales:
```yaml
# Línea del frontend (ruta /)
address: https://frontend-service-TU_ID.europe-southwest1.run.app/

# Líneas del backend (rutas /api/* y /activate/*)
address: https://bot-service-TU_ID.europe-southwest1.run.app/
```

También cambiar el `host`:
```yaml
host: bots-gateway-prod-TU_HASH.ew.gateway.dev
```

> Este host lo sabrás después de crear el gateway (paso 6.4). Puedes dejarlo como placeholder de momento.

### 6.3 Crear la configuración del gateway

```bash
gcloud api-gateway api-configs create bots-config-v1 \
  --api bots-api \
  --openapi-spec openapi.yaml \
  --project botsecommerce
```

Esperar a que termine (puede tardar 1-2 minutos).

### 6.4 Crear el gateway

```bash
gcloud api-gateway gateways create bots-gateway-prod \
  --api bots-api \
  --api-config bots-config-v1 \
  --location europe-west1 \
  --project botsecommerce
```

> **Importante:** el gateway se crea en `europe-west1`, no en `europe-southwest1`. Es un requisito de API Gateway.

Esperar a que termine. Al final aparece la URL pública:
```
defaultHostname: bots-gateway-prod-XXXXXXXX.ew.gateway.dev
```

Esa es la URL pública del proyecto.

### 6.5 Actualizar el gateway cuando cambie openapi.yaml

Cada vez que se modifique `openapi.yaml`, hay que crear una nueva versión de configuración y actualizar el gateway:

```bash
# Crear nueva versión de configuración (incrementar el número)
gcloud api-gateway api-configs create bots-config-v2 \
  --api bots-api \
  --openapi-spec openapi.yaml \
  --project botsecommerce

# Actualizar el gateway para usar la nueva configuración
gcloud api-gateway gateways update bots-gateway-prod \
  --api bots-api \
  --api-config bots-config-v2 \
  --location europe-west1 \
  --project botsecommerce
```

---

## 7. Configurar Cloud Build (CI/CD)

Cloud Build conecta GitHub con Cloud Run: cada push a `main` construye y despliega automáticamente.

### 7.1 Conectar repositorios de GitHub

Esto se hace desde la consola web (no hay comando gcloud para ello):

1. Ir a **Cloud Build → Repositorios → Conectar repositorio**
2. Seleccionar GitHub como proveedor
3. Autenticarse con GitHub y dar permisos a Google Cloud Build
4. Seleccionar el repositorio `Bots_Ecommerce_Cloud`
5. Repetir para `Bots_Ecommerce_Frontend`

### 7.2 Crear el trigger para el backend

```bash
gcloud builds triggers create github \
  --repo-name=Bots_Ecommerce_Cloud \
  --repo-owner=jvboronatjosep \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --substitutions _DEVICE_TOKEN=TU_TOKEN_SECRETO_AQUI \
  --region global \
  --project botsecommerce
```

> Sustituir `jvboronatjosep` por el usuario de GitHub dueño del repositorio backend.
> Sustituir `TU_TOKEN_SECRETO_AQUI` por el mismo token usado en Cloud Run.

### 7.3 Crear el trigger para el frontend

```bash
gcloud builds triggers create github \
  --repo-name=Bots_Ecommerce_Frontend \
  --repo-owner=CarlosMarNav \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --region global \
  --project botsecommerce
```

### 7.4 Verificar los triggers

```bash
gcloud builds triggers list --project botsecommerce
```

Deben aparecer los dos triggers.

### 7.5 Probar que el CI/CD funciona

Hacer un pequeño cambio en cualquier fichero y hacer push a `main`:

```bash
git add .
git commit -m "test: verificar CI/CD"
git push origin main
```

Ver el progreso en tiempo real:
```bash
gcloud builds list --limit=5 --project botsecommerce
```

O en la consola web: **Cloud Build → Historial de compilaciones**

### Estructura del cloudbuild.yaml del backend

El archivo `cloudbuild.yaml` en el repositorio backend hace tres cosas:

```yaml
steps:
  # 1. Construir la imagen Docker
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'europe-southwest1-docker.pkg.dev/$PROJECT_ID/repo-bots/bot-app:$SHORT_SHA', '.']

  # 2. Subir la imagen a Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'europe-southwest1-docker.pkg.dev/$PROJECT_ID/repo-bots/bot-app:$SHORT_SHA']

  # 3. Desplegar en Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'bot-service'
      - '--image'
      - 'europe-southwest1-docker.pkg.dev/$PROJECT_ID/repo-bots/bot-app:$SHORT_SHA'
      - '--region'
      - 'europe-southwest1'
      - '--memory'
      - '4Gi'
      - '--cpu'
      - '2'
      - '--timeout'
      - '3600'
      - '--no-cpu-throttling'
      - '--allow-unauthenticated'
      - '--update-env-vars'
      - 'DEVICE_TOKEN=$_DEVICE_TOKEN'

images:
  - 'europe-southwest1-docker.pkg.dev/$PROJECT_ID/repo-bots/bot-app:$SHORT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
```

> `$PROJECT_ID` y `$SHORT_SHA` son variables automáticas de Cloud Build.
> `$_DEVICE_TOKEN` es la variable personalizada definida en el trigger.

---

## 8. Configurar Cloud Scheduler

Cloud Scheduler ejecuta automáticamente todos los bots cada día a las 06:00.

### 8.1 Crear el job

```bash
gcloud scheduler jobs create http diario-bots-0600 \
  --location europe-southwest1 \
  --schedule "0 6 * * *" \
  --uri "https://bots-gateway-prod-TU_HASH.ew.gateway.dev/api/auto-run-all" \
  --http-method POST \
  --headers "X-CloudScheduler=true" \
  --time-zone "Europe/Madrid" \
  --project botsecommerce
```

> Sustituir `TU_HASH` por el hash real del gateway obtenido en el paso 6.4.

### 8.2 Probar el job manualmente

Para verificar que el scheduler puede llamar al backend correctamente:

```bash
gcloud scheduler jobs run diario-bots-0600 \
  --location europe-southwest1 \
  --project botsecommerce
```

Después comprobar los logs del bot-service para ver si recibió la petición:

```bash
gcloud run services logs read bot-service \
  --region europe-southwest1 \
  --limit 20 \
  --project botsecommerce
```

### 8.3 Ver el estado del job

```bash
gcloud scheduler jobs describe diario-bots-0600 \
  --location europe-southwest1 \
  --project botsecommerce
```

---

## 9. Verificar que todo funciona

### 9.1 Comprobar todos los servicios de un vistazo

```bash
# Cloud Run
gcloud run services list --region europe-southwest1 --project botsecommerce

# API Gateway
gcloud api-gateway gateways list --location europe-west1 --project botsecommerce

# Cloud Build triggers
gcloud builds triggers list --project botsecommerce

# Scheduler
gcloud scheduler jobs list --location europe-southwest1 --project botsecommerce

# Artifact Registry
gcloud artifacts repositories list --location europe-southwest1 --project botsecommerce
```

### 9.2 Probar el gateway con curl

```bash
# Debe devolver el HTML del dashboard (200 OK)
curl -I https://bots-gateway-prod-TU_HASH.ew.gateway.dev/

# Debe devolver la lista de bots en JSON (401 sin cookie, correcto)
curl https://bots-gateway-prod-TU_HASH.ew.gateway.dev/api/bots
```

### 9.3 Activar un dispositivo

Abrir en el navegador:
```
https://bots-gateway-prod-TU_HASH.ew.gateway.dev/activate/TU_DEVICE_TOKEN
```

Si funciona, redirige al dashboard y establece la cookie de autenticación.

---

## 10. Variables y valores que debes cambiar

Al recrear el proyecto desde cero, estos son todos los valores que son específicos del entorno y que hay que sustituir:

| Variable | Dónde cambiarla | Descripción |
|----------|----------------|-------------|
| `botsecommerce` | Todos los comandos gcloud | ID del proyecto GCP |
| `europe-southwest1` | Comandos Cloud Run y Artifact Registry | Región de los servicios |
| `TU_TOKEN_SECRETO_AQUI` | Trigger de Cloud Build y comando `gcloud run deploy` | Token de autenticación del dashboard |
| URL de `bot-service` | `openapi.yaml` (secciones de backend) | URL real de Cloud Run del backend |
| URL de `frontend-service` | `openapi.yaml` (sección del frontend) | URL real de Cloud Run del frontend |
| `TU_HASH` | Cloud Scheduler (URI) y `openapi.yaml` (host) | Hash del API Gateway (se genera automáticamente) |
| `jvboronatjosep` | Trigger de Cloud Build backend | Dueño del repositorio GitHub del backend |
| `CarlosMarNav` | Trigger de Cloud Build frontend | Dueño del repositorio GitHub del frontend |

### Generar un DEVICE_TOKEN seguro

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Ejemplo de output: `9f3b7c1e5a4d8f6b2c1e9a7d3f8b6c4a2d1e7f9c3b5a8d6e1f2c4b7a9d3e6f1`

---

## Resumen rápido (comandos en orden)

```bash
# 1. Configurar proyecto
gcloud config set project botsecommerce

# 2. Activar servicios
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com apigateway.googleapis.com \
  servicemanagement.googleapis.com servicecontrol.googleapis.com \
  cloudscheduler.googleapis.com

# 3. Artifact Registry
gcloud artifacts repositories create repo-bots \
  --repository-format=docker --location=europe-southwest1

# 4. Dar permisos a Cloud Build
PROJECT_NUMBER=$(gcloud projects describe botsecommerce --format='value(projectNumber)')
gcloud projects add-iam-policy-binding botsecommerce \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding botsecommerce \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud iam service-accounts add-iam-policy-binding \
  ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 5. Desplegar backend (primer deploy manual)
gcloud auth configure-docker europe-southwest1-docker.pkg.dev
docker build -t europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1 .
docker push europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1
gcloud run deploy bot-service \
  --image europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:v1 \
  --region europe-southwest1 --cpu 4 --memory 8Gi --timeout 3600 \
  --no-cpu-throttling --min-instances 1 --allow-unauthenticated \
  --set-env-vars DEVICE_TOKEN=TU_TOKEN

# 6. Desplegar frontend (primer deploy manual)
docker build -t europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1 .
docker push europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1
gcloud run deploy frontend-service \
  --image europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:v1 \
  --region europe-southwest1 --cpu 1 --memory 256Mi --allow-unauthenticated

# 7. API Gateway
gcloud api-gateway apis create bots-api
gcloud api-gateway api-configs create bots-config-v1 \
  --api bots-api --openapi-spec openapi.yaml
gcloud api-gateway gateways create bots-gateway-prod \
  --api bots-api --api-config bots-config-v1 --location europe-west1

# 8. Cloud Build triggers (desde consola web: conectar repos de GitHub primero)
gcloud builds triggers create github \
  --repo-name=Bots_Ecommerce_Cloud --repo-owner=jvboronatjosep \
  --branch-pattern=^main$ --build-config=cloudbuild.yaml \
  --substitutions _DEVICE_TOKEN=TU_TOKEN
gcloud builds triggers create github \
  --repo-name=Bots_Ecommerce_Frontend --repo-owner=CarlosMarNav \
  --branch-pattern=^main$ --build-config=cloudbuild.yaml

# 9. Cloud Scheduler
gcloud scheduler jobs create http diario-bots-0600 \
  --location europe-southwest1 \
  --schedule "0 6 * * *" \
  --uri "https://bots-gateway-prod-TU_HASH.ew.gateway.dev/api/auto-run-all" \
  --http-method POST --headers "X-CloudScheduler=true" \
  --time-zone "Europe/Madrid"
```
