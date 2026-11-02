"""AutoScout24 España – parsea el JSON __NEXT_DATA__ de la página de resultados."""
import json

from bs4 import BeautifulSoup

from .base import BaseScraper, log, to_int


class AutoScout24Scraper(BaseScraper):
    name = "autoscout24"

    def fetch_description(self, listing):
        try:
            r = self.client.get(listing["url"])
            r.raise_for_status()
            tag = BeautifulSoup(r.text, "html.parser").find("script", id="__NEXT_DATA__")
            details = json.loads(tag.string)["props"]["pageProps"].get("listingDetails") or {}
            return BeautifulSoup(details.get("description") or "", "html.parser").get_text(" ", strip=True)[:1500]
        except Exception as e:  # noqa: BLE001
            log.warning("autoscout24: no se pudo leer la ficha %s: %s", listing.get("id"), e)
            return None

    def search(self, min_price, max_price, min_year, max_km):
        out = []
        for page in range(1, self.max_pages + 1):
            params = {"atype": "C", "cy": "E", "damaged_listing": "exclude",
                      "fregfrom": min_year, "kmto": max_km,
                      "pricefrom": min_price, "priceto": max_price,
                      "sort": "price", "desc": 0, "page": page, "body": "4,5,6"}
            r = self.client.get("https://www.autoscout24.es/lst", params=params)
            r.raise_for_status()
            tag = BeautifulSoup(r.text, "html.parser").find("script", id="__NEXT_DATA__")
            if not tag:
                break
            listings = json.loads(tag.string)["props"]["pageProps"].get("listings", [])
            if not listings:
                break
            for l in listings:
                v = l.get("vehicle", {})
                reg = (l.get("tracking") or {}).get("firstRegistration") or ""
                out.append({
                    "id": f"autoscout24:{l.get('id')}",
                    "source": "autoscout24",
                    "title": f"{v.get('make', '')} {v.get('model', '')} {v.get('modelVersionInput') or ''}".strip(),
                    "make": v.get("make"), "model": v.get("model"),
                    "year": to_int(reg[-4:]) if reg else None,
                    "km": to_int(v.get("mileageInKm")),
                    "price": to_int((l.get("tracking") or {}).get("price") or l.get("price", {}).get("priceFormatted")),
                    "fuel": v.get("fuel"), "gearbox": v.get("transmission"),
                    "body": v.get("bodyType") or v.get("body"),
                    "location": (l.get("location") or {}).get("city"),
                    "postal": (l.get("location") or {}).get("zip"),
                    "url": "https://www.autoscout24.es" + (l.get("url") or ""),
                    "image": ((l.get("images") or [""])[0] or "").replace("250x188", "640x480") or None,
                    "images": [i.replace("250x188", "640x480") for i in (l.get("images") or []) if isinstance(i, str)],
                })
            self.polite_sleep()
        return out
