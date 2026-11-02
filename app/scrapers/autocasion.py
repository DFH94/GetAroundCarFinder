"""Autocasion – parsea los datos estructurados (JSON-LD, lista de Product/Car) de la página de resultados.
Los filtros de precio y km van en la ruta (/precio-desde-5000/precio-hasta-11000/km-hasta-60000);
el año no se puede filtrar por URL, así que se filtra aquí."""
import json
import re

from bs4 import BeautifulSoup

from .base import BaseScraper, log, to_int

BASE = "https://www.autocasion.com/coches-segunda-mano"


class AutocasionScraper(BaseScraper):
    name = "autocasion"
    max_pages = 15

    def _path(self, min_price, max_price, max_km, with_km=True):
        parts = []
        if min_price:
            parts.append(f"precio-desde-{min_price}")
        parts.append(f"precio-hasta-{max_price}")
        if with_km:
            parts.append(f"km-hasta-{max_km}")
        return BASE + "/" + "/".join(parts)

    def _get(self, url, page):
        return self.client.get(url, params={"page": page} if page > 1 else None)

    def fetch_description(self, listing):
        """Comentario del vendedor (si la ficha lo trae ya escrito en el HTML)."""
        try:
            r = self.client.get(listing["url"])
            r.raise_for_status()
            box = BeautifulSoup(r.text, "html.parser").select_one(".comments-box")
            return box.get_text(" ", strip=True)[:1500] if box else ""
        except Exception as e:  # noqa: BLE001
            log.warning("autocasion: no se pudo leer la ficha %s: %s", listing.get("id"), e)
            return None

    def search(self, min_price, max_price, min_year, max_km):
        out, seen, with_km = [], set(), True
        for page in range(1, self.max_pages + 1):
            r = self._get(self._path(min_price, max_price, max_km, with_km), page)
            if r.status_code == 404 and with_km and page == 1:  # combinación de ruta no soportada
                with_km = False
                r = self._get(self._path(min_price, max_price, max_km, with_km), page)
            r.raise_for_status()
            products = []
            for s in BeautifulSoup(r.text, "html.parser").find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string)
                except (TypeError, ValueError):
                    continue
                if isinstance(data, list):
                    products += [x for x in data if isinstance(x, dict) and x.get("@type") == "Product"]
            if not products:
                break
            new = 0
            for p in products:
                offer = p.get("offers") or {}
                car = offer.get("itemOffered") or {}
                ident = car.get("identifier")
                if ident is None or ident in seen:
                    continue
                seen.add(ident)
                new += 1
                year = to_int(car.get("productionDate"))
                km = to_int((car.get("mileageFromOdometer") or {}).get("value"))
                price = to_int(offer.get("price"))
                if not (year and year >= min_year and km is not None and km <= max_km
                        and price and min_price <= price <= max_price):
                    continue
                images = [i for i in (car.get("image") or p.get("image") or []) if isinstance(i, str)]
                title = re.sub(r"-?\d+€$", "", car.get("name") or p.get("name") or "").strip()
                out.append({
                    "id": f"autocasion:{ident}",
                    "source": "autocasion",
                    "title": title,
                    "make": car.get("manufacturer") or (p.get("brand") or {}).get("name"),
                    "model": car.get("model"),
                    "year": year, "km": km, "price": price,
                    "gearbox": car.get("vehicleTransmission"),
                    "body": car.get("bodyType"),
                    "url": offer.get("url"),
                    "image": images[0] if images else None, "images": images,
                })
            if not new:  # página repetida: se acabó el listado
                break
            self.polite_sleep()
        return out
