# Shopify Test Order Bot

Bot de automatizacion para generar pedidos de prueba en tiendas Shopify. Utiliza Camoufox (navegador stealth basado en Firefox) y Playwright para simular comportamiento humano y evadir sistemas antibot.

## Requisitos

- Python 3.10+
- [Camoufox](https://github.com/nicedayzhu/camoufox) (se instala con las dependencias)

## Instalacion

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd BotComprasShopify

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Configuracion

Crea un archivo `.env` en la raiz del proyecto:

```env
BOT_STORE_URL=https://tu-tienda.myshopify.com/
BOT_STORE_PASSWORD=tu_password
BOT_NUM_ORDERS=10
BOT_HEADLESS=false

# Pago (Bogus Gateway para testing)
BOT_PAYMENT_CARD_NUMBER=1
BOT_PAYMENT_CARD_NAME=Bogus Gateway
BOT_PAYMENT_CARD_EXPIRY=12/28
BOT_PAYMENT_CARD_CVV=123
```

### Variables disponibles

| Variable | Descripcion | Default |
|----------|-------------|---------|
| `BOT_STORE_URL` | URL de la tienda Shopify | - |
| `BOT_STORE_PASSWORD` | Password de la tienda (si esta protegida) | - |
| `BOT_NUM_ORDERS` | Numero de pedidos a generar | `10` |
| `BOT_HEADLESS` | Ejecutar sin interfaz grafica | `false` |
| `BOT_PAYMENT_CARD_NUMBER` | Numero de tarjeta | `1` |
| `BOT_PAYMENT_CARD_NAME` | Nombre en la tarjeta | `Bogus Gateway` |
| `BOT_PAYMENT_CARD_EXPIRY` | Fecha de expiracion | `12/28` |
| `BOT_PAYMENT_CARD_CVV` | CVV | `123` |

## Uso

```bash
# Ejecutar con configuracion por defecto (.env)
python main.py

# Especificar numero de pedidos
python main.py --orders 5

# Modo headless (sin ventana del navegador)
python main.py --headless

# Varios productos por pedido
python main.py --products-per-order 3

# Delay entre pedidos (segundos)
python main.py --delay 5

# Combinar opciones
python main.py --orders 20 --headless --products-per-order 2 --delay 3
```

### Argumentos CLI

| Argumento | Descripcion |
|-----------|-------------|
| `--orders N` | Numero de pedidos a generar |
| `--headless` | Ejecutar navegador en modo headless |
| `--products-per-order N` | Productos por pedido |
| `--slow-mo MS` | Delay de slow motion en ms |
| `--delay SECONDS` | Delay entre pedidos |

## Estructura del proyecto

```
BotComprasShopify/
├── main.py                  # Punto de entrada
├── requirements.txt         # Dependencias
├── .env                     # Configuracion
│
├── config/
│   └── settings.py          # Configuracion con Pydantic
│
├── core/
│   ├── browser.py           # Gestion del navegador Camoufox
│   ├── store_navigator.py   # Bypass de password y descubrimiento de productos
│   ├── cart_manager.py      # Gestion del carrito
│   ├── checkout_handler.py  # Proceso de checkout
│   └── payment_handler.py   # Rellenado de datos de pago (iframes)
│
├── data/
│   ├── fake_customer.py     # Generacion de clientes falsos (ES)
│   └── addresses.py         # Base de datos de direcciones espanolas
│
└── utils/
    ├── selectors.py         # Selectores CSS de la UI
    ├── timing.py            # Delays humanizados
    ├── logger.py            # Logging con Rich
    └── retry.py             # Logica de reintentos
```

## Como funciona

1. **Inicio**: Lanza un navegador Camoufox con fingerprint spoofing
2. **Acceso**: Bypasea la pagina de password de la tienda
3. **Descubrimiento**: Obtiene todos los productos disponibles desde `/collections/all`
4. **Por cada pedido**:
   - Genera un cliente falso con datos espanoles realistas (Faker)
   - Crea un perfil de delays unico para simular comportamiento humano
   - Navega a productos aleatorios y los anade al carrito
   - Completa el formulario de checkout (contacto, envio, pago)
   - Confirma el pedido y extrae el numero de orden
5. **Resultado**: Muestra tabla resumen con estadisticas de exito/fallo

## Output

- **Consola**: Tabla formateada con Rich mostrando estado de cada pedido
- **Logs**: Archivo `bot_orders.log` con logs detallados
- **Screenshots**: Capturas automaticas en `screenshots/` cuando hay errores

## Tecnologias

- **[Playwright](https://playwright.dev/)** - Automatizacion de navegador
- **[Camoufox](https://github.com/nicedayzhu/camoufox)** - Navegador stealth anti-deteccion
- **[Faker](https://faker.readthedocs.io/)** - Generacion de datos falsos
- **[Pydantic](https://docs.pydantic.dev/)** - Validacion de configuracion
- **[Rich](https://rich.readthedocs.io/)** - Output de terminal enriquecido
- **[Tenacity](https://tenacity.readthedocs.io/)** - Reintentos con backoff
