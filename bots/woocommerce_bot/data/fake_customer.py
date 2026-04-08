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

# Cache en memoria: evita repetir llamadas al Catastro para la misma ciudad
_street_cache: dict[str, list[dict]] = {}   # "PROVINCIA:CIUDAD" → [{tipo_via, nombre_via}]
_number_cache: dict[str, list[str]] = {}    # "PROVINCIA:CIUDAD:TV:NV" → ["1","3","5",...]


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
    """Busca elementos por tag con o sin namespace del Catastro."""
    result = list(root.iter(_catastro_tag(tag)))
    return result if result else list(root.iter(tag))


def _find_text(elem: ET.Element, tag: str) -> str:
    """Devuelve el texto de un sub-elemento, con o sin namespace."""
    child = elem.find(_catastro_tag(tag))
    if child is None:
        child = elem.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _catastro_callejero(province_name: str, city: str) -> list[dict]:
    """Devuelve la lista de vías de un municipio vía Catastro (con caché)."""
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
    """
    Consulta los portales reales de una vía en el Catastro.
    Devuelve {"numbers": [...], "cp": "08015"} con caché.
    El campo "cp" es el CP oficial de esa vía según el Catastro.
    """
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
            # El CP de la vía está en <cp> dentro de <have>
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
    """
    Construye una dirección real consultando el Catastro.

    Prioridad:
      1. Calles cuyo <cp> devuelto por ConsultaNumero coincide con el CP objetivo.
      2. Calles con portales pero de otro sector (si el paso 1 falla).
    """
    province_name = PROVINCE_CODE_TO_NAME.get(province_code)
    if not province_name:
        return None

    streets = _catastro_callejero(province_name, city)
    if not streets:
        return None

    # Consulta hasta 15 vías aleatorias y clasifica por coincidencia de CP
    sample = random.sample(streets, min(15, len(streets)))
    cp_match: list[tuple] = []    # (street, numbers) con CP exacto
    cp_other: list[tuple] = []    # (street, numbers) con CP distinto o sin CP

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

    # Elige de las calles que sí pertenecen al CP; si no hay, usa el resto
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
        prov_code = PROVINCE_BY_ZIP_PREFIX.get(postcode[:2], "MD")
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


# ── CustomerGenerator ─────────────────────────────────────────────────────────

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
            zip_code=addr["zip_code"],
            country="Spain",
            country_code="ES",
            dni=_generate_dni(),
            fuente=addr.get("fuente", "FALLBACK"),
        )
