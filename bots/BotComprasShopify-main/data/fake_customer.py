import random
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Optional

from faker import Faker

from data.addresses import SPAIN_ADDRESSES, STREET_NAMES


def _sanitize_for_email(text: str) -> str:
    """Remove accents, spaces, and non-ASCII characters for email-safe strings."""
    # Decompose unicode and strip accent marks
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    # Lowercase, replace spaces/special chars with nothing
    ascii_text = re.sub(r"[^a-z0-9]", "", ascii_text.lower())
    return ascii_text or "user"


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


class CustomerGenerator:
    def __init__(self):
        self.fake = Faker("es_ES")

    def generate(self) -> FakeCustomer:
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        addr = random.choice(SPAIN_ADDRESSES)
        street_number = random.randint(1, 150)
        street = random.choice(STREET_NAMES)
        hex_id = uuid.uuid4().hex[:6]

        address2 = None
        if random.random() < 0.3:
            address2 = f"Piso {random.randint(1, 10)}, {random.choice('ABCD')}"

        return FakeCustomer(
            email=f"bottest.{_sanitize_for_email(first_name)}.{_sanitize_for_email(last_name)}.{hex_id}@example.com",
            first_name=first_name,
            last_name=last_name,
            phone=f"+346{random.randint(10000000, 99999999)}",
            address1=f"{street} {street_number}",
            address2=address2,
            city=addr["city"],
            province_code=addr["province_code"],
            zip_code=addr["zip"],
            country="Spain",
            country_code="ES",
        )
