"""Deduplicación: el mismo coche publicado varias veces (p. ej. un grupo de concesionarios
lo anuncia en distintas ciudades) se muestra y se puntúa una sola vez."""
from collections import defaultdict

from .vehicle import norm


def same_car_key(r: dict):
    if not (r.get("make") and r.get("year") and r.get("km") is not None and r.get("price")):
        return None  # sin datos suficientes no se puede asegurar que sea el mismo coche
    key = (norm(r["make"]), norm(r.get("model") or ""), r["year"], r["km"], r["price"])
    if r["km"] % 1000 == 0:  # km redondos son poco distintivos: se exige también el mismo título
        key += (norm(r.get("title") or ""),)
    return key


def _best(group: list[dict]) -> dict:
    """Representante: más fotos, y a igualdad el visto antes."""
    return min(group, key=lambda r: (-len(r.get("images") or []), r.get("first_seen") or "", r["id"]))


def dedupe(rows: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    """Devuelve (filas únicas, {id_representante: [duplicados]}). Conserva el orden de entrada."""
    groups, order = defaultdict(list), []
    for r in rows:
        k = same_car_key(r) or ("único", r["id"])
        if k not in groups:
            order.append(k)
        groups[k].append(r)
    kept, dups = [], {}
    for k in order:
        g = groups[k]
        best = _best(g)
        kept.append(best)
        if len(g) > 1:
            dups[best["id"]] = [r for r in g if r["id"] != best["id"]]
    return kept, dups
