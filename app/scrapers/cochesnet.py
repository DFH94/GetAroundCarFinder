"""coches.net – parsea el estado inicial embebido (window.__INITIAL_PROPS__) de la página de resultados.
Tiene protección anti-bot: tras unas pocas peticiones seguidas sirve una página de verificación.
Por eso se pagina despacio y, si se detecta el bloqueo, se devuelve lo obtenido hasta ese momento."""
import json
import logging
import random
import re
import time

from .base import BaseScraper, to_int

log = logging.getLogger("scraper")

PROPS = re.compile(r"window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\((\".*?\")\);", re.S)


class CochesNetScraper(BaseScraper):
    name = "cochesnet"
    max_pages = 5
    URL = "https://www.coches.net/segunda-mano/"

    def polite_sleep(self):
        time.sleep(random.uniform(8, 14))

    def search(self, min_price, max_price, min_year, max_km):
        out = []
        for page in range(1, self.max_pages + 1):
            params = {"MinPrice": min_price, "MaxPrice": max_price, "MinYear": min_year,
                      "MaxKms": max_km, "pg": page}
            r = self.client.get(self.URL, params=params)
            r.raise_for_status()
            m = PROPS.search(r.text)
            if not m:
                log.warning("cochesnet: bloqueado por el anti-bot en la página %d (se reintentará en la próxima búsqueda)", page)
                break
            items = (json.loads(json.loads(m.group(1))).get("initialResults") or {}).get("items") or []
            if not items:
                break
            for it in items:
                year, km, price = to_int(it.get("year")), to_int(it.get("km")), to_int(it.get("price"))
                if not (year and year >= min_year and km is not None and km <= max_km
                        and price and min_price <= price <= max_price):
                    continue  # los filtros de la URL pueden no aplicarse: se filtra aquí también
                photos = [p for p in (it.get("photos") or []) if isinstance(p, str)]
                img = photos[0] if photos else it.get("img")
                out.append({
                    "id": f"cochesnet:{it.get('id')}",
                    "source": "cochesnet",
                    "title": it.get("title") or f"{it.get('make', '')} {it.get('model', '')}".strip(),
                    "make": it.get("make"), "model": it.get("model"),
                    "year": year, "km": km, "price": price,
                    "fuel": it.get("fuelType"),
                    "location": (it.get("location") or {}).get("mainProvince"),
                    "url": "https://www.coches.net" + (it.get("url") or ""),
                    "image": img, "images": photos or ([img] if img else []),
                })
            self.polite_sleep()
        return out
