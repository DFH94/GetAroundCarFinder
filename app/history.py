"""Histórico de precios por modelo: una foto diaria (mínimo, mediana y nº de anuncios únicos)."""
from collections import Counter, defaultdict
from datetime import date
from statistics import median

from .vehicle import norm


def model_key(r: dict) -> str | None:
    make, model = norm(r.get("make")), norm(r.get("model")).split(" ")[0]
    return f"{make}|{model}" if make and model else None


def snapshots(rows: list[dict], day: str | None = None) -> list[dict]:
    """Una fila por modelo con los precios actuales. `rows` ya deben estar deduplicadas."""
    day = day or date.today().isoformat()
    groups, labels = defaultdict(list), defaultdict(Counter)
    for r in rows:
        k = model_key(r)
        if k and r.get("price"):
            groups[k].append(r["price"])
            labels[k][f"{r['make']} {(r.get('model') or '').split(' ')[0]}".strip()] += 1
    return [{"day": day, "model_key": k, "label": labels[k].most_common(1)[0][0],
             "min_price": min(p), "median_price": int(median(p)), "count": len(p)}
            for k, p in groups.items()]
