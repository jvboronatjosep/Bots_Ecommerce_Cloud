# Documentación del Proyecto: Plataforma de Bots de Ecommerce en la Nube

**Empresa:** SendingBay
**Proyecto:** Bot Auto Pedidos — Bots_Ecommerce_Cloud
**Repositorio backend:** https://github.com/jvboronatjosep/Bots_Ecommerce_Cloud
**Repositorio frontend:** https://github.com/CarlosMarNav/Bots_Ecommerce_Frontend
**URL pública:** https://bots-gateway-prod-83hfw8tp.ew.gateway.dev/

---

## Índice

1. [Descripción general del proyecto](#1-descripción-general-del-proyecto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Estructura de repositorios y ficheros](#3-estructura-de-repositorios-y-ficheros)
4. [Componentes principales](#4-componentes-principales)
   - 4.1 [Servidor Flask (backend)](#41-servidor-flask-backend)
   - 4.2 [Dashboard web (frontend)](#42-dashboard-web-frontend)
   - 4.3 [Bot de Shopify](#43-bot-de-shopify)
5. [Infraestructura en Google Cloud](#5-infraestructura-en-google-cloud)
   - 5.1 [Cloud Run — bot-service](#51-cloud-run--bot-service)
   - 5.2 [Cloud Run — frontend-service](#52-cloud-run--frontend-service)
   - 5.3 [API Gateway](#53-api-gateway)
   - 5.4 [Cloud Build (CI/CD)](#54-cloud-build-cicd)
   - 5.5 [Cloud Scheduler](#55-cloud-scheduler)
   - 5.6 [Artifact Registry](#56-artifact-registry)
6. [Seguridad y autenticación](#6-seguridad-y-autenticación)
7. [Problemas encontrados y soluciones aplicadas](#7-problemas-encontrados-y-soluciones-aplicadas)
8. [Flujo completo de una ejecución](#8-flujo-completo-de-una-ejecución)
9. [Decisiones de diseño y evolución del proyecto](#9-decisiones-de-diseño-y-evolución-del-proyecto)
10. [URLs y recursos de producción](#10-urls-y-recursos-de-producción)

---

## 1. Descripción general del proyecto

El proyecto consiste en una **plataforma cloud** que automatiza la generación de pedidos de prueba en tiendas de ecommerce. Permite lanzar bots de automatización de navegador sobre cuatro plataformas distintas (Shopify, PrestaShop 8, PrestaShop 1.7 y WooCommerce) desde un panel de control web accesible desde cualquier dispositivo.

**Objetivo principal:** generar pedidos de prueba en tiendas de ecommerce de forma automática y programada (6am), sin intervención manual, con visibilidad en tiempo real del progreso de cada ejecución.

**Tecnologías clave:**
- Python (Flask, Playwright, Camoufox, Faker)
- Google Cloud Platform (Cloud Run, API Gateway, Cloud Build, Cloud Scheduler, Artifact Registry)
- Docker y nginx
- GitHub (dos repositorios independientes, CI/CD automático)

---

## 2. Arquitectura del sistema

```
Usuario (navegador)
        │
        ▼
┌─────────────────────────────────────────┐
│   Google API Gateway                    │
│   bots-gateway-prod-83hfw8tp.ew.        │
│   gateway.dev                           │
│                                         │
│   GET /          → frontend-service     │
│   GET/POST /api/* → bot-service         │
│   GET /activate/* → bot-service         │
└──────────┬───────────────┬──────────────┘
           │               │
           ▼               ▼
┌──────────────────┐  ┌────────────────────────────────┐
│ frontend-service │  │ bot-service                    │
│ (Cloud Run)      │  │ (Cloud Run)                    │
│                  │  │                                │
│ nginx:alpine     │  │ Flask + Gunicorn               │
│ 1 CPU / 256Mi    │  │ 4 CPU / 8 GB RAM               │
│ Sirve index.html │  │ 1 worker / 8 threads           │
└──────────────────┘  │ Playwright + Camoufox bots     │
                      └────────────────────────────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      │     Cloud Scheduler        │
                      │  (diario a las 06:00)      │
                      │  POST /api/auto-run-all    │
                      └────────────────────────────┘

CI/CD:
GitHub push → Cloud Build trigger → Docker build → Artifact Registry → Cloud Run deploy
```

### Flujo de routing en el API Gateway

| Ruta | Destino |
|------|---------|
| `GET /` | frontend-service (nginx sirve index.html) |
| `GET/POST /api/{p1}` | bot-service |
| `GET/POST /api/{p1}/{p2}` | bot-service |
| `GET/POST /api/{p1}/{p2}/{p3}` | bot-service |
| `GET/POST /api/{p1}/{p2}/{p3}/{p4}` | bot-service |
| `GET /activate/{key}` | bot-service |

---

## 3. Estructura de repositorios y ficheros

### Repositorio backend: `Bots_Ecommerce_Cloud`

```
Bots_Ecommerce_Cloud/
├── server.py                          # Servidor Flask principal
├── Dockerfile                         # Imagen Docker con Playwright/Camoufox
├── cloudbuild.yaml                    # Pipeline CI/CD para bot-service
├── bot-service.yaml                   # Configuración Cloud Run (knative)
├── openapi.yaml                       # Definición del API Gateway (Swagger 2.0)
├── requirements.txt
└── bots/
    ├── BotComprasShopify-main/
    │   ├── main.py                    # Punto de entrada del bot
    │   ├── config/settings.py         # Configuración (BotSettings via pydantic)
    │   ├── core/
    │   │   ├── browser.py             # Gestión del navegador Camoufox
    │   │   ├── store_navigator.py     # Navegación por la tienda
    │   │   ├── cart_manager.py        # Gestión del carrito
    │   │   ├── checkout_handler.py    # Proceso de checkout completo
    │   │   └── payment_handler.py     # Relleno de campos de pago (iframes)
    │   ├── data/
    │   │   ├── fake_customer.py       # Generador de clientes ficticios (Faker)
    │   │   └── addresses.py           # Base de datos de direcciones españolas
    │   └── utils/
    │       ├── selectors.py           # Selectores CSS/XPath centralizados
    │       ├── timing.py              # Sistema de delays aleatorios por pedido
    │       ├── logger.py              # Logger con Rich
    │       └── retry.py               # Lógica de reintentos
    ├── Prestashop_8_bot/
    ├── Prestashop1.7_bot/
    └── woocommerce_bot/
```

### Repositorio frontend: `Bots_Ecommerce_Frontend`

```
Bots_Ecommerce_Frontend/
├── index.html          # Dashboard SPA (HTML + JS vanilla + CSS)
├── nginx.conf          # Configuración nginx (puerto 8080)
├── Dockerfile          # FROM nginx:alpine
└── cloudbuild.yaml     # Pipeline CI/CD para frontend-service
```

---

## 4. Componentes principales

### 4.1 Servidor Flask (backend)

**Fichero:** `server.py`

El servidor Flask actúa como orquestador de los bots. Sus responsabilidades son:

- Recibir peticiones del dashboard para lanzar bots
- Ejecutar cada bot como un **subproceso** independiente (`subprocess.Popen`)
- Capturar la salida del subproceso en tiempo real con un hilo (`threading.Thread`)
- Almacenar los logs en memoria (`runs` dict) para que el frontend los consulte
- Exponer una API REST para el control del dashboard

**Bots registrados:**

| ID | Nombre | Ruta |
|----|--------|------|
| `shopify` | Shopify Bot | `bots/BotComprasShopify-main` |
| `prestashop8` | PrestaShop 8 Bot | `bots/Prestashop_8_bot` |
| `prestashop17` | PrestaShop 1.7 Bot | `bots/Prestashop1.7_bot` |
| `woocommerce` | WooCommerce Bot | `bots/woocommerce_bot` |

**Endpoints de la API:**

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Sirve index.html (solo desarrollo local) |
| `GET` | `/activate/<key>` | Activa el dispositivo y establece cookie de auth |
| `POST` | `/api/auto-run-all` | Lanza todos los bots (usado por Cloud Scheduler) |
| `POST` | `/api/run` | Lanza un bot concreto con parámetros |
| `GET` | `/api/bots` | Lista los bots disponibles |
| `GET` | `/api/runs` | Lista todas las ejecuciones en memoria |
| `GET` | `/api/runs/<run_id>` | Detalle de una ejecución |
| `GET` | `/api/runs/<run_id>/logs?offset=N` | Logs de una ejecución desde offset N |
| `POST` | `/api/run/<run_id>/stop` | Detiene un proceso en ejecución |

**Servidor WSGI:** Gunicorn con `--workers 1 --threads 8 --timeout 0`
La configuración de 1 worker es intencional: todos los threads comparten el mismo espacio de memoria donde se guardan los logs y el estado de las ejecuciones.

### 4.2 Dashboard web (frontend)

**Fichero:** `index.html` (repositorio `Bots_Ecommerce_Frontend`)

SPA desarrollada en HTML + CSS + JavaScript vanilla. Funcionalidades:

- Visualización de los bots disponibles con estado (disponible/no disponible)
- Lanzamiento manual de bots con configuración (número de pedidos, modo headless)
- Vista de ejecuciones activas e historial
- **Consola de logs en tiempo real:** hace polling a `/api/runs/<run_id>/logs?offset=N` cada 800ms, incrementando el offset para solo pedir los logs nuevos
- Indicadores de estado por ejecución (running, completed, failed)

**Mecanismo de polling de logs:**

```javascript
// Petición incremental: solo pide logs nuevos desde el último offset
const logData = await fetch(`/api/runs/${runId}/logs?offset=${logOffset}`);
logOffset += logData.logs ? logData.logs.length : 0;
// logOffset se incrementa con los logs recibidos, no con un campo "total" inexistente
```

### 4.3 Bot de Shopify

El bot está estructurado en módulos con responsabilidades claras:

**`BrowserManager` (browser.py)**
Gestiona el navegador usando **Camoufox**, una variante de Firefox diseñada para evadir detección de bots. Cada pedido se ejecuta en un contexto de navegador aislado con cookies compartidas (para mantener el bypass de la página de contraseña).

**`StoreNavigator` (store_navigator.py)**
- Detecta y bypasea la página de contraseña de la tienda enviando un POST vía JavaScript (`fetch`) para evitar el refresco de página
- Obtiene el catálogo de productos via la API JSON de Shopify (`/products.json?limit=250`)
- Navega a páginas de producto individuales

**`CartManager` (cart_manager.py)**
- Añade productos al carrito (botón `button[name='add']`)
- Procede al checkout: primero intenta el botón del carrito lateral (`cart-drawer`), con fallback a la página `/cart`

**`CheckoutHandler` (checkout_handler.py)**
Gestiona los 4 pasos del checkout de Shopify:
1. **Datos personales:** email del cliente
2. **Dirección de envío:** nombre, apellidos, dirección, ciudad, provincia, CP, país
3. **Método de envío:** auto-seleccionado por la tienda
4. **Pago:** datos de tarjeta en los iframes de Shopify (Bogus Gateway para pruebas)

**`CustomerGenerator` (fake_customer.py)**
Genera clientes ficticios realistas usando la librería `Faker` en locale español:
- Nombre y apellidos aleatorios españoles
- Email con formato `bottest.{nombre}.{apellido}.{hex6}@example.com`
- Dirección aleatoria de una base de datos de ciudades y códigos postales españoles reales
- Número de tarjeta `"1"` (Bogus Gateway de Shopify = pago de prueba que siempre aprueba)

**`OrderDelays` (timing.py)**
Sistema de delays aleatorios para simular comportamiento humano. Distribuye un presupuesto total aleatorio de entre 10 y 20 segundos entre todos los puntos del flujo (20 puntos: después de cargar la página, antes de teclear el email, entre campos, antes de pagar, etc.), generando un perfil de timing único por pedido.

**Selectores CSS centralizados (selectors.py)**

```python
EMAIL_INPUT = "input#email, input[type='email'], input[autocomplete='email'], input[name='email']"
```
Se usan selectores múltiples separados por coma para mayor compatibilidad con distintas versiones del checkout de Shopify.

---

## 5. Infraestructura en Google Cloud

**Proyecto GCP:** `botsecommerce`
**Región:** `europe-southwest1` (Madrid)

### 5.1 Cloud Run — bot-service

Servicio que ejecuta el servidor Flask con los bots.

| Parámetro | Valor |
|-----------|-------|
| URL | `https://bot-service-634498283437.europe-southwest1.run.app` |
| CPU | 4 vCPU |
| RAM | 8 GB |
| CPU throttling | Desactivado (la CPU siempre disponible, necesario para los bots) |
| Timeout | 3600 s (1 hora, para ejecuciones largas de bots) |
| Instancias mínimas | 1 (siempre activo, evita cold start) |
| Instancias máximas | 100 |
| Concurrencia | 80 peticiones por instancia |
| Ingress | `all` (acepta tráfico externo + desde el Gateway) |
| Startup probe | TCP socket, failureThreshold: 3, period: 240s |
| Variable de entorno | `DEVICE_TOKEN` (token de autenticación de dispositivos) |

**Dockerfile:**
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn
RUN playwright install chromium firefox
RUN python -m camoufox fetch
COPY . .
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 server:app
```

Se usa la imagen oficial de Microsoft para Playwright porque incluye todas las dependencias del sistema operativo necesarias para ejecutar navegadores Chrome y Firefox dentro de un contenedor Linux.

### 5.2 Cloud Run — frontend-service

Servicio ligero que sirve el dashboard HTML estático.

| Parámetro | Valor |
|-----------|-------|
| URL | `https://frontend-service-634498283437.europe-southwest1.run.app` |
| CPU | 1 vCPU |
| RAM | 256 MB |
| Servidor | nginx:alpine |
| Puerto | 8080 |

**Dockerfile:**
```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf:**
```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 5.3 API Gateway

La puerta de enlace es el único punto de entrada público. Todo el tráfico pasa por ella.

| Parámetro | Valor |
|-----------|-------|
| ID del gateway | `bots-gateway-prod` |
| URL pública | `https://bots-gateway-prod-83hfw8tp.ew.gateway.dev/` |
| Región | `europe-west1` |
| Formato de spec | Swagger 2.0 (OpenAPI 2.0) |
| Fichero de configuración | `openapi.yaml` (versión 1.2.0) |

**Decisión de diseño — rutas explícitas por niveles:**
Google API Gateway con Swagger 2.0 no soporta el patrón `/{proxy+}`. Por ello, se definieron rutas explícitas para hasta 4 niveles de profundidad de path (`/{p1}`, `/{p1}/{p2}`, `/{p1}/{p2}/{p3}`, `/{p1}/{p2}/{p3}/{p4}`), cubriendo todos los endpoints de la API:

- `/api/bots` → 2 niveles
- `/api/runs` → 2 niveles
- `/api/runs/{run_id}` → 3 niveles
- `/api/runs/{run_id}/logs` → 4 niveles ← requería nivel 4, se añadió específicamente
- `/api/run/{run_id}/stop` → 4 niveles

### 5.4 Cloud Build (CI/CD)

**Backend (`cloudbuild.yaml` en `Bots_Ecommerce_Cloud`):**

Trigger conectado al repositorio `github.com/jvboronatjosep/Bots_Ecommerce_Cloud`, rama `main`.

```
Push a main
  → Build imagen Docker: europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/bot-app:{SHORT_SHA}
  → Push a Artifact Registry
  → Deploy en bot-service (Cloud Run, europe-southwest1, 4Gi RAM, 2 CPU en yaml / 4 CPU en runtime)
```

Variables sustituidas en tiempo de build: `$_DEVICE_TOKEN` (token de autenticación).

**Frontend (`cloudbuild.yaml` en `Bots_Ecommerce_Frontend`):**

Trigger conectado al repositorio `github.com/CarlosMarNav/Bots_Ecommerce_Frontend`, rama `main`.

```
Push a main
  → Build imagen Docker: europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/frontend-app:{SHORT_SHA}
  → Push a Artifact Registry
  → Deploy en frontend-service (Cloud Run, europe-southwest1, 256Mi RAM, 1 CPU)
```

### 5.5 Cloud Scheduler

**Job:** `diario-bots-0600`
**Horario:** todos los días a las 06:00 (zona horaria Europe/Madrid)
**URL:** `https://bots-gateway-prod-83hfw8tp.ew.gateway.dev/api/auto-run-all`
**Método:** `POST`
**Header:** `X-CloudScheduler: true`

El header `X-CloudScheduler: true` es la clave que bypasea la autenticación por cookie en el servidor Flask. El middleware `check_device_auth` tiene una excepción explícita para este header:

```python
if request.headers.get('X-CloudScheduler') == 'true':
    return None  # Bypass auth
```

La ruta `/api/auto-run-all` también tiene su propia validación adicional para aceptar este header sin cookie.

### 5.6 Artifact Registry

**Repositorio:** `europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/`

| Imagen | Uso |
|--------|-----|
| `bot-app:{SHORT_SHA}` | bot-service (backend + bots) |
| `frontend-app:{SHORT_SHA}` | frontend-service (nginx + dashboard) |

---

## 6. Seguridad y autenticación

### Sistema de autenticación por cookie

El acceso al dashboard está protegido por un sistema de cookie de dispositivo:

1. El administrador accede a `/activate/{DEVICE_TOKEN}` por primera vez
2. El servidor verifica que el token coincide con la variable de entorno `DEVICE_TOKEN`
3. Se establece una cookie `device_auth` con expiración de 1 año
4. Todas las peticiones posteriores incluyen automáticamente esta cookie

```python
@app.before_request
def check_device_auth():
    # Rutas excluidas de auth
    if request.path.startswith('/activate/') or \
       request.path.startswith('/static/') or \
       request.path == '/api/auto-run-all':
        return None
    # Bypass para Cloud Scheduler
    if request.headers.get('X-CloudScheduler') == 'true':
        return None
    # Verificar cookie
    auth_cookie = request.cookies.get('device_auth')
    if auth_cookie != DEVICE_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401
```

### Ingress de Cloud Run

Se configuró `run.googleapis.com/ingress: all` en bot-service para que el API Gateway pueda enrutar tráfico hacia él. La alternativa `internal-and-cloud-load-balancing` bloqueaba las peticiones del gateway.

---

## 7. Problemas encontrados y soluciones aplicadas

### 7.1 API Gateway — `{proxy+}` no soportado en Swagger 2.0

**Problema:** El fichero `openapi.yaml` usaba `/{proxy+}` (sintaxis de AWS API Gateway) para capturar cualquier ruta. Google API Gateway con Swagger 2.0 rechaza este patrón con error `INVALID_ARGUMENT`.

**Solución:** Definir rutas explícitas con parámetros de path para cada nivel de profundidad:
```yaml
/api/{p1}: ...
/api/{p1}/{p2}: ...
/api/{p1}/{p2}/{p3}: ...
/api/{p1}/{p2}/{p3}/{p4}: ...
```

---

### 7.2 Logs no aparecían en el dashboard (404 en `/api/runs/{id}/logs`)

**Problema:** La ruta `/api/runs/{run_id}/logs` tiene 4 segmentos de path. El `openapi.yaml` solo tenía definidas rutas hasta 3 niveles, por lo que el gateway devolvía 404 antes de llegar al backend.

**Solución:** Añadir el nivel `/{p1}/{p2}/{p3}/{p4}` a la definición del gateway.

---

### 7.3 Logs duplicados (aparecían muchas veces en la consola)

**Problema:** En el JavaScript del dashboard, la variable `logOffset` se actualizaba con `logData.total`:
```javascript
logOffset = logData.total;  // "total" no existe en la respuesta → undefined
```
Al ser `undefined`, en la siguiente petición se enviaba `?offset=undefined`. El servidor Python lanzaba `ValueError: invalid literal for int() with base 10: 'undefined'` y devolvía todos los logs desde el inicio. Cada tick del polling añadía TODOS los logs de nuevo.

**Soluciones aplicadas (dos capas):**

Backend (`server.py`) — tolerancia al parámetro inválido:
```python
try:
    offset = int(request.args.get('offset', 0))
except (ValueError, TypeError):
    offset = 0
```

Frontend (`index.html`) — corrección del incremento del offset:
```javascript
logOffset += logData.logs ? logData.logs.length : 0;
// Antes: logOffset = logData.total  (campo inexistente)
```

---

### 7.4 Cloud Scheduler recibía 403 al llamar directamente a Cloud Run

**Problema:** El job de Cloud Scheduler llamaba directamente a la URL de Cloud Run (`bot-service-XXX.run.app`). Cloud Run devolvía 403 porque requería autenticación de Google (IAM) para llamadas directas.

**Solución:** Actualizar el URI del scheduler para que apunte a la URL del API Gateway en su lugar. El Gateway actúa como intermediario autorizado, y el backend acepta el header `X-CloudScheduler: true` como bypass de autenticación.

---

### 7.5 Instancias Cloud Run se reiniciaban durante la ejecución de bots

**Problema:** Los bots de navegador son procesos intensivos en CPU y RAM. Con la configuración inicial (2 CPU, 4 GB RAM, `failureThreshold: 1`), el startup probe fallaba durante la ejecución porque el proceso tardaba en responder, y Cloud Run reiniciaba el contenedor.

**Solución:** Aumentar los recursos y la tolerancia del probe:

| Parámetro | Antes | Después |
|-----------|-------|---------|
| CPU | 2 | 4 |
| RAM | 4 Gi | 8 Gi |
| `failureThreshold` | 1 | 3 |
| `periodSeconds` | — | 240 |
| `timeoutSeconds` | — | 240 |
| CPU throttling | activado | desactivado |

---

### 7.6 Separación de frontend y backend en dos servicios Cloud Run
**Motivación:** Reducir costes. El bot-service necesita 4 CPU y 8 GB para ejecutar navegadores. Antes, también servía el HTML estático con esos mismos recursos caros. Separando el frontend a un servicio independiente de 1 CPU / 256 MB, el coste del frontend se reduce drásticamente.

**Cambios realizados:**
1. Eliminado el código de servicio de ficheros estáticos de `server.py` (ruta `GET /` y `send_from_directory`)
2. Eliminada la carpeta `static/` del repositorio backend
3. Creado nuevo repositorio `Bots_Ecommerce_Frontend` con:
   - `index.html` (el mismo dashboard)
   - `nginx.conf` (servidor nginx en puerto 8080)
   - `Dockerfile` (FROM nginx:alpine)
   - `cloudbuild.yaml` (pipeline CI/CD para `frontend-service`)
4. Actualizado `openapi.yaml` para que `GET /` apunte a `frontend-service` y `GET/POST /api/*` apunte a `bot-service`
5. Añadida ruta `GET /` en `server.py` para desarrollo local (sirve el `index.html` del repositorio frontend hermano)

---

### 7.7 Checkout de Shopify — timeout buscando el campo email

**Problema:** El bot hacía click en el botón de checkout del carrito y acto seguido intentaba encontrar el campo `input#email`. El error era:
```
Locator.wait_for: Timeout 20000ms exceeded.
waiting for locator("input#email, ...").first to be visible
```

**Causa raíz:** Shopify realiza redirecciones del lado del cliente tras el click en checkout. El evento `domcontentloaded` se dispara en una página intermedia de transición, antes de que el formulario de checkout haya renderizado. El bot buscaba el email en esa página intermedia donde el campo no existe.

**Solución aplicada en `checkout_handler.py`:**

```python
async def _fill_contact_info(self):
    # Esperar a que Shopify navegue a la URL real del checkout
    try:
        await self.page.wait_for_url("**/checkouts/**", timeout=20000)
    except Exception:
        logger.warning("wait_for_url timed out, url: %s", self.page.url)
    # Esperar a que la red esté inactiva (página completamente cargada)
    await self.page.wait_for_load_state("networkidle", timeout=15000)
    await asyncio.sleep(1.5)
    logger.warning("Checkout page url before email fill: %s", self.page.url)
    email_input = self.page.locator(Selectors.EMAIL_INPUT).first
    await email_input.wait_for(state="visible", timeout=20000)
```

El selector de email también se amplió para cubrir distintas versiones del checkout:
```python
EMAIL_INPUT = "input#email, input[type='email'], input[autocomplete='email'], input[name='email']"
```

---

## 8. Flujo completo de una ejecución

### Ejecución manual desde el dashboard
1. El usuario abre `https://bots-gateway-prod-83hfw8tp.ew.gateway.dev/`
2. El Gateway enruta a `frontend-service`, que devuelve `index.html`
3. El usuario pulsa "Ejecutar" en un bot → el JS hace `POST /api/run` con `{bot_id, orders, headless}`
4. El Gateway enruta la petición a `bot-service`
5. Flask crea un `run_id` único, lanza el bot como subproceso y devuelve `{run_id}`
6. El dashboard hace polling a `/api/runs/{run_id}/logs?offset=0` cada 800ms
7. El servidor devuelve los logs nuevos; el dashboard los muestra en la consola
8. Cuando el proceso termina, el status cambia a `completed` o `failed`

### Ejecución automática (Cloud Scheduler)
1. A las 06:00 el scheduler hace `POST https://bots-gateway-prod.../api/auto-run-all` con header `X-CloudScheduler: true`
2. El Gateway enruta a `bot-service`
3. Flask bypasea la autenticación por el header y lanza los 4 bots en paralelo
4. Cada bot genera 10 pedidos de prueba en su tienda correspondiente

### Flujo del bot de Shopify (por pedido)
```
1. Abrir nuevo contexto de navegador (Camoufox/Firefox antidetección)
2. Inyectar cookies de sesión (bypass página de contraseña)
3. Seleccionar producto aleatorio del catálogo
4. Navegar a la página del producto
5. Seleccionar variante aleatoria (talla, color, etc.)
6. Añadir al carrito
7. Ir al checkout (carrito lateral → fallback página /cart)
8. Esperar navegación a URL /checkouts/...
9. Rellenar email del cliente ficticio
10. Rellenar dirección de envío (nombre, apellidos, dirección, ciudad, provincia, CP, país)
11. Esperar carga de métodos de envío
12. Rellenar datos de pago en iframes (número, expiración, CVV, nombre)
13. Hacer click en "Pagar ahora"
14. Esperar página de confirmación (URL contiene "thank-you")
15. Extraer número de pedido
16. Cerrar contexto del navegador
```

Cada paso incluye delays aleatorios distribuidos (entre 10 y 20 segundos en total por pedido) para simular comportamiento humano.

---

## 9. Decisiones de diseño y evolución del proyecto

### Camoufox como motor de navegador
Se eligió **Camoufox** (wrapper antidetección sobre Firefox) en lugar de Playwright puro con Chromium. Camoufox modifica las huellas del navegador (user agent, canvas fingerprint, WebGL, etc.) para reducir la probabilidad de que Shopify detecte el bot.

### Almacenamiento de logs en memoria
Los logs de ejecución se guardan en un diccionario Python en memoria (`runs = {}`), sin base de datos. Esto es sencillo y suficiente porque:
- Los logs solo necesitan persistir mientras el proceso de Gunicorn esté activo
- Con 1 worker (un solo proceso), todos los threads comparten el mismo diccionario
- Al reiniciar el servicio, el historial se pierde (aceptable para el caso de uso)

### Un solo worker de Gunicorn
La configuración `--workers 1 --threads 8` es deliberada. Con múltiples workers (múltiples procesos Python), cada worker tendría su propia copia del diccionario `runs`, y el dashboard podría conectar a un worker que no tiene los logs del bot que está ejecutando otro worker. Con un solo worker y múltiples threads, todos comparten el mismo espacio de memoria.

### Separación frontend/backend
La separación se hizo principalmente por **reducción de costes**. El frontend es HTML/CSS/JS puro y no necesita Python ni navegadores — basta con nginx en 256 MB. El backend necesita 4 CPU y 8 GB para Playwright. Mantenerlos juntos era desperdiciar recursos de cómputo costosos para servir un fichero HTML estático.

---

## 10. URLs y recursos de producción

| Recurso | URL / Identificador |
|---------|---------------------|
| Dashboard (URL pública) | `https://bots-gateway-prod-83hfw8tp.ew.gateway.dev/` |
| API Gateway ID | `bots-gateway-prod` |
| bot-service (Cloud Run) | `https://bot-service-634498283437.europe-southwest1.run.app` |
| frontend-service (Cloud Run) | `https://frontend-service-634498283437.europe-southwest1.run.app` |
| Artifact Registry | `europe-southwest1-docker.pkg.dev/botsecommerce/repo-bots/` |
| GCP Project | `botsecommerce` (ID: `634498283437`) |
| GitHub backend repo | `https://github.com/jvboronatjosep/Bots_Ecommerce_Cloud` |
| GitHub frontend repo | `https://github.com/CarlosMarNav/Bots_Ecommerce_Frontend` |
| Cloud Scheduler job | `diario-bots-0600` (06:00 diario, `europe-southwest1`) |
| Tienda Shopify de pruebas | `https://store-sendingbay.myshopify.com/` |
