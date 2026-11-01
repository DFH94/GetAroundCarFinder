"""Clasificación de carrocería: solo berlinas o superior (berlina, familiar, SUV, monovolumen).
Excluye motos, quads, furgonetas, microcoches, utilitarios pequeños, etc."""
import re
import unicodedata

BODY_TYPES = {
    "berlina": "Berlina",
    "familiar": "Familiar / Ranchera",
    "suv": "SUV / Todoterreno",
    "monovolumen": "Monovolumen",
}

# Palabras que descartan el anuncio siempre
EXCLUDE = [
    "moto", "motocicleta", "scooter", "quad", "atv", "buggy", "kart", "ciclomotor", "trimoto",
    "furgon", "furgoneta", "camion", "autocaravana", "caravana", "camper", "tractor", "remolque",
    "microcar", "sin carnet", "sin carne", "aixam", "ligier", "chatenet", "microcoche",
    "despiece", "piezas", "averiado", "siniestro", "accidentado", "no arranca", "golpe", "golpeado",
    "granizo", "inundado", "para reparar",
    "yamaha", "kawasaki", "ducati", "ktm", "harley", "piaggio", "vespa", "kymco", "sym ", "can-am", "polaris",
]

# Valores de carrocería que devuelven los portales -> tipo normalizado
BODY_MAP = {
    "sedan": "berlina", "berlina": "berlina", "saloon": "berlina", "limousine": "berlina",
    "family_car": "familiar", "familiar": "familiar", "ranchera": "familiar", "estate": "familiar",
    "station wagon": "familiar", "wagon": "familiar", "touring": "familiar",
    "4x4": "suv", "suv": "suv", "todoterreno": "suv", "off-road": "suv", "pick-up": None, "crossover": "suv",
    "minivan": "monovolumen", "monovolumen": "monovolumen", "mpv": "monovolumen", "van": None,
    "small_car": None, "compacto": None, "utilitario": None, "coupe": None, "coupe_cabrio": None,
    "cabrio": None, "descapotable": None,
}

# Modelos de berlina/superior con buena demanda de alquiler (para anuncios sin carrocería)
MODELS = {
    "berlina": ["corolla sedan", "camry", "octavia", "superb", "passat", "arteon", "jetta", "508", "talisman",
                "insignia", "mondeo", "a4", "a6", "serie 3", "serie 5", "3 series", "5 series", "clase c",
                "c-class", "clase e", "model 3", "i30 fastback", "elantra", "ioniq 6", "k5", "optima",
                "mazda6", "mazda 6", "civic sedan", "accord", "giulia", "s60", "s90", "c5 x", "c-elysee",
                "xceed", "toledo", "rapid", "scala", "megane sedan", "tipo"],
    "familiar": ["octavia combi", "superb combi", "leon st", "leon sportstourer", "corolla touring",
                 "passat variant", "golf variant", "ceed sw", "ceed tourer", "i30 cw", "308 sw", "508 sw",
                 "megane sport tourer", "focus sportbreak", "a4 avant", "a6 avant", "touring", "v60", "v90"],
    "suv": ["qashqai", "x-trail", "juke", "tucson", "kona", "santa fe", "bayon", "sportage", "niro", "sorento",
            "stonic", "seltos", "3008", "5008", "2008", "4008", "kadjar", "austral", "arkana", "captur", "koleos",
            "c-hr", "rav4", "rav-4", "yaris cross", "corolla cross", "ateca", "arona", "tarraco", "formentor",
            "karoq", "kodiaq", "kamiq", "enyaq", "tiguan", "t-roc", "t-cross", "taigo", "touareg", "id.4",
            "x1", "x2", "x3", "q2", "q3", "q5", "gla", "glb", "glc", "puma", "kuga", "ecosport", "mokka",
            "grandland", "crossland", "c3 aircross", "c5 aircross", "duster", "jogger", "cx-3", "cx-30", "cx-5",
            "hr-v", "cr-v", "zr-v", "outlander", "eclipse cross", "asx", "vitara", "s-cross", "compass",
            "renegade", "model y", "xc40", "xc60", "evoque", "mg zs", "zs", "hs", "ehs", "marvel r", "atto 3",
            "tonale", "ds 7", "ds7", "ds 3", "sandero stepway", "omoda 5", "jaecoo 7", "tiggo"],
    "monovolumen": ["touran", "sharan", "alhambra", "scenic", "grand scenic", "rifter", "berlingo", "c4 picasso",
                    "c4 spacetourer", "zafira", "s-max", "galaxy", "5008", "carens", "sportsvan", "multivan",
                    "lodgy", "jogger", "kangoo combi"],
}

KNOWN_MAKES = ["Alfa Romeo", "Land Rover", "Mercedes-Benz", "Mercedes", "Aston Martin", "Lynk & Co", "DS",
               "Audi", "BMW", "BYD", "Citroen", "Citroën", "Cupra", "Dacia", "Fiat", "Ford", "Honda", "Hyundai",
               "Jaguar", "Jeep", "Kia", "Lexus", "Mazda", "MG", "Mini", "Mitsubishi", "Nissan", "Opel",
               "Peugeot", "Polestar", "Renault", "Seat", "Skoda", "Smart", "SsangYong", "Subaru", "Suzuki",
               "Tesla", "Toyota", "Volkswagen", "VW", "Volvo", "Omoda", "Jaecoo", "Chery"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def split_make_model(title: str):
    """Extrae marca y modelo de un título libre (Milanuncios)."""
    t = norm(title)
    for mk in sorted(KNOWN_MAKES, key=len, reverse=True):
        if t.startswith(norm(mk) + " "):
            rest = (title or "").strip()[len(mk):].strip().split(" ")
            return mk, " ".join(rest[:2])
    parts = (title or "").split(" ")
    return parts[0], " ".join(parts[1:3])


def classify(listing: dict) -> str | None:
    """Devuelve el tipo de carrocería normalizado o None si no es berlina o superior."""
    text = norm(f"{listing.get('title') or ''} {listing.get('make') or ''} {listing.get('model') or ''}")
    if any(re.search(rf"(^|[^a-z0-9]){re.escape(norm(k))}([^a-z0-9]|$)", text) for k in EXCLUDE):
        return None
    body = norm(listing.get("body") or "")
    if body:
        for k, v in BODY_MAP.items():
            if k in body:
                return v  # puede ser None (utilitario, coupé...)
    # Sin carrocería: buscamos el modelo (primero los más específicos)
    for btype in ["familiar", "monovolumen", "suv", "berlina"]:
        for m in MODELS[btype]:
            if re.search(rf"(^|\s){re.escape(m)}(\s|$)", text):
                return btype
    return None
