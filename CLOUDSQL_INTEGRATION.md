# Integración de WooCommerce Bot con Cloud SQL

## 📋 Descripción

El bot WooCommerce ahora obtiene **EXCLUSIVAMENTE** direcciones reales de la base de datos Cloud SQL del proyecto `botsecommerce`. Ya no usa APIs externas como randomuser.me, zippopotam.us ni Catastro.

## 🗄️ Base de Datos

**Instancia:** `bbdd-espana-db` (PostgreSQL 15)
**Ubicación:** Europe-west1-b (IP: 34.53.151.235)
**Base de datos:** `cartociudad`
**Tabla principal:** `portalpk_publi` (428,625 registros)

### Campos disponibles en la BD

```
nombre_via       | VARCHAR(200) | Nombre de la vía (ej: "Calle Mayor")
numero           | VARCHAR(6)   | Número de la calle (ej: "42")
cod_postal       | VARCHAR(5)   | Código postal (ej: "28001")
municipio        | VARCHAR(128) | Municipio (ej: "Madrid")
provincia        | VARCHAR(50)  | Provincia (ej: "Girona", "Araba/Álava")
poblacion        | VARCHAR(200) | Población
```

### Datos disponibles actualmente

- **Araba/Álava:** 52,539 direcciones
- **Girona:** 376,086 direcciones
- **Total:** 428,625 registros

## 📝 Campos del Cliente Generado

Los clientes generados incluyen estos campos obtenidos de CloudSQL:

```python
{
    "address1": "SANTA MARGARIDA 13",      # De: nombre_via + numero
    "zip_code": "17220",                   # De: cod_postal
    "city": "Sant Feliu de Guíxols",       # De: municipio
    "province_code": "GI",                 # Extraído de cod_postal
    "country": "Spain",
    "country_code": "ES",
    "fuente": "CloudSQL"
}
```

## 🚀 Uso

### 1. Configuración

Asegúrate de que el archivo `.env` en `bots/woocommerce_bot/` contiene:

```env
CLOUDSQL_HOST=34.53.151.235
CLOUDSQL_USER=cartociudad-user
CLOUDSQL_PASSWORD=TempPassword456!
CLOUDSQL_DATABASE=cartociudad
CLOUDSQL_PORT=5432
```

### 2. Instalación de dependencias

```bash
cd Bots_Ecommerce_Cloud
pip install -r requirements.txt
```

### 3. Ejecutar el bot

**Sin provincia específica (dirección aleatoria de toda España):**
```bash
cd bots/woocommerce_bot
python3 main.py --orders 5
```

**Con provincia específica:**
```bash
python3 main.py --orders 5 --province "Girona"
python3 main.py --orders 5 --province "GI"
```

## 🔍 Pruebas

Para verificar que la integración funciona correctamente:

```bash
cd Bots_Ecommerce_Cloud
python3 test_cloudsql_integration.py
```

Esto verificará:
- ✅ Conexión a Cloud SQL
- ✅ Estadísticas de direcciones por provincia
- ✅ Generación de cliente sin provincia
- ✅ Generación de cliente con provincia específica

## 📊 Estructura del código

### Archivos nuevos/modificados

```
bots/woocommerce_bot/
├── data/
│   ├── database.py          # 🆕 Módulo de conexión a CloudSQL
│   └── fake_customer.py     # ✏️ Modificado para usar CloudSQL
├── .env                     # 🆕 Variables de entorno
└── [otros archivos...]

Bots_Ecommerce_Cloud/
├── test_cloudsql_integration.py  # 🆕 Script de prueba
└── requirements.txt              # ✏️ Añadido psycopg2-binary
```

### Módulo `database.py`

Contiene:

**`CloudSQLConnection`** - Gestor de conexión PostgreSQL
- `__init__()` - Inicializa conexión
- `get_connection()` - Context manager para obtener conexión
- `test_connection()` - Verifica conexión activa

**`AddressRepository`** - Repositorio de direcciones
- `get_address_by_province(code)` - Obtiene dirección aleatoria de provincia
- `get_random_address()` - Obtiene dirección aleatoria de todo
- `get_addresses_batch(province, limit)` - Obtiene lote de direcciones
- `get_province_stats()` - Obtiene estadísticas por provincia

**`format_address_from_db()`** - Convierte registro BD a formato cliente

### Módulo `fake_customer.py` (modificado)

- **Removido:** Todas las llamadas a APIs externas
- **Removido:** Lógica de Catastro, randomuser.me, zippopotam.us
- **Removido:** CSVs locales como fallback
- **Añadido:** Función `_fetch_address_from_cloudsql()`
- **Añadido:** Integración con `CloudSQLConnection` y `AddressRepository`

## ⚠️ Limitaciones Actuales

La base de datos contiene **solo 2 provincias**:
- Araba/Álava
- Girona

Si solicitas una provincia no disponible, el sistema automáticamente usa una aleatoria de las disponibles.

## 🔄 Flujo de obtención de dirección

```
1. CustomerGenerator.generate()
   └─> _fetch_address_from_cloudsql(province_code)
       ├─ Si province_code: busca en esa provincia
       │  └─ Si no hay: busca aleatoria
       └─ Si no province_code: busca aleatoria
           └─> _address_repo.get_address_by_province() O get_random_address()
               └─> format_address_from_db()
                   └─> FakeCustomer con dirección real
```

## 🛠️ Troubleshooting

### Error: "No se puede conectar a Cloud SQL"
- Verifica que IP `34.53.151.235` sea accesible
- Comprueba las credenciales en `.env`
- Ejecuta: `ping 34.53.151.235`

### Error: "No address found in CloudSQL"
- Las provincias en BD son limitadas (Álava, Girona)
- El sistema hará fallback a dirección aleatoria

### Error: `psycopg2` no instalado
```bash
pip install 'psycopg2-binary>=2.9.0'
```

## 📈 Mejoras futuras

1. **Cargar todas las provincias españolas** en la BD
2. **Caché en memoria** de direcciones para menor latencia
3. **Precarga de datos** al iniciar bot
4. **Estadísticas por provincia** para requests balanceadas
5. **Tests unitarios** para repositorio

## 👤 Contacto

Para preguntas sobre la integración, contacta al equipo de desarrollo.
