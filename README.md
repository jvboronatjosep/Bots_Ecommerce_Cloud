# 🤖 Bot Control Das
Panel web para gestionar y ejecutar bots de compras automáticas en Shopify, WooCommerce y PrestaShop.
---
## 📋 Requisitos previos
- **Python 3.10+**
- **pip**
---

## 🚀 Instalación
### 1. Crear entorno virtual (recomendado)

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 2. Instalar dependencias del servidor (Flask)

```bash
pip install -r requirements.txt
```

Esto instala:
| Paquete | Versión mínima | Para qué sirve |
|---|---|---|
| `flask` | 3.0.0 | Servidor web del dashboard |
| `flask-cors` | 4.0.0 | Permite peticiones cross-origin al API |

---


### 3. Instalar navegadores de Playwright
Después de instalar Playwright, hay que descargar los navegadores:

```bash
playwright install
```

### 4. Instalar datos de Camoufox (GeoIP)
```bash
python -m camoufox fetch
```

---

## ⚙️ Configuración

Toda la configuración se gestiona desde un único archivo en la raíz del proyecto:

```
.env                  ← único archivo para todos los bots
```

Cada bot usa su propio prefijo para evitar colisiones:

| Bot | Prefijo |
|-----|---------|
| Shopify | `SHOPIFY_BOT_` |
| WooCommerce | `WOOCOMMERCE_BOT_` |
| PrestaShop 1.7 | `PRESTASHOP17_BOT_` |
| PrestaShop 8 | `PRESTASHOP8_BOT_` |

### Variables principales por bot

```env
# --- Shopify ---
SHOPIFY_BOT_STORE_URL=https://tu-tienda.myshopify.com/
SHOPIFY_BOT_STORE_PASSWORD=tu_password
SHOPIFY_BOT_NUM_ORDERS=10
SHOPIFY_BOT_HEADLESS=false
SHOPIFY_BOT_PAYMENT_CARD_NUMBER=1
SHOPIFY_BOT_PAYMENT_CARD_NAME=Bogus Gateway
SHOPIFY_BOT_PAYMENT_CARD_EXPIRY=12/28
SHOPIFY_BOT_PAYMENT_CARD_CVV=123

# --- WooCommerce ---
WOOCOMMERCE_BOT_STORE_URL=https://tu-tienda.com/
WOOCOMMERCE_BOT_STORE_EMAIL=tu@email.com
WOOCOMMERCE_BOT_STORE_PASSWORD=tu_password
WOOCOMMERCE_BOT_NUM_ORDERS=10
WOOCOMMERCE_BOT_HEADLESS=false

# --- PrestaShop 1.7 ---
PRESTASHOP17_BOT_STORE_URL=https://tu-tienda.com/
PRESTASHOP17_BOT_NUM_ORDERS=10
PRESTASHOP17_BOT_HEADLESS=false

# --- PrestaShop 8 ---
PRESTASHOP8_BOT_STORE_URL=https://tu-tienda.com/
PRESTASHOP8_BOT_NUM_ORDERS=10
PRESTASHOP8_BOT_HEADLESS=false
```

---

## ▶️ Ejecución
### Iniciar el dashboard web
```bash
python server.py
```

Luego abre tu navegador en: **http://localhost:5000**

### Ejecutar un bot directamente (sin dashboard)

```bash
# Shopify
cd bots/BotComprasShopify-main
python main.py

# WooCommerce
cd bots/woocommerce_bot
python main.py

# PrestaShop 8
cd bots/Prestashop_8_bot
python main.py

# PrestaShop 1.7
cd bots/Prestashop1.7_bot
python main.py
```

---

## 📁 Estructura del proyecto
```
├── server.py                    # Servidor Flask (dashboard)
├── requirements.txt             # Dependencias del servidor
├── static/
│   └── index.html               # Frontend del dashboard
└── bots/
    ├── BotComprasShopify-main/  # Bot para Shopify
    ├── woocommerce_bot/         # Bot para WooCommerce
    ├── Prestashop_8_bot/        # Bot para PrestaShop 8
    └── Prestashop1.7_bot/       # Bot para PrestaShop 1.7
```

---
## 🛠️ Resumen de comandos de instalación
```bash
# 1. Entorno virtual
python3 -m venv .venv && source .venv/bin/activate

# 2. Dependencias del servidor
pip install -r requirements.txt

# 3. Dependencias de los bots
pip install -r bots/BotComprasShopify-main/requirements.txt

# 4. Navegadores de Playwright
playwright install chromium

# 5. Datos GeoIP de Camoufox
python -m camoufox fetch

# 6. Configurar variables de entorno
# Edita el archivo .env en la raíz del proyecto (un solo archivo para todos los bots)

# --- Shopify
# 7. Arrancar
python server.py
```
