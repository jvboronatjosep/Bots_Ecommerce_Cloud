import json
import random
import re
import unicodedata
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Optional

from faker import Faker

from data.addresses import (
    SPAIN_ADDRESSES, STREET_NAMES,
    PROVINCE_BY_ZIP_PREFIX, PROVINCE_PREFIXES, PROVINCE_NAME_TO_CODE,
)


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
    state_id: str
    zip_code: str
    country: str
    country_code: str
    dni: str


FIRST_NAMES_MALE = [
    "Alejandro", "Alfonso", "Álvaro", "Andrés", "Antonio", "Arturo", "Borja",
    "Carlos", "César", "Cristian", "Daniel", "David", "Diego", "Eduardo",
    "Emilio", "Enrique", "Ernesto", "Esteban", "Felipe", "Fernando", "Francisco",
    "Gabriel", "Gonzalo", "Guillermo", "Gustavo", "Héctor", "Hugo", "Ignacio",
    "Iván", "Jaime", "Javier", "Jorge", "José", "Juan", "Julián", "Lorenzo",
    "Lucas", "Luis", "Manuel", "Marcos", "Mario", "Martín", "Mateo", "Miguel",
    "Nicolás", "Óscar", "Pablo", "Pedro", "Rafael", "Raúl", "Ricardo", "Roberto",
    "Rodrigo", "Rubén", "Salvador", "Santiago", "Sergio", "Tomás", "Víctor",
]

FIRST_NAMES_FEMALE = [
    "Adriana", "Alba", "Alejandra", "Alicia", "Ana", "Andrea", "Beatriz",
    "Blanca", "Carla", "Carmen", "Carolina", "Claudia", "Cristina", "Elena",
    "Elisa", "Eva", "Gloria", "Inés", "Irene", "Isabel", "Jessica", "Laura",
    "Lucía", "Luna", "Marta", "María", "Marina", "Mercedes", "Miriam", "Mónica",
    "Natalia", "Nuria", "Olga", "Patricia", "Pilar", "Raquel", "Rosa",
    "Sandra", "Sara", "Silvia", "Sofía", "Sonia", "Teresa", "Valentina",
    "Valeria", "Verónica", "Victoria", "Virginia", "Yolanda",
]

LAST_NAMES = [
    "García", "Martínez", "López", "Sánchez", "González", "Rodríguez", "Fernández",
    "Pérez", "Gómez", "Martín", "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno",
    "Álvarez", "Muñoz", "Romero", "Alonso", "Gutiérrez", "Navarro", "Torres",
    "Domínguez", "Vázquez", "Ramos", "Gil", "Ramírez", "Serrano", "Blanco",
    "Suárez", "Molina", "Morales", "Ortega", "Delgado", "Castro", "Ortiz",
    "Rubio", "Marín", "Sanz", "Iglesias", "Nuñez", "Medina", "Garrido", "Cortés",
    "Castillo", "Santos", "Lozano", "Guerrero", "Cano", "Prieto", "Méndez",
    "Cruz", "Calvo", "Gallego", "Vidal", "León", "Cabrera", "Ibáñez", "Herrera",
    "Arias", "Mora", "Vargas", "Carmona", "Crespo", "Campos", "Bravo", "Reyes",
    "Vicente", "Esteban", "Fuentes", "Carrasco", "Aguilar", "Pascual", "Herrero",
]


def _resolve_province_code(province: str) -> str:
    normalized = province.strip().lower()
    if province.strip().upper() in PROVINCE_PREFIXES:
        return province.strip().upper()
    return PROVINCE_NAME_TO_CODE.get(normalized, province.strip().upper())


def _fetch_street_from_randomuser() -> str:
    try:
        with urllib.request.urlopen("https://randomuser.me/api/?nat=es", timeout=5) as resp:
            data = json.loads(resp.read())
        loc = data["results"][0]["location"]
        return f"{loc['street']['name']} {loc['street']['number']}"
    except Exception:
        return f"{random.choice(STREET_NAMES)} {random.randint(1, 150)}"


def _fetch_address_for_province(province_code: str) -> dict:
    prefix = PROVINCE_PREFIXES.get(province_code)
    if prefix:
        for _ in range(5):
            cp = prefix + str(random.randint(1, 999)).zfill(3)
            try:
                url = f"https://api.zippopotam.us/es/{cp}"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                places = data.get("places", [])
                if places:
                    city = places[0]["place name"]
                    street = _fetch_street_from_randomuser()
                    # state_id is resolved dynamically from the DOM in checkout_handler
                    static = next((a for a in SPAIN_ADDRESSES if a["province_code"] == province_code), SPAIN_ADDRESSES[0])
                    return {
                        "address1": street, "city": city, "zip_code": cp,
                        "province_code": province_code, "state_id": static["state_id"],
                    }
            except Exception:
                continue

    province_addrs = [a for a in SPAIN_ADDRESSES if a["province_code"] == province_code]
    if not province_addrs:
        province_addrs = SPAIN_ADDRESSES
    addr = random.choice(province_addrs)
    return {
        "address1": f"{random.choice(STREET_NAMES)} {random.randint(1, 150)}",
        "city": addr["city"],
        "zip_code": addr["zip"],
        "province_code": addr["province_code"],
        "state_id": addr["state_id"],
    }


def _fetch_address_from_api(province_code: str = None) -> dict:
    if province_code:
        return _fetch_address_for_province(province_code)
    try:
        with urllib.request.urlopen("https://randomuser.me/api/?nat=es", timeout=5) as resp:
            data = json.loads(resp.read())
        loc = data["results"][0]["location"]
        postcode = str(loc["postcode"]).zfill(5)
        prov_code = PROVINCE_BY_ZIP_PREFIX.get(postcode[:2], "M")
        static = next((a for a in SPAIN_ADDRESSES if a["province_code"] == prov_code), SPAIN_ADDRESSES[0])
        return {
            "address1": f"{loc['street']['name']} {loc['street']['number']}",
            "city": loc["city"],
            "zip_code": postcode,
            "province_code": prov_code,
            "state_id": static["state_id"],
        }
    except Exception:
        addr = random.choice(SPAIN_ADDRESSES)
        return {
            "address1": f"{random.choice(STREET_NAMES)} {random.randint(1, 150)}",
            "city": addr["city"],
            "zip_code": addr["zip"],
            "province_code": addr["province_code"],
            "state_id": addr["state_id"],
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
        )
