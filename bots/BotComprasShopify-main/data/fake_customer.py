import json
import random
import re
import unicodedata
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from faker import Faker

from data.addresses import (
    SPAIN_ADDRESSES,
    PROVINCE_BY_ZIP_PREFIX, PROVINCE_PREFIXES, PROVINCE_NAME_TO_CODE,
)


class CatastroUnavailableError(Exception):
    """
    El servicio OVCCatastro no devolvió datos verificados.
    No se generará una dirección inventada. La order debe reintentarse.
    """

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


def _fetch_address_from_catastro(province_code: str, city: str, cp: str) -> Optional[dict]:
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
        "fuente":       "OVCCatastro",
    }


def _sanitize_for_email(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower()) or "user"


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
    fuente: str = "FALLBACK"


def _resolve_province_code(province: str) -> str:
    normalized = province.strip().lower()
    if province.strip().upper() in PROVINCE_PREFIXES:
        return province.strip().upper()
    return PROVINCE_NAME_TO_CODE.get(normalized, province.strip().upper())


def _fetch_address_for_province(province_code: str) -> dict:
    """
    Modo Paranoico: solo devuelve direcciones confirmadas por el Catastro.
    Intenta hasta 15 CPs distintos. Último recurso: capital de provincia.
    Si todo falla → CatastroUnavailableError (nunca inventa una dirección).
    """
    prefix = PROVINCE_PREFIXES.get(province_code)
    if prefix:
        for _ in range(15):
            cp = prefix + str(random.randint(1, 999)).zfill(3)
            try:
                url = f"https://api.zippopotam.us/es/{cp}"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                places = data.get("places", [])
                if not places:
                    continue
                city = places[0]["place name"]
                addr = _fetch_address_from_catastro(province_code, city, cp)
                if addr:
                    return addr
            except Exception:
                continue

    # Último recurso: capital de provincia conocida
    static = next((a for a in SPAIN_ADDRESSES if a["province_code"] == province_code), None)
    if static:
        addr = _fetch_address_from_catastro(province_code, static["city"], static["zip"])
        if addr:
            return addr

    raise CatastroUnavailableError(
        f"Catastro no devolvió datos verificados para provincia={province_code}. "
        "La order debe reintentarse cuando el servicio esté disponible."
    )


def _fetch_address_from_api(province_code: str = None) -> dict:
    """
    Modo Paranoico: solo devuelve direcciones confirmadas por el Catastro.
    Intenta con randomuser.me primero; si falla, prueba 15 CPs aleatorios.
    Si todo falla → CatastroUnavailableError (nunca inventa una dirección).
    """
    if province_code:
        return _fetch_address_for_province(province_code)

    try:
        with urllib.request.urlopen("https://randomuser.me/api/?nat=es", timeout=5) as resp:
            data = json.loads(resp.read())
        loc = data["results"][0]["location"]
        postcode = str(loc["postcode"]).zfill(5)
        prov_code = PROVINCE_BY_ZIP_PREFIX.get(postcode[:2], "M")
        city = loc["city"]
        addr = _fetch_address_from_catastro(prov_code, city, postcode)
        if addr:
            return addr
        # randomuser dio ciudad pero Catastro no respondió → probar otros CPs
        return _fetch_address_for_province(prov_code)
    except CatastroUnavailableError:
        raise
    except Exception:
        pass

    # randomuser.me no disponible → intentar con una provincia aleatoria
    prov_code = random.choice(list(PROVINCE_PREFIXES.keys()))
    return _fetch_address_for_province(prov_code)


class CustomerGenerator:
    def __init__(self, province: str = None):
        self.fake = Faker("es_ES")
        self.province_code = _resolve_province_code(province) if province else None

    def generate(self) -> FakeCustomer:
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        addr = _fetch_address_from_api(self.province_code)
        hex_id = uuid.uuid4().hex[:6]

        address2 = None
        if random.random() < 0.3:
            address2 = f"Piso {random.randint(1, 10)}, {random.choice('ABCD')}"

        return FakeCustomer(
            email=f"bottest.{_sanitize_for_email(first_name)}.{_sanitize_for_email(last_name)}.{hex_id}@example.com",
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
            fuente=addr.get("fuente", "FALLBACK"),
        )
