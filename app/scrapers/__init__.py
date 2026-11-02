from .autocasion import AutocasionScraper
from .autoscout24 import AutoScout24Scraper
from .cochesnet import CochesNetScraper
from .flexicar import FlexicarScraper
from .milanuncios import MilanunciosScraper
from .wallapop import WallapopScraper

SCRAPERS = {s.name: s for s in [WallapopScraper, AutoScout24Scraper, CochesNetScraper, MilanunciosScraper,
                                  FlexicarScraper, AutocasionScraper]}
