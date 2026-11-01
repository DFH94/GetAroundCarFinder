"""Avisos por Telegram."""
import logging

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


def deal_message(l: dict) -> str:
    return (
        f"🔥 <b>GANGA</b> en {l['source']}\n"
        f"<b>{l['title']}</b>\n"
        f"💶 {l['price']:,} € (mediana {l['median_price']:,} €, <b>-{l['discount_pct']}%</b>)\n"
        f"📅 {l.get('year') or '?'} · 🛣 {l.get('km') or '?'} km · ⛽ {l.get('fuel') or '?'}\n"
        f"📍 {l.get('location') or '?'}\n"
        f"📈 Beneficio estimado GetAround: {l['monthly_profit']} €/mes · payback {l['payback_months']} meses\n"
        f"{l['url']}"
    ).replace(",", ".")
