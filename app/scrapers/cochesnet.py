"""coches.net – usa el endpoint JSON que consume su web."""
from .base import BaseScraper, to_int


class CochesNetScraper(BaseScraper):
    name = "cochesnet"
    API = "https://ms-mt--api-web.spain.advgo.net/search"

    def search(self, min_price, max_price, min_year, max_km):
        out = []
        headers = {"x-adevinta-channel": "web-desktop", "x-schibsted-tenant": "coches",
                   "Content-Type": "application/json", "Origin": "https://www.coches.net",
                   "Referer": "https://www.coches.net/"}
        for page in range(1, self.max_pages + 1):
            body = {
                "pagination": {"page": page, "size": 30},
                "sort": {"order": "asc", "term": "price"},
                "filters": {
                    "price": {"from": min_price, "to": max_price},
                    "year": {"from": min_year, "to": None},
                    "km": {"from": None, "to": max_km},
                    "categories": {"category1Ids": [2500]},
                    "offerTypeIds": [0, 2, 3, 4, 5],
                    "isFinanced": False,
                },
            }
            r = self.client.post(self.API, json=body, headers=headers)
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                break
            for it in items:
                res = it.get("resources") or []
                out.append({
                    "id": f"cochesnet:{it.get('id')}",
                    "source": "cochesnet",
                    "title": it.get("title"),
                    "make": it.get("make"), "model": it.get("model"),
                    "year": to_int(it.get("year")), "km": to_int(it.get("km")),
                    "price": to_int((it.get("price") or {}).get("amount")),
                    "fuel": it.get("fuelType"), "gearbox": it.get("transmissionType"),
                    "location": it.get("mainProvince"),
                    "url": "https://www.coches.net" + (it.get("url") or ""),
                    "image": res[0].get("url") if res else None,
                })
            self.polite_sleep()
        return out
