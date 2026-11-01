"""Detección de gangas y rentabilidad estimada en GetAround."""
from collections import defaultdict
from statistics import median


def _norm(s):
    return (s or "").strip().lower()


def hourly_rate(price: int) -> float:
    """Tarifa/hora estimada en GetAround según segmento (aprox. mercado España)."""
    if price < 8000:
        return 6.0
    if price < 12000:
        return 7.5
    if price < 16000:
        return 9.0
    return 11.0


def compute(rows: list[dict], cfg: dict) -> list[dict]:
    eco = cfg["economics"]
    # Índices por marca: comparables con el mismo modelo (completo y luego 1ª palabra) y año ±1
    by_make = defaultdict(list)
    for r in rows:
        if r.get("price") and r.get("make") and r.get("year"):
            by_make[_norm(r["make"])].append(r)

    def comparables(r):
        make, model = _norm(r.get("make")), _norm(r.get("model"))
        year = r.get("year")
        if not (make and year):
            return []
        pool = [c for c in by_make.get(make, []) if abs(c["year"] - year) <= 1]
        for words in (2, 1):
            key = " ".join(model.split(" ")[:words])
            comps = [c["price"] for c in pool if " ".join(_norm(c["model"]).split(" ")[:words]) == key]
            if len(comps) >= cfg["min_comparables"]:
                return comps
        return []

    out = []
    for r in rows:
        price = r.get("price") or 0
        comps = comparables(r)
        med = int(median(comps)) if comps else None
        disc = round((med - price) / med * 100, 1) if med and price else None
        is_deal = int(bool(disc is not None and disc >= cfg["deal_threshold_pct"]))

        revenue = hourly_rate(price) * eco["rented_hours_month"]
        net = revenue * (1 - eco["getaround_commission_pct"] / 100) - eco["monthly_fixed_costs"]
        payback = round(price / net, 1) if net > 0 and price else None

        out.append({"id": r["id"], "median_price": med, "discount_pct": disc,
                    "is_deal": is_deal, "monthly_profit": int(net), "payback_months": payback})
    return out
