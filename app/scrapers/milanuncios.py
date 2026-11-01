"""Milanuncios – parsea el estado inicial embebido (window.__INITIAL_PROPS__).
Milanuncios tiene protección anti-bot fuerte; puede devolver 0 resultados."""
import json
import re

from ..vehicle import split_make_model
from .base import BaseScraper, to_int


class MilanunciosScraper(BaseScraper):
    name = "milanuncios"

    def search(self, min_price, max_price, min_year, max_km):
        out = []
        for page in range(1, self.max_pages + 1):
            params = {"desde": min_price, "hasta": max_price, "anod": min_year,
                      "kilometrosh": max_km, "orden": "baratos", "pagina": page}
            r = self.client.get("https://www.milanuncios.com/coches-de-segunda-mano/", params=params)
            r.raise_for_status()
            m = re.search(r"window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\((\".*?\")\);", r.text, re.S)
            if not m:
                break
            data = json.loads(json.loads(m.group(1)))
            ads = data.get("adListPagination", {}).get("adList", {}).get("ads", [])
            if not ads:
                break
            for a in ads:
                raw_tags = a.get("tags", []) or []
                tags = {t.get("type"): t.get("text") for t in raw_tags if isinstance(t, dict)}
                texts = [str(t.get("text") if isinstance(t, dict) else t) for t in raw_tags]
                year = to_int(tags.get("year")) or next(
                    (int(x) for x in texts if re.fullmatch(r"(19|20)\d{2}", x.strip())), None)
                km = to_int(tags.get("kilometers")) or next(
                    (to_int(x) for x in texts if "km" in x.lower()), None)
                photos = []
                for p in a.get("photos") or a.get("images") or []:
                    u = p if isinstance(p, str) else (p.get("url") or p.get("src") or p.get("big") or "")
                    if u:
                        photos.append(u if u.startswith("http") else "https:" + u)
                out.append({
                    "id": f"milanuncios:{a.get('id')}",
                    "source": "milanuncios",
                    "title": a.get("title"),
                    "make": split_make_model(a.get("title"))[0],
                    "model": split_make_model(a.get("title"))[1],
                    "body": tags.get("bodyType") or tags.get("carroceria"),
                    "year": year, "km": km,
                    "price": to_int((a.get("price") or {}).get("cashPrice", {}).get("value")),
                    "fuel": tags.get("fuel"), "gearbox": tags.get("transmission"),
                    "location": (a.get("location") or {}).get("province", {}).get("name"),
                    "url": "https://www.milanuncios.com" + (a.get("url") or ""),
                    "image": photos[0] if photos else None, "images": photos,
                })
            self.polite_sleep()
        return out
