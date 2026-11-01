"""Flexicar – API JSON que consume su web (services.flexicar.es), paginada de 12 en 12.
Flexicar es un concesionario con coches garantizados, así que no hay anuncios de particulares."""
from .base import BaseScraper, to_int


class FlexicarScraper(BaseScraper):
    name = "flexicar"
    max_pages = 15
    API = "https://services.flexicar.es/api/v1/vehicles"

    def search(self, min_price, max_price, min_year, max_km):
        out = []
        for page in range(1, self.max_pages + 1):
            params = {"priceFrom": min_price, "priceTo": max_price, "yearFrom": min_year,
                      "kmTo": max_km, "page": page}
            r = self.client.get(self.API, params=params)
            r.raise_for_status()
            data = r.json()
            for v in data.get("results") or []:
                if v.get("reserved"):
                    continue
                images = [i for i in (v.get("images") or []) if isinstance(i, str)]
                image = v.get("image") or (images[0] if images else None)
                out.append({
                    "id": f"flexicar:{v.get('id')}",
                    "source": "flexicar",
                    "title": f"{v.get('brand', '')} {v.get('model', '')} {v.get('version') or ''}".strip(),
                    "make": v.get("brand"), "model": v.get("model"),
                    "year": to_int(v.get("year")), "km": to_int(v.get("km")),
                    "price": to_int(v.get("price")),
                    "fuel": v.get("fuel"), "gearbox": v.get("transmission"),
                    "location": v.get("carDealership"),
                    "url": f"https://www.flexicar.es/coches-ocasion/{v.get('slug')}",
                    "image": image, "images": images or ([image] if image else []),
                })
            if not data.get("hasNext"):
                break
            self.polite_sleep()
        return out
