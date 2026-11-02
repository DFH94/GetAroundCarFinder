"""Interfaz común para scrapers."""
import logging
import random
import time

import httpx

log = logging.getLogger("scraper")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


class BaseScraper:
    name = "base"
    max_pages = 10

    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"},
            timeout=25, follow_redirects=True,
        )

    def polite_sleep(self):
        time.sleep(random.uniform(1.5, 3.5))

    def search(self, min_price: int, max_price: int, min_year: int, max_km: int) -> list[dict]:
        raise NotImplementedError

    def fetch_description(self, listing: dict) -> str | None:
        """Descripción completa del anuncio (requiere abrir su ficha). None si el portal ya la da en el listado."""
        return None

    def run(self, **kw) -> list[dict]:
        try:
            res = self.search(**kw)
            log.info("%s: %d anuncios (%s-%s €)", self.name, len(res), kw["min_price"], kw["max_price"])
            return res
        except Exception as e:  # noqa: BLE001
            log.warning("%s falló: %s", self.name, e)
            return []


def to_int(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return int(digits) if digits else None
