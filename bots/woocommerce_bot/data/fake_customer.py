import json
import random
import re
import unicodedata
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Optional
from faker import Faker
from data.addresses import SPAIN_ADDRESSES, STREET_NAMES, PROVINCE_BY_ZIP_PREFIX

def _sanitize_for_email(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-z0-9]", "", ascii_text.lower())
    return ascii_text or "user"

def _generate_dni() -> str:
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    number = random.randint(10000000, 99999999)
    letter = letters[number % 23]
    return f"{number}{letter}"

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

def _fetch_address_from_api() -> dict:
    """Obtiene una dirección española real desde randomuser.me. Fallback al array estático si falla."""
    try:
        with urllib.request.urlopen("https://randomuser.me/api/?nat=es", timeout=5) as resp:
            data = json.loads(resp.read())
        loc = data["results"][0]["location"]
        postcode = str(loc["postcode"]).zfill(5)
        province_code = PROVINCE_BY_ZIP_PREFIX.get(postcode[:2], "MD")
        return {
            "address1": f"{loc['street']['name']} {loc['street']['number']}",
            "city": loc["city"],
            "zip_code": postcode,
            "province_code": province_code,
        }
    except Exception:
        addr = random.choice(SPAIN_ADDRESSES)
        street = random.choice(STREET_NAMES)
        return {
            "address1": f"{street} {random.randint(1, 150)}",
            "city": addr["city"],
            "zip_code": addr["zip"],
            "province_code": addr["province_code"],
        }


class CustomerGenerator:
    def __init__(self):
        self.fake = Faker("es_ES")

    def generate(self) -> FakeCustomer:
        first_name = random.choice(FIRST_NAMES_MALE if random.random() < 0.5 else FIRST_NAMES_FEMALE)
        last_name = f"{random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"
        addr = _fetch_address_from_api()
        hex_id = uuid.uuid4().hex[:6]
        address2 = None
        if random.random() < 0.4:
            floor = random.randint(1, 10)
            door = random.choice(["A","B","C","D","Izq","Dcha"])
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
        )
