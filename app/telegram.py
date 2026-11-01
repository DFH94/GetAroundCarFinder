"""Avisos por Telegram."""
import logging
from html import escape

import httpx

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send(text: str) -> bool:
    if not enabled():
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": False},
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:  # noqa: BLE001
        log.warning("Telegram error: %s", e)
        return False


def _eur(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def deal_message(l: dict) -> str:
    e = lambda v: escape(str(v if v not in (None, "") else "?"))  # noqa: E731
    return "\n".join([
        f"🔥 <b>GANGA</b> en {e(l['source'])}",
        f"<b>{e(l['title'])}</b>",
        f"💶 {_eur(l['price'])} € (mediana {_eur(l['median_price'])} €, <b>-{l['discount_pct']}%</b>)",
        f"📅 {e(l.get('year'))} · 🛣 {e(l.get('km'))} km · ⛽ {e(l.get('fuel'))}",
        f"📍 {e(l.get('location'))}",
        f"📈 Beneficio estimado GetAround: {l['monthly_profit']} €/mes · payback {l['payback_months']} meses",
        escape(l["url"]),
    ])


