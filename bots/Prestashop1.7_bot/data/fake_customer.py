import csv
import json
import os
import random
import re
import unicodedata
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from faker import Faker

from data.addresses import (
    SPAIN_ADDRESSES, STREET_NAMES,
    PROVINCE_BY_ZIP_PREFIX, PROVINCE_PREFIXES, PROVINCE_NAME_TO_CODE,
)
from data.database import CloudSQLConnection, AddressRepository, format_address_from_db

# ── Cloud SQL Database ────────────────────────────────────────────────────────

_db_connection = CloudSQLConnection()
_address_repo = AddressRepository(_db_connection)

_SMALL_TOWN_STREETS = [
    "Calle Mayor", "Calle Real", "Calle Nueva", "Calle del Sol",
    "Calle de la Iglesia", "Calle de la Fuente", "Calle del Río",
    "Plaza Mayor", "Plaza de la Iglesia", "Calle Larga",
    "Camino de la Sierra", "Calle del Campo", "Calle Alta", "Calle Baja",
]
_CITY_STREETS = STREET_NAMES

# ── Catastro ──────────────────────────────────────────────────────────────────

_CATASTRO_BASE = (
    "https://ovc.catastro.meh.es/ovcservweb/"
    "ovcswlocalizacionrc/ovccallejero.asmx"
)
_CATASTRO_NS = "http://www.catastro.meh.es/"

TIPO_VIA_TO_FULL = {
    "CL": "Calle",    "AV": "Avenida",  "PS": "Paseo",      "CM": "Camino",
    "PL": "Plaza",    "TR": "Travesía", "RD": "Ronda",      "GV": "Gran Vía",
    "CR": "Carretera","GL": "Glorieta", "AL": "Alameda",    "PZ": "Plazuela",
    "CJ": "Callejón", "BO": "Barrio",   "LG": "Lugar",      "VL": "Vial",
    "BV": "Bulevar",  "SN": "Senda",    "UR": "Urbanización",
}

PROVINCE_CODE_TO_NAME = {
    "VI": "Álava",     "AB": "Albacete",  "A": "Alicante",   "AL": "Almería",
    "AV": "Ávila",     "BA": "Badajoz",   "PM": "Baleares",  "B": "Barcelona",
    "BU": "Burgos",    "CC": "Cáceres",   "CA": "Cádiz",     "CS": "Castellón",
    "CR": "Ciudad Real","CO": "Córdoba",  "C": "La Coruña",  "CU": "Cuenca",
    "GI": "Gerona",    "GR": "Granada",   "GU": "Guadalajara","SS": "Guipúzcoa",
    "H": "Huelva",     "HU": "Huesca",    "J": "Jaén",       "LE": "León",
    "L": "Lérida",     "LO": "La Rioja",  "LU": "Lugo",
    "M": "Madrid",     "MD": "Madrid",
    "MA": "Málaga",    "MU": "Murcia",    "NA": "Navarra",
    "OR": "Orense",    "O": "Asturias",   "P": "Palencia",   "GC": "Las Palmas",
    "PO": "Pontevedra","SA": "Salamanca", "TF": "Santa Cruz de Tenerife",
    "S": "Cantabria",  "SG": "Segovia",   "SE": "Sevilla",   "SO": "Soria",
    "T": "Tarragona",  "TE": "Teruel",    "TO": "Toledo",    "V": "Valencia",
    "VA": "Valladolid","BI": "Vizcaya",   "ZA": "Zamora",    "Z": "Zaragoza",
    "CE": "Ceuta",     "ML": "Melilla",
}

_street_cache: dict[str, list[dict]] = {}
_number_cache: dict[str, list[str]] = {}
_real_address_cache_by_province: dict[str, list[dict]] = {}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_DEFAULT_REAL_ADDRESS_CSVS = (
    str(_PROJECT_ROOT / "services_rows (23).csv"),
    str(_PROJECT_ROOT / "services_rows (24).csv"),
    str(Path.home() / "Downloads" / "services_rows (23).csv"),
    str(Path.home() / "Downloads" / "services_rows (24).csv"),
    str(Path.cwd() / "services_rows (23).csv"),
    str(Path.cwd() / "services_rows (24).csv"),
)


def _catastro_tag(tag: str) -> str:
    return f"{{{_CATASTRO_NS}}}{tag}"


