# WooCommerce Test Order Bot

Bot para generar pedidos de prueba en `https://woocomerce.mendepru.com`.

## Diferencias con el bot de PrestaShop

| | PrestaShop Bot | WooCommerce Bot |
|---|---|---|
| Acceso | Login con cuenta | Guest checkout (sin login) |
| Variantes | Radio buttons | `<select>` dropdown |
| Carrito | Página `/carrito` | Página `/cart` |
| Checkout | Una sola página `/pedido` | Una sola página `/checkout` |
| Pago | Selección de opción + checkbox | Primera opción disponible + #terms |
| Confirmación | URL `confirmacion-pedido` | URL `order-received` |

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium
```

## Uso

```bash
# Ejecución básica (10 pedidos)
python main.py

# Personalizar número de pedidos
python main.py --orders 5

# Modo headless
python main.py --headless

# Con slow motion (ms) y delay entre pedidos (segundos)
python main.py --orders 3 --slow-mo 500 --delay 5 --headless
```

## Variables de entorno (.env)

```env
BOT_STORE_URL=https://woocomerce.mendepru.com
BOT_STORE_EMAIL=integraciones@sendingbay.com
BOT_STORE_PASSWORD=Revergac10n!
BOT_NUM_ORDERS=10
BOT_HEADLESS=false
```

## Estructura

```
woocommerce_bot/
├── config/
│   └── settings.py         # Configuración (URL, credenciales, etc.)
├── core/
│   ├── browser.py          # Gestión del navegador (Camoufox)
│   ├── store_navigator.py  # Navegación y descubrimiento de productos
│   ├── cart_manager.py     # Añadir al carrito + ir al checkout
│   └── checkout_handler.py # Datos de envío + pago + confirmación
├── data/
│   ├── addresses.py        # Direcciones españolas
│   └── fake_customer.py    # Generador de clientes falsos
├── utils/
│   ├── logger.py           # Logger con Rich
│   ├── retry.py            # Decorador de reintentos
│   ├── selectors.py        # Selectores CSS de WooCommerce
│   └── timing.py           # Delays aleatorios por pedido
├── main.py                 # Punto de entrada
└── requirements.txt
```

## Flujo del bot

1. **Descubrimiento** de productos en `/shop`
2. Por cada pedido:
   - Navegar a producto aleatorio
   - Seleccionar variante aleatoria (dropdown `<select>`)
   - Añadir al carrito
   - Ir a `/cart` → Proceder al checkout
   - En `/checkout`: rellenar datos de facturación (nombre, email, dirección española, DNI) → seleccionar método de pago → aceptar términos
   - Capturar referencia del pedido en `/order-received/{id}`
