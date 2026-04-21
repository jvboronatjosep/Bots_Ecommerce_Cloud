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
    """Repositorio de direcciones desde Cloud SQL - Todas las provincias"""

    PROVINCE_TABLE_MAP = {
        "MD": "direcciones_madrid", "MADRID": "direcciones_madrid",
        "B": "direcciones_barcelona", "BARCELONA": "direcciones_barcelona",
        "V": "direcciones_valencia", "VALENCIA": "direcciones_valencia",
        "SE": "direcciones_sevilla", "SEVILLA": "direcciones_sevilla",
        "GI": "direcciones_girona", "GIRONA": "direcciones_girona",
        "VI": "direcciones_alava", "ALAVA": "direcciones_alava", "ÁRABA": "direcciones_alava",
        "AB": "direcciones_albacete", "ALBACETE": "direcciones_albacete",
        "A": "direcciones_alicante", "ALICANTE": "direcciones_alicante",
        "AL": "direcciones_almeria", "ALMERIA": "direcciones_almeria", "ALMERÍA": "direcciones_almeria",
        "O": "direcciones_asturias", "ASTURIAS": "direcciones_asturias",
        "BA": "direcciones_badajoz", "BADAJOZ": "direcciones_badajoz",
        "PM": "direcciones_baleares", "BALEARES": "direcciones_baleares",
        "CA": "direcciones_cadiz", "CADIZ": "direcciones_cadiz", "CÁDIZ": "direcciones_cadiz",
        "S": "direcciones_cantabria", "CANTABRIA": "direcciones_cantabria",
        "CS": "direcciones_castellon", "CASTELLON": "direcciones_castellon", "CASTELLÓ": "direcciones_castellon",
        "CR": "direcciones_ciudad_real", "CIUDAD REAL": "direcciones_ciudad_real",
        "CO": "direcciones_cordoba", "CORDOBA": "direcciones_cordoba", "CÓRDOBA": "direcciones_cordoba",
        "CU": "direcciones_cuenca", "CUENCA": "direcciones_cuenca",
        "CE": "direcciones_ceuta", "CEUTA": "direcciones_ceuta",
        "GU": "direcciones_guadalajara", "GUADALAJARA": "direcciones_guadalajara",
        "SS": "direcciones_guipuzcoa", "GUIPUZCOA": "direcciones_guipuzcoa", "GIPUZKOA": "direcciones_guipuzcoa",
        "H": "direcciones_huelva", "HUELVA": "direcciones_huelva",
        "HU": "direcciones_huesca", "HUESCA": "direcciones_huesca",
        "J": "direcciones_jaen", "JAEN": "direcciones_jaen", "JAÉN": "direcciones_jaen",
        "LO": "direcciones_la_rioja", "LA RIOJA": "direcciones_la_rioja",
        "GC": "direcciones_las_palmas", "LAS PALMAS": "direcciones_las_palmas",
        "LE": "direcciones_leon", "LEON": "direcciones_leon", "LEÓN": "direcciones_leon",
        "L": "direcciones_lleida", "LLEIDA": "direcciones_lleida",
        "LU": "direcciones_lugo", "LUGO": "direcciones_lugo",
        "MA": "direcciones_malaga", "MALAGA": "direcciones_malaga", "MÁLAGA": "direcciones_malaga",
        "ML": "direcciones_melilla", "MELILLA": "direcciones_melilla",
        "MU": "direcciones_murcia", "MURCIA": "direcciones_murcia",
        "NA": "direcciones_navarra", "NAVARRA": "direcciones_navarra",
        "OR": "direcciones_ourense", "OURENSE": "direcciones_ourense",
        "P": "direcciones_palencia", "PALENCIA": "direcciones_palencia",
        "PO": "direcciones_pontevedra", "PONTEVEDRA": "direcciones_pontevedra",
        "SA": "direcciones_salamanca", "SALAMANCA": "direcciones_salamanca",
        "SG": "direcciones_segovia", "SEGOVIA": "direcciones_segovia",
        "SO": "direcciones_soria", "SORIA": "direcciones_soria",
        "T": "direcciones_tarragona", "TARRAGONA": "direcciones_tarragona",
        "TF": "direcciones_tenerife", "TENERIFE": "direcciones_tenerife",
        "TE": "direcciones_teruel", "TERUEL": "direcciones_teruel",
        "TO": "direcciones_toledo", "TOLEDO": "direcciones_toledo",
        "VA": "direcciones_valladolid", "VALLADOLID": "direcciones_valladolid",
        "BI": "direcciones_vizcaya", "VIZCAYA": "direcciones_vizcaya", "BIZKAIA": "direcciones_vizcaya",
        "C": "direcciones_a_coruna", "A CORUÑA": "direcciones_a_coruna", "A CORUNA": "direcciones_a_coruna",
        "ZA": "direcciones_zamora", "ZAMORA": "direcciones_zamora",
        "Z": "direcciones_zaragoza", "ZARAGOZA": "direcciones_zaragoza",
    }

    def __init__(self, db: CloudSQLConnection):
        self.db = db

    def _get_table_for_province(self, province_identifier: str) -> Optional[str]:
        """Obtiene el nombre de tabla basado en código o nombre de provincia."""
        if not province_identifier:
            return None
        normalized = province_identifier.upper().strip()
        return self.PROVINCE_TABLE_MAP.get(normalized)

    def get_address_by_province(self, province_code: str) -> Optional[Dict]:
        """Obtiene dirección aleatoria de provincia específica."""
        table_name = self._get_table_for_province(province_code)
        if not table_name:
            return None

        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = f"SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion FROM {table_name} ORDER BY RANDOM() LIMIT 1"
                    cur.execute(query)
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error obtener dirección de {province_code}: {e}")
            return None

    def get_random_address(self) -> Optional[Dict]:
        """Obtiene dirección aleatoria de todas las provincias."""
        try:
            tables = list(set([t for t in self.PROVINCE_TABLE_MAP.values()]))
            random_table = random.choice(tables)

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = f"SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion FROM {random_table} ORDER BY RANDOM() LIMIT 1"
                    cur.execute(query)
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error obtener dirección aleatoria: {e}")
            return None

    def get_addresses_batch(self, province_code: str = None, limit: int = 10) -> List[Dict]:
        """Obtiene lote de direcciones."""
        try:
            if province_code:
                table_name = self._get_table_for_province(province_code)
                if not table_name:
                    return []
            else:
                tables = list(set([t for t in self.PROVINCE_TABLE_MAP.values()]))
                table_name = random.choice(tables)

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = f"SELECT nombre_via, numero, cod_postal, municipio, provincia, poblacion FROM {table_name} ORDER BY RANDOM() LIMIT %s"
                    cur.execute(query, (limit,))
                    results = cur.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            print(f"Error obtener lote: {e}")
            return []

    def get_province_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de direcciones por provincia."""
        stats = {}
        try:
            with self.db.get_connection() as conn:
                for table_name in set(self.PROVINCE_TABLE_MAP.values()):
                    with conn.cursor() as cur:
                        try:
                            query = f"SELECT COUNT(*) as count FROM {table_name}"
                            cur.execute(query)
                            result = cur.fetchone()
                            provincia = table_name.replace("direcciones_", "").upper()
                            stats[provincia] = result[0] if result else 0
                        except:
                            pass
        except Exception as e:
            print(f"Error estadísticas: {e}")
        return stats


def format_address_from_db(db_record: Dict) -> Dict:
    """Convierte registro BD a formato FakeCustomer."""
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
    """Extrae código provincia de ZIP."""
    from data.addresses import PROVINCE_BY_ZIP_PREFIX
    prefix = zip_code[:2] if len(zip_code) >= 2 else ""
    return PROVINCE_BY_ZIP_PREFIX.get(prefix, "XX")
