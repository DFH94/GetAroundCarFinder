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
    groups = defaultdict(list)
    for r in rows:
        if r.get("price") and r.get("make"):
            groups[(_norm(r["make"]), _norm(r["model"]).split(" ")[0], r.get("year"))].append(r["price"])

    out = []
    for r in rows:
        price = r.get("price") or 0
        key = (_norm(r.get("make")), _norm(r.get("model")).split(" ")[0], r.get("year"))
        comps = groups.get(key, [])
        med = int(median(comps)) if len(comps) >= cfg["min_comparables"] else None
        disc = round((med - price) / med * 100, 1) if med and price else None
        is_deal = int(bool(disc is not None and disc >= cfg["deal_threshold_pct"]))

        revenue = hourly_rate(price) * eco["rented_hours_month"]
        net = revenue * (1 - eco["getaround_commission_pct"] / 100) - eco["monthly_fixed_costs"]
        payback = round(price / net, 1) if net > 0 and price else None

        out.append({"id": r["id"], "median_price": med, "discount_pct": disc,
                    "is_deal": is_deal, "monthly_profit": int(net), "payback_months": payback})
    return out
