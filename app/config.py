"""Configuración persistente (presupuestos, criterios seminuevo, supuestos económicos)."""
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SCRAPE_INTERVAL_MIN = int(os.getenv("SCRAPE_INTERVAL_MIN", "60"))

DEFAULT_CONFIG = {
    # Varios presupuestos: se busca en cada rango
    "budgets": [
        {"name": "Económico", "min": 5000, "max": 9000, "active": True},
        {"name": "Medio", "min": 9000, "max": 14000, "active": True},
        {"name": "Alto", "min": 14000, "max": 20000, "active": False},
    ],
    # Seminuevo
    "max_age_years": 4,
    "max_km": 60000,
    # Solo berlinas o superior (sin utilitarios, motos, quads, furgonetas...)
    "body_types": ["berlina", "familiar", "suv", "monovolumen"],
    "sources": ["wallapop", "autoscout24", "cochesnet", "milanuncios"],
    # Ganga = precio por debajo de la mediana de comparables en este %
    "deal_threshold_pct": 15,
    "min_comparables": 3,
    # Supuestos de negocio GetAround
    "economics": {
        "rented_hours_month": 120,
        "getaround_commission_pct": 30,
        "monthly_fixed_costs": 180,  # seguro, ITV/mantenimiento prorrateado, plaza
    },
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **cfg}
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> dict:
    merged = {**DEFAULT_CONFIG, **cfg}
    CONFIG_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged


def min_year(cfg: dict) -> int:
    return date.today().year - int(cfg["max_age_years"])
