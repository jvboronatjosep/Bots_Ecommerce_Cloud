# Fallback estático usado si la API de randomuser.me no está disponible
SPAIN_ADDRESSES = [
    {"city": "Madrid",     "province_code": "MD", "zip": "28001"},
    {"city": "Madrid",     "province_code": "MD", "zip": "28013"},
    {"city": "Barcelona",  "province_code": "B",  "zip": "08001"},
    {"city": "Barcelona",  "province_code": "B",  "zip": "08015"},
    {"city": "Valencia",   "province_code": "V",  "zip": "46001"},
    {"city": "Valencia",   "province_code": "V",  "zip": "46010"},
    {"city": "Sevilla",    "province_code": "SE", "zip": "41001"},
    {"city": "Zaragoza",   "province_code": "Z",  "zip": "50001"},
    {"city": "Malaga",     "province_code": "MA", "zip": "29001"},
    {"city": "Bilbao",     "province_code": "BI", "zip": "48001"},
    {"city": "Alicante",   "province_code": "A",  "zip": "03001"},
    {"city": "Granada",    "province_code": "GR", "zip": "18001"},
    {"city": "Murcia",     "province_code": "MU", "zip": "30001"},
    {"city": "Valladolid", "province_code": "VA", "zip": "47001"},
    {"city": "Cordoba",    "province_code": "CO", "zip": "14001"},
    {"city": "Palma",      "province_code": "PM", "zip": "07001"},
    {"city": "Las Palmas", "province_code": "GC", "zip": "35001"},
    {"city": "Santander",  "province_code": "S",  "zip": "39001"},
    {"city": "Pamplona",   "province_code": "NA", "zip": "31001"},
    {"city": "Vitoria",    "province_code": "VI", "zip": "01001"},
]

STREET_NAMES = [
    "Calle Mayor", "Calle del Carmen", "Calle de la Paz",
    "Avenida de la Constitucion", "Calle Gran Via", "Paseo del Prado",
    "Calle de Alcala", "Calle de Serrano", "Avenida de America",
    "Calle de Goya", "Calle de Velazquez", "Paseo de la Castellana",
    "Calle de Fuencarral", "Calle de Atocha", "Calle de Toledo",
    "Rambla de Catalunya", "Passeig de Gracia", "Carrer de Balmes",
    "Calle del Principe", "Calle de la Cruz",
]

# Los primeros 2 dígitos del CP español identifican la provincia de forma unívoca
PROVINCE_BY_ZIP_PREFIX = {
    "01": "VI", "02": "AB", "03": "A",  "04": "AL", "05": "AV",
    "06": "BA", "07": "PM", "08": "B",  "09": "BU", "10": "CC",
    "11": "CA", "12": "CS", "13": "CR", "14": "CO", "15": "C",
    "16": "CU", "17": "GI", "18": "GR", "19": "GU", "20": "SS",
    "21": "H",  "22": "HU", "23": "J",  "24": "LE", "25": "L",
    "26": "LO", "27": "LU", "28": "MD", "29": "MA", "30": "MU",
    "31": "NA", "32": "OR", "33": "O",  "34": "P",  "35": "GC",
    "36": "PO", "37": "SA", "38": "TF", "39": "S",  "40": "SG",
    "41": "SE", "42": "SO", "43": "T",  "44": "TE", "45": "TO",
    "46": "V",  "47": "VA", "48": "BI", "49": "ZA", "50": "Z",
    "51": "CE", "52": "ML",
}
