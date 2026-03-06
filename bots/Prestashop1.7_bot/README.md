# PrestaShop 1.7 Test Order Bot

Bot para generar pedidos de prueba en PrestaShop 1.7 como invitado con datos aleatorios.

## Instalación

```bash
pip install -r requirements.txt
playwright install firefox
```

## Configuración (.env)

```env
BOT_STORE_URL=https://prestashop7.mendepru.com
BOT_NUM_ORDERS=10
BOT_HEADLESS=false
```

## Uso

```bash
# 1 pedido de prueba
python main.py --orders 1

# 10 pedidos en modo headless
python main.py --orders 10 --headless
```

## Estructura

```
prestashop17_bot/
├── config/settings.py       # Configuración
├── core/
│   ├── browser.py           # Camoufox browser
│   ├── store_navigator.py   # Scraping de productos
│   ├── cart_manager.py      # Añadir al carrito
│   └── checkout_handler.py  # Flujo de checkout (4 pasos)
├── data/
│   ├── addresses.py         # Direcciones españolas
│   └── fake_customer.py     # Generador de clientes falsos
└── utils/
    ├── selectors.py         # Selectores CSS
    ├── timing.py            # Delays aleatorios
    └── logger.py            # Logging con Rich
```

## Flujo

1. Scrapea productos de `/index.php`
2. Por cada pedido: nuevo contexto de navegador (cliente limpio)
3. Añade producto al carrito
4. Checkout como invitado: datos personales → dirección → envío → pago
5. Confirma y extrae referencia del pedido