def _catastro_get(method: str, params: dict) -> Optional[ET.Element]:
    try:
        qs = urllib.parse.urlencode(params)
        url = f"{_CATASTRO_BASE}/{method}?{qs}"
        req = urllib.request.Request(url, headers={"Accept": "text/xml"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return ET.fromstring(resp.read())
    except Exception:
        return None


def _find_all(root: ET.Element, tag: str) -> list[ET.Element]:
    result = list(root.iter(_catastro_tag(tag)))
    return result if result else list(root.iter(tag))


def _find_text(elem: ET.Element, tag: str) -> str:
    child = elem.find(_catastro_tag(tag))
    if child is None:
        child = elem.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _clean_csv_value(value: Optional[str]) -> str:
    return (value or "").strip()


def _load_real_addresses_from_csvs(state_id: str) -> dict[str, list[dict]]:
    if _real_address_cache_by_province:
        return _real_address_cache_by_province

    raw_paths = os.getenv("WOO_REAL_ADDRESS_CSVS")
    csv_paths = [
        Path(p.strip()) for p in raw_paths.split(",") if p.strip()
    ] if raw_paths else [Path(p) for p in _DEFAULT_REAL_ADDRESS_CSVS]
    csv_paths = list(dict.fromkeys(csv_paths))

    rows_by_province: dict[str, list[dict]] = {}
    seen: set[tuple[str, str, str]] = set()
    for csv_path in csv_paths:
        if not csv_path.exists():
            continue
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    address1 = _clean_csv_value(row.get("service_address"))
                    city = _clean_csv_value(row.get("service_city"))
                    zip_code = _clean_csv_value(row.get("service_postal_code")).zfill(5)
                    country = _clean_csv_value(row.get("service_country")).lower()
                    if not address1 or not city or len(zip_code) != 5 or not zip_code.isdigit():
                        continue
                    if country and country not in {"es", "esp", "spain", "espana", "españa"}:
                        continue
                    province_code = PROVINCE_BY_ZIP_PREFIX.get(zip_code[:2])
                    if not province_code:
                        continue
                    city_normalized = city.casefold()
                    if province_code in {"MD", "M"} and city_normalized != "madrid":
                        continue
                    if province_code == "B" and city_normalized != "barcelona":
                        continue
                    key = (address1.lower(), city.lower(), zip_code)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows_by_province.setdefault(province_code, []).append({
                        "address1": address1.title(),
                        "city": city.title(),
                        "zip_code": zip_code,
                        "province_code": province_code,
                        "state_id": state_id,
                        "fuente": "CSV_REAL",
                    })
        except Exception:
            continue

    _real_address_cache_by_province.update(rows_by_province)
    return _real_address_cache_by_province


def _catastro_callejero(province_name: str, city: str) -> list[dict]:
    key = f"{province_name.upper()}:{city.upper()}"
    if key in _street_cache:
        return _street_cache[key]
    root = _catastro_get("ConsultaVia", {
        "Provincia": province_name.upper(),
        "Municipio": city.upper(),
    })
    streets: list[dict] = []
    if root is not None:
        for have in _find_all(root, "have"):
            tv = _find_text(have, "tv")
            nv = _find_text(have, "nv")
            if tv and nv:
                streets.append({"tipo_via": tv, "nombre_via": nv})
    _street_cache[key] = streets
    return streets


def _catastro_numeros(province_name: str, city: str,
                      tipo_via: str, nombre_via: str) -> dict:
    key = f"{province_name.upper()}:{city.upper()}:{tipo_via}:{nombre_via}"
    if key in _number_cache:
        return _number_cache[key]
    root = _catastro_get("ConsultaNumero", {
        "Provincia": province_name.upper(),
        "Municipio": city.upper(),
        "TipoVia":   tipo_via.upper(),
        "NombreVia": nombre_via.upper(),
    })
    result: dict = {"numbers": [], "cp": None}
    if root is not None:
        for have in _find_all(root, "have"):
            street_cp = _find_text(have, "cp")
            if street_cp:
                result["cp"] = street_cp
            for pnp in _find_all(have, "pnp"):
                val = (pnp.text or "").strip()
                if val.isdigit():
                    result["numbers"].append(val)
    _number_cache[key] = result
    return result


def _is_large_city(cp: str) -> bool:
    suffix = int(cp[2:]) if len(cp) == 5 and cp[2:].isdigit() else 999
    return suffix <= 99


def _fallback_street(cp: str) -> tuple[str, int]:
    if _is_large_city(cp):
        return random.choice(_CITY_STREETS), random.randint(1, 250)
    return random.choice(_SMALL_TOWN_STREETS), random.randint(1, 15)


def _fetch_address_from_catastro(province_code: str, city: str, cp: str,
                                  state_id: str = "0") -> Optional[dict]:
    province_name = PROVINCE_CODE_TO_NAME.get(province_code)
    if not province_name:
        return None
    streets = _catastro_callejero(province_name, city)
    if not streets:
        return None

    sample = random.sample(streets, min(15, len(streets)))
    cp_match: list[tuple] = []
    cp_other: list[tuple] = []
    for street in sample:
        data = _catastro_numeros(
            province_name, city, street["tipo_via"], street["nombre_via"]
        )
        if not data["numbers"]:
            continue
        if data["cp"] == cp:
            cp_match.append((street, data["numbers"]))
        else:
            cp_other.append((street, data["numbers"]))

    pool = cp_match if cp_match else cp_other
    if not pool:
        return None
    street, numbers = random.choice(pool)
    numero = random.choice(numbers)
    tipo_full = TIPO_VIA_TO_FULL.get(street["tipo_via"], "Calle")
    nombre = street["nombre_via"].title()
    return {
        "address1":     f"{tipo_full} {nombre} {numero}",
        "city":         city,
        "zip_code":     cp,
        "province_code": province_code,
        "state_id":     state_id,
        "fuente":       "OVCCatastro",
    }


def _sanitize_for_email(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower()) or "user"


def _generate_dni() -> str:
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    number = random.randint(10000000, 99999999)
    return f"{number}{letters[number % 23]}"


FIRST_NAMES_MALE = [
    "Alejandro","Alfonso","Álvaro","Andrés","Antonio","Arturo","Borja",
    "Carlos","César","Cristian","Daniel","David","Diego","Eduardo",
    "Emilio","Enrique","Ernesto","Esteban","Felipe","Fernando","Francisco",
    "Gabriel","Gonzalo","Guillermo","Gustavo","Héctor","Hugo","Ignacio",
    "Iván","Jaime","Javier","Jorge","José","Juan","Julián","Lorenzo",
    "Lucas","Luis","Manuel","Marcos","Mario","Martín","Mateo","Miguel",
    "Nicolás","Óscar","Pablo","Pedro","Rafael","Raúl","Ricardo","Roberto",
    "Rodrigo","Rubén","Salvador","Santiago","Sergio","Tomás","Víctor",
]

FIRST_NAMES_FEMALE = [
    "Adriana","Alba","Alejandra","Alicia","Ana","Andrea","Beatriz",
    "Blanca","Carla","Carmen","Carolina","Claudia","Cristina","Elena",
    "Elisa","Eva","Gloria","Inés","Irene","Isabel","Jessica","Laura",
    "Lucía","Luna","Marta","María","Marina","Mercedes","Miriam","Mónica",
    "Natalia","Nuria","Olga","Patricia","Pilar","Raquel","Rosa",
    "Sandra","Sara","Silvia","Sofía","Sonia","Teresa","Valentina",
    "Valeria","Verónica","Victoria","Virginia","Yolanda",
]

LAST_NAMES = [
    "García","Martínez","López","Sánchez","González","Rodríguez","Fernández",
    "Pérez","Gómez","Martín","Jiménez","Ruiz","Hernández","Díaz","Moreno",
    "Álvarez","Muñoz","Romero","Alonso","Gutiérrez","Navarro","Torres",
    "Domínguez","Vázquez","Ramos","Gil","Ramírez","Serrano","Blanco",
    "Suárez","Molina","Morales","Ortega","Delgado","Castro","Ortiz",
    "Rubio","Marín","Sanz","Iglesias","Nuñez","Medina","Garrido","Cortés",
    "Castillo","Santos","Lozano","Guerrero","Cano","Prieto","Méndez",
    "Cruz","Calvo","Gallego","Vidal","León","Cabrera","Ibáñez","Herrera",
]


@dataclass
class FakeCustomer:
    email: str
    first_name: str
    last_name: str
    phone: str
    address1: str
    address2: Optional[str]
    city: str
    province_code: str
    state_id: str
    zip_code: str
    country: str
    country_code: str
    dni: str
    fuente: str = "FALLBACK"


def _resolve_province_code(province: str) -> str:
    normalized = province.strip().lower()
    if province.strip().upper() in PROVINCE_PREFIXES:
        return province.strip().upper()
    return PROVINCE_NAME_TO_CODE.get(normalized, province.strip().upper())


def _fetch_address_for_province(province_code: str) -> dict:
    prefix = PROVINCE_PREFIXES.get(province_code)
    static_match = next((a for a in SPAIN_ADDRESSES if a["province_code"] == province_code), SPAIN_ADDRESSES[0])
    real_csv_rows = _load_real_addresses_from_csvs(static_match["state_id"]).get(province_code, [])
    if real_csv_rows:
        return random.choice(real_csv_rows)

    def _province_error_address(zip_code: str = "") -> dict:
        return {
            "address1": "CALLE ERROR",
            "city": "PUEBLO O CIUDAD ERROR",
            "zip_code": zip_code if (zip_code and len(zip_code) == 5 and zip_code.isdigit()) else "00000",
            "province_code": province_code,
            "state_id": static_match["state_id"],
            "fuente": "ERROR_NO_REAL_ADDRESS",
        }

    if prefix:
        for _ in range(5):
            cp = prefix + str(random.randint(1, 999)).zfill(3)
            try:
                url = f"https://api.zippopotam.us/es/{cp}"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                places = data.get("places", [])
                if not places:
                    continue
                city = places[0]["place name"]
                addr = _fetch_address_from_catastro(
                    province_code, city, cp, state_id=static_match["state_id"]
                )
                if addr:
                    return addr
                return _province_error_address(cp)
            except Exception:
                continue
    return _province_error_address()


def _fetch_address_from_cloudsql(province_code: str = None) -> dict:
    """Obtiene dirección de Cloud SQL con fallback a CSV/Catastro."""
    try:
        db_record = None

        if province_code:
            db_record = _address_repo.get_address_by_province(province_code)
            if not db_record:
                print(f"⚠️  No hay datos en Cloud SQL para provincia {province_code}, usando fallback")
        else:
            db_record = _address_repo.get_random_address()

        if db_record:
            addr_dict = format_address_from_db(db_record)
            static_match = next((a for a in SPAIN_ADDRESSES if a["province_code"] == addr_dict["province_code"]), SPAIN_ADDRESSES[0])
            return {
                "address1": addr_dict["address1"],
                "city": addr_dict["city"],
                "zip_code": addr_dict["zip_code"],
                "province_code": addr_dict["province_code"],
                "state_id": static_match["state_id"],
                "fuente": "CloudSQL",
            }
    except Exception as e:
        print(f"❌ Error Cloud SQL: {e}")
    return None


def _fetch_address_from_api(province_code: str = None) -> dict:
    # Primero intentar Cloud SQL
    cloudsql_addr = _fetch_address_from_cloudsql(province_code)
    if cloudsql_addr:
        return cloudsql_addr

    if province_code:
        return _fetch_address_for_province(province_code)
    try:
        with urllib.request.urlopen("https://randomuser.me/api/?nat=es", timeout=5) as resp:
            data = json.loads(resp.read())
        loc = data["results"][0]["location"]
        postcode = str(loc["postcode"]).zfill(5)
        prov_code = PROVINCE_BY_ZIP_PREFIX.get(postcode[:2], "M")
        if prov_code in {"MD", "B", "M"}:
            target_code = "M" if prov_code == "MD" else prov_code
            return _fetch_address_for_province(target_code)
        city = loc["city"]
        static_match = next(
            (a for a in SPAIN_ADDRESSES if a["province_code"] == prov_code), SPAIN_ADDRESSES[0]
        )
        addr = _fetch_address_from_catastro(prov_code, city, postcode, state_id=static_match["state_id"])
        if addr:
            return addr
        _, max_num = _fallback_street(postcode)
        ru_num = int(loc["street"]["number"]) if str(loc["street"]["number"]).isdigit() else max_num
        return {
            "address1":     f"{loc['street']['name']} {min(ru_num, max_num)}",
            "city":         city,
            "zip_code":     postcode,
            "province_code": prov_code,
            "state_id":     static_match["state_id"],
            "fuente":       "RandomUser",
        }
    except Exception:
        addr = random.choice(SPAIN_ADDRESSES)
        street, number = _fallback_street(addr["zip"])
        return {
            "address1":     f"{street} {number}",
            "city":         addr["city"],
            "zip_code":     addr["zip"],
            "province_code": addr["province_code"],
            "state_id":     addr["state_id"],
            "fuente":       "FALLBACK",
        }


class CustomerGenerator:
    def __init__(self, province: str = None):
        self.fake = Faker("es_ES")
        self.province_code = _resolve_province_code(province) if province else None

    def generate(self) -> FakeCustomer:
        first_name = random.choice(FIRST_NAMES_MALE if random.random() < 0.5 else FIRST_NAMES_FEMALE)
        last_name = f"{random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"
        addr = _fetch_address_from_api(self.province_code)
        hex_id = uuid.uuid4().hex[:6]

        address2 = None
        if random.random() < 0.4:
            floor = random.randint(1, 10)
            door = random.choice(["A", "B", "C", "D", "Izq", "Dcha"])
            address2 = f"Piso {floor}, {door}"

        return FakeCustomer(
            email=f"bottest.{_sanitize_for_email(first_name)}.{hex_id}@example.com",
            first_name=first_name,
            last_name=last_name,
            phone=f"+346{random.randint(10000000, 99999999)}",
            address1=addr["address1"],
            address2=address2,
            city=addr["city"],
            province_code=addr["province_code"],
            state_id=addr["state_id"],
            zip_code=addr["zip_code"],
            country="Spain",
            country_code="ES",
            dni=_generate_dni(),
            fuente=addr.get("fuente", "FALLBACK"),
        )
