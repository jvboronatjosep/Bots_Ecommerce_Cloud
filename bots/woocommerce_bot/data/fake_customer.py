import random
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Optional

from faker import Faker

from data.addresses import PROVINCE_PREFIXES, PROVINCE_NAME_TO_CODE
from data.database import CloudSQLConnection, AddressRepository, format_address_from_db

# ── Cloud SQL Database ────────────────────────────────────────────────────────

_db_connection = CloudSQLConnection()
_address_repo = AddressRepository(_db_connection)

# ── Helpers de email / DNI ────────────────────────────────────────────────────

def _sanitize_for_email(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower()) or "user"


def _generate_dni() -> str:
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    number = random.randint(10000000, 99999999)
    return f"{number}{letters[number % 23]}"


# ── Nombres ───────────────────────────────────────────────────────────────────

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


# ── Dataclass ─────────────────────────────────────────────────────────────────

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
    zip_code: str
    country: str
    country_code: str
    dni: str
    fuente: str = "FALLBACK"


# ── Generación de direcciones ─────────────────────────────────────────────────

def _resolve_province_code(province: str) -> str:
    """Resuelve un código de provincia desde nombre o código."""
    normalized = province.strip().lower()
    if province.strip().upper() in PROVINCE_PREFIXES:
        return province.strip().upper()
    return PROVINCE_NAME_TO_CODE.get(normalized, province.strip().upper())


def _fetch_address_from_cloudsql(province_code: str = None) -> dict:
    """
    Obtiene dirección exclusivamente de Cloud SQL.

    Si province_code es proporcionado, intenta obtener de esa provincia.
    Si no hay datos de esa provincia, obtiene una dirección aleatoria.
    Si no se proporciona provincia, obtiene aleatoria de todo.
    """
    try:
        db_record = None

        if province_code:
            db_record = _address_repo.get_address_by_province(province_code)
            if not db_record:
                print(f"⚠️  No hay datos para provincia {province_code}, usando aleatoria")
                db_record = _address_repo.get_random_address()
        else:
            db_record = _address_repo.get_random_address()

        if db_record:
            return format_address_from_db(db_record)
        else:
            raise Exception("No address found in CloudSQL")
    except Exception as e:
        print(f"❌ Error fetching address from CloudSQL: {e}")
        return {
            "address1": "CALLE ERROR",
            "zip_code": "00000",
            "city": "ERROR",
            "province_code": "XX",
            "country": "Spain",
            "country_code": "ES",
            "fuente": "ERROR",
        }


# ── CustomerGenerator ─────────────────────────────────────────────────────────

class CustomerGenerator:
    def __init__(self, province: str = None):
        self.fake = Faker("es_ES")
        self.province_code = _resolve_province_code(province) if province else None

    def generate(self) -> FakeCustomer:
        first_name = random.choice(FIRST_NAMES_MALE if random.random() < 0.5 else FIRST_NAMES_FEMALE)
        last_name = f"{random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"
        addr = _fetch_address_from_cloudsql(self.province_code)
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
            zip_code=addr["zip_code"],
            country="Spain",
            country_code="ES",
            dni=_generate_dni(),
            fuente=addr.get("fuente", "FALLBACK"),
        )
