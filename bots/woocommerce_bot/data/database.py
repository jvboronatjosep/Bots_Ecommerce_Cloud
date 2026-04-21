import os
import random
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


class CloudSQLConnection:
    """Gestor de conexión a Cloud SQL PostgreSQL"""

    def __init__(
        self,
        host: str = os.getenv("CLOUDSQL_HOST", "34.53.151.235"),
        user: str = os.getenv("CLOUDSQL_USER", "cartociudad-user"),
        password: str = os.getenv("CLOUDSQL_PASSWORD", "TempPassword456!"),
        database: str = os.getenv("CLOUDSQL_DATABASE", "cartociudad"),
        port: int = int(os.getenv("CLOUDSQL_PORT", "5432")),
    ):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port

    @contextmanager
    def get_connection(self):
        """Context manager para obtener conexión a BD"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connect_timeout=10,
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def test_connection(self) -> bool:
        """Prueba la conexión a la BD"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            print(f"Error de conexión a Cloud SQL: {e}")
            return False


class AddressRepository:
    """Repositorio de direcciones desde Cloud SQL"""

    def __init__(self, db: CloudSQLConnection):
        self.db = db

    def get_address_by_province(self, province_code: str) -> Optional[Dict]:
        """
        Obtiene una dirección aleatoria de una provincia específica.

        Args:
            province_code: Código de provincia (ej: "MD" para Madrid, "B" para Barcelona)

        Returns:
            Dict con campos: nombre_via, numero, cod_postal, municipio, provincia, poblacion
            O None si no hay direcciones disponibles
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Obtener una dirección aleatoria de la provincia
                    query = """
                        SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion
                        FROM portalpk_publi
                        WHERE LOWER(provincia) = LOWER(%s)
                        ORDER BY RANDOM()
                        LIMIT 1
                    """
                    cur.execute(query, (province_code,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error al obtener dirección de provincia {province_code}: {e}")
            return None

    def get_random_address(self) -> Optional[Dict]:
        """
        Obtiene una dirección completamente aleatoria de toda la BD.

        Returns:
            Dict con campos: nombre_via, numero, cod_postal, municipio, provincia, poblacion
            O None si hay error
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion
                        FROM portalpk_publi
                        ORDER BY RANDOM()
                        LIMIT 1
                    """
                    cur.execute(query)
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error al obtener dirección aleatoria: {e}")
            return None

    def get_addresses_batch(self, province_code: str = None, limit: int = 10) -> List[Dict]:
        """
        Obtiene un lote de direcciones (útil para precarga en memoria).

        Args:
            province_code: Código de provincia (opcional)
            limit: Número de direcciones a obtener

        Returns:
            Lista de direcciones
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if province_code:
                        query = """
                            SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion
                            FROM portalpk_publi
                            WHERE LOWER(provincia) = LOWER(%s)
                            ORDER BY RANDOM()
                            LIMIT %s
                        """
                        cur.execute(query, (province_code, limit))
                    else:
                        query = """
                            SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion
                            FROM portalpk_publi
                            ORDER BY RANDOM()
                            LIMIT %s
                        """
                        cur.execute(query, (limit,))

                    results = cur.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            print(f"Error al obtener lote de direcciones: {e}")
            return []

    def get_province_stats(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de direcciones por provincia.

        Returns:
            Dict con {provincia: cantidad_direcciones}
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT provincia, COUNT(*) as count
                        FROM portalpk_publi
                        GROUP BY provincia
                        ORDER BY provincia
                    """
                    cur.execute(query)
                    results = cur.fetchall()
                    return {row["provincia"]: row["count"] for row in results}
        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
            return {}


def format_address_from_db(db_record: Dict) -> Dict:
    """
    Transforma un registro de BD en formato compatible con FakeCustomer.

    Args:
        db_record: Registro de BD con campos: nombre_via, numero, cod_postal, municipio, provincia, poblacion

    Returns:
        Dict con campos: address1, zip_code, city, province_code, provincia, fuente
    """
    if not db_record:
        return None

    return {
        "address1": f"{db_record.get('nombre_via', '')} {db_record.get('numero', '')}".strip(),
        "zip_code": db_record.get("cod_postal", "").zfill(5),
        "city": db_record.get("municipio", ""),
        "poblacion": db_record.get("poblacion", ""),
        "province_code": _extract_province_code(db_record.get("cod_postal", "")),
        "provincia": db_record.get("provincia", ""),
        "country": "Spain",
        "country_code": "ES",
        "fuente": "CloudSQL",
    }


def _extract_province_code(zip_code: str) -> str:
    """
    Extrae el código de provincia a partir del código postal.
    Los dos primeros dígitos del CP español identifican la provincia.
    """
    from data.addresses import PROVINCE_BY_ZIP_PREFIX

    prefix = zip_code[:2] if len(zip_code) >= 2 else ""
    return PROVINCE_BY_ZIP_PREFIX.get(prefix, "XX")
