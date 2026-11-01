"""Persistencia SQLite de anuncios."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DATA_DIR

DB_PATH = DATA_DIR / "listings.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,            -- source:external_id
    source TEXT, title TEXT, make TEXT, model TEXT,
    year INTEGER, km INTEGER, price INTEGER,
    fuel TEXT, gearbox TEXT, location TEXT, body TEXT,
    url TEXT, image TEXT, images TEXT,
    first_seen TEXT, last_seen TEXT,
    median_price INTEGER, discount_pct REAL, is_deal INTEGER DEFAULT 0,
    monthly_profit INTEGER, payback_months REAL,
    notified INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_mm ON listings(make, model, year);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)
        cols = [r[1] for r in c.execute("PRAGMA table_info(listings)")]
        if "body" not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN body TEXT")
        if "images" not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN images TEXT")


def upsert(listing: dict) -> bool:
    """Inserta o actualiza. Devuelve True si es nuevo."""
    now = datetime.now().isoformat(timespec="seconds")
    listing = {**listing, "images": json.dumps(listing.get("images") or ([listing["image"]] if listing.get("image") else []))}
    with conn() as c:
        exists = c.execute("SELECT 1 FROM listings WHERE id=?", (listing["id"],)).fetchone()
        if exists:
            c.execute(
                "UPDATE listings SET price=?, km=COALESCE(?, km), year=COALESCE(?, year), last_seen=?, "
                "image=COALESCE(?, image), images=? WHERE id=?",
                (listing["price"], listing.get("km"), listing.get("year"), now, listing.get("image"),
                 listing["images"], listing["id"]),
            )
            return False
        cols = ["id", "source", "title", "make", "model", "year", "km", "price",
                "fuel", "gearbox", "location", "body", "url", "image", "images"]
        c.execute(
            f"INSERT INTO listings ({','.join(cols)}, first_seen, last_seen) "
            f"VALUES ({','.join('?' * len(cols))}, ?, ?)",
            [listing.get(k) for k in cols] + [now, now],
        )
        return True


def all_rows():
    with conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM listings")]
    for r in rows:
        r["images"] = json.loads(r.get("images") or "[]") or ([r["image"]] if r.get("image") else [])
    return rows


def update_scores(rows):
    with conn() as c:
        c.executemany(
            "UPDATE listings SET median_price=:median_price, discount_pct=:discount_pct, "
            "is_deal=:is_deal, monthly_profit=:monthly_profit, payback_months=:payback_months WHERE id=:id",
            rows,
        )


def mark_notified(lid: str):
    with conn() as c:
        c.execute("UPDATE listings SET notified=1 WHERE id=?", (lid,))
