# Esquema de Base de Datos - BotsEcommerce Cloud SQL

## Información General
- **Instancia**: `bbdd-espana-db` (PostgreSQL 15)
- **Ubicación**: `europe-west1-b`
- **Proyecto**: `botsecommerce` (ID: 634498283437)
- **IP Pública**: `34.53.151.235`

## Bases de Datos

| Base de Datos | Descripción |
|---|---|
| `cartociudad` | Base de datos principal con direcciones españolas |
| `cloudsqladmin` | Administración de Cloud SQL |
| `postgres` | Base de datos por defecto |

## Usuarios
- `postgres` - Usuario administrador
- `cartociudad-user` - Usuario para acceso a datos de direcciones

## Tablas Principales

### 1. **portalpk_publi** (428,625 registros)
Tabla principal con información de direcciones y ubicaciones para publicaciones.

| Campo | Tipo | Descripción |
|---|---|---|
| `ogc_fid` | INTEGER (PK) | ID único auto-incrementado |
| `id_porpk` | VARCHAR(100) | Identificador de portal PK |
| `tipo` | VARCHAR(200) | Tipo de ubicación (ej: "PK") |
| `tipo_vial` | VARCHAR | Tipo de vía (calle, avenida, etc) |
| `nombre_via` | VARCHAR(200) | Nombre de la vía |
| `numero` | VARCHAR(6) | Número de la calle |
| `extension` | VARCHAR(50) | Extensión/complemento del número |
| `id_pob` | VARCHAR(10) | ID de población |
| `poblacion` | VARCHAR(200) | Nombre de la población |
| `cod_postal` | VARCHAR(5) | Código postal (5 dígitos) |
| `ine_mun` | VARCHAR(5) | Código INE del municipio |
| `municipio` | VARCHAR(128) | Nombre del municipio |
| `provincia` | VARCHAR(50) | Nombre de la provincia |
| `comunidad_autonoma` | VARCHAR(50) | Comunidad autónoma |
| `fuente_datos` | VARCHAR(200) | Fuente de los datos |
| `fecha_modificacion` | TIMESTAMP | Fecha de última modificación |
| `geom` | GEOMETRY(Point, 4258) | Coordenadas geográficas |

**Índices:**
- `portalpk_publi_pkey` - PRIMARY KEY en `ogc_fid`
- `portalpk_publi_geom_geom_idx` - Índice GIST en geometría

### 2. **direcciones_completo** (0 registros actualmente)
Tabla consolidada de direcciones completas (actualmente vacía).

| Campo | Tipo | Descripción |
|---|---|---|
| `ogc_fid` | INTEGER | ID único |
| `id_porpk` | VARCHAR(100) | Identificador de portal |
| `nombre_via` | VARCHAR(200) | Nombre de la vía |
| `numero` | VARCHAR(6) | Número de la calle |
| `extension` | VARCHAR(50) | Extensión del número |
| `cod_postal` | VARCHAR(5) | Código postal |
| `provincia` | VARCHAR(50) | Provincia |
| `municipio` | VARCHAR(128) | Municipio |
| `poblacion` | VARCHAR(200) | Población |
| `comunidad_autonoma` | VARCHAR(50) | Comunidad autónoma |
| `geom` | GEOMETRY(Point, 4258) | Coordenadas geográficas |

**Índices:**
- `idx_direcciones_cp` - Índice en `cod_postal`
- `idx_direcciones_municipio` - Índice en `municipio`
- `idx_direcciones_provincia` - Índice en `provincia`

### 3. **Tablas por Provincia** (54 tablas)
Tablas separadas por provincia con la misma estructura que `direcciones_completo`:
- `direcciones_a_coruna`
- `direcciones_alava`
- `direcciones_albacete`
- ... (una tabla por cada provincia española)
- `direcciones_zaragoza`

### 4. **Tablas de Geometría PostGIS**
- `geography_columns` - Metadatos de columnas geográficas
- `geometry_columns` - Metadatos de columnas geométricas
- `spatial_ref_sys` - Sistemas de referencia espacial
- `manzana` - Datos de manzanas urbanas

## Datos Geográficos

Las tablas utilizan PostGIS para almacenar geometría:
- **SRID**: 4258 (ETRS89 - Sistema de referencia europeo)
- **Tipo**: Point (coordenadas de punto)

## Ejemplo de Consulta

```sql
-- Obtener direcciones de una provincia
SELECT nombre_via, numero, cod_postal, municipio, poblacion
FROM portalpk_publi
WHERE provincia = 'Madrid'
LIMIT 10;

-- Obtener por código postal
SELECT * FROM portalpk_publi
WHERE cod_postal = '28001';

-- Búsqueda por municipio y provincia
SELECT nombre_via, numero, cod_postal, poblacion
FROM portalpk_publi
WHERE municipio = 'Madrid' AND provincia = 'Madrid'
ORDER BY nombre_via, numero;
```

## Credenciales de Conexión

**Para conectarse desde Python:**

```python
import psycopg2

connection = psycopg2.connect(
    host="34.53.151.235",
    user="cartociudad-user",
    password="TempPassword456!",
    database="cartociudad",
    port=5432
)

cursor = connection.cursor()
cursor.execute("SELECT * FROM portalpk_publi LIMIT 5;")
rows = cursor.fetchall()
```

**Para conectarse desde línea de comandos:**

```bash
export PGPASSWORD=TempPassword456!
psql -h 34.53.151.235 -U cartociudad-user -d cartociudad
```

## Notas Importantes

1. **volumen de datos**: La tabla principal (`portalpk_publi`) tiene más de 428K registros de direcciones españolas
2. **Índices**: Existen índices en provincias, municipios y códigos postales para optimizar búsquedas
3. **Geometría**: Los datos incluyen coordenadas geográficas para ubicación exacta
4. **Disponibilidad**: La base de datos está en EU (europe-west1-b) con IP pública accesible
