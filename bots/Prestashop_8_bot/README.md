# PrestaShop Test Order Bot

Bot para generar pedidos de prueba en `https://prestashop8.mendepru.com`.

## Diferencias con el bot de Shopify

| | Shopify Bot | PrestaShop Bot |
|---|---|---|
| Acceso | Contraseña de tienda | Login con cuenta |
| Variantes | `<select>` dropdown | Radio buttons |
| Carrito | Drawer lateral | Página `/carrito` |
| Checkout | Multi-página | Una sola página `/pedido` |
| Pago | iframes (Bogus Gateway) | Selección de opción + checkbox |
| Confirmación | URL `thank-you` | URL `confirmacion-pedido` |

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

# Con delay entre pedidos
python main.py --orders 3 --delay 5
```

## Variables de entorno (.env)

```env
BOT_STORE_URL=https://prestashop8.mendepru.com
BOT_STORE_EMAIL=integraciones@sendingbay.com
BOT_STORE_PASSWORD=Revergac10n!
BOT_NUM_ORDERS=10
BOT_HEADLESS=false
```

## Estructura

```
prestashop_bot/
├── config/
│   └── settings.py         # Configuración (URL, credenciales, etc.)
├── core/
│   ├── browser.py          # Gestión del navegador (Camoufox)
│   ├── store_navigator.py  # Login + navegación de productos
│   ├── cart_manager.py     # Añadir al carrito + ir al checkout
│   └── checkout_handler.py # Dirección + envío + pago + confirmación
├── data/
│   ├── addresses.py        # Direcciones españolas
│   └── fake_customer.py    # Generador de clientes falsos
├── utils/
│   ├── logger.py           # Logger con Rich
│   ├── retry.py            # Decorador de reintentos
│   ├── selectors.py        # Selectores CSS de PrestaShop
│   └── timing.py           # Delays aleatorios por pedido
├── main.py                 # Punto de entrada
└── requirements.txt
```

## Flujo del bot

1. **Login** con `integraciones@sendingbay.com`
2. **Descubrimiento** de productos en `/men`
3. Por cada pedido:
   - Login en contexto nuevo
   - Navegar a producto aleatorio
   - Seleccionar variante aleatoria (talla/color)
   - Añadir al carrito
   - Ir a `/carrito` → Proceder al checkout
   - En `/pedido`: confirmar dirección → confirmar envío → pagar → aceptar términos
   - Capturar referencia del pedido en `/confirmacion-pedido`
