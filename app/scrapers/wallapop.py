"""Wallapop – API JSON pública de búsqueda (categoría Coches = 100)."""
from .base import BaseScraper, to_int


class WallapopScraper(BaseScraper):
    name = "wallapop"

    def search(self, min_price, max_price, min_year, max_km):
        out, next_page = [], None
        headers = {"X-DeviceOS": "0", "Accept": "application/json"}
        for _ in range(self.max_pages):
            params = {
                "category_id": 100, "source": "search_box",
                "latitude": 40.4168, "longitude": -3.7038, "distance_in_km": 1000,  # toda España
                "min_sale_price": min_price, "max_sale_price": max_price,
                "min_year": min_year, "max_km": max_km,
                "body_type": "sedan,family_car,4X4,minivan",
                "order_by": "price_low_to_high",
            }
            if next_page:
                params = {"next_page": next_page}
            r = self.client.get("https://api.wallapop.com/api/v3/search", params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
            items = (data.get("data", {}).get("section", {}).get("payload", {}).get("items")
                     or data.get("search_objects") or [])
            for it in items:
                car = it.get("type_attributes") or it.get("car_info") or {}
                price = it.get("price", {})
                price = price.get("amount") if isinstance(price, dict) else price
                imgs = it.get("images") or []
                gallery = [(i.get("urls") or {}).get("big") or (i.get("urls") or {}).get("medium")
                           for i in imgs if isinstance(i, dict)]
                gallery = [g for g in gallery if g]
                img = gallery[0] if gallery else None
                loc = it.get("location", {})
                out.append({
                    "id": f"wallapop:{it.get('id')}",
                    "source": "wallapop",
                    "title": it.get("title"),
                    "description": (it.get("description") or "")[:1500],
                    "make": car.get("brand") or (car.get("brand", {}) if isinstance(car.get("brand"), str) else None),
                    "model": car.get("model"),
                    "year": to_int(car.get("year")),
                    "km": to_int(car.get("km")),
                    "price": to_int(price),
                    "fuel": car.get("engine") or car.get("fuel"),
                    "gearbox": car.get("gearbox"),
                    "body": car.get("body_type"),
                    "location": loc.get("city") if isinstance(loc, dict) else None,
                    "province": loc.get("region2") if isinstance(loc, dict) else None,
                    "postal": loc.get("postal_code") if isinstance(loc, dict) else None,
                    "url": f"https://es.wallapop.com/item/{it.get('web_slug')}",
                    "image": img, "images": gallery,
                })
            next_page = data.get("meta", {}).get("next_page")
            if not next_page:
                break
            self.polite_sleep()
        return out
