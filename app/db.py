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
CREATE TABLE IF NOT EXISTS price_history (
    day TEXT, model_key TEXT, label TEXT,
    min_price INTEGER, median_price INTEGER, count INTEGER,
    PRIMARY KEY (day, model_key)
);
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
        for extra in ("province", "postal"):
            if extra not in cols:
                c.execute(f"ALTER TABLE listings ADD COLUMN {extra} TEXT")
        if "description" not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN description TEXT")
        if "damaged" not in cols:
            c.execute("ALTER TABLE listings ADD COLUMN damaged INTEGER DEFAULT 0")


def upsert(listing: dict) -> bool:
    """Inserta o actualiza. Devuelve True si es nuevo."""
    now = datetime.now().isoformat(timespec="seconds")
    listing = {**listing, "images": json.dumps(listing.get("images") or ([listing["image"]] if listing.get("image") else []))}
    with conn() as c:
        exists = c.execute("SELECT 1 FROM listings WHERE id=?", (listing["id"],)).fetchone()
        if exists:
            c.execute(
                "UPDATE listings SET price=?, km=COALESCE(?, km), year=COALESCE(?, year), last_seen=?, "
                "image=COALESCE(?, image), images=?, description=COALESCE(?, description), "
                "province=COALESCE(?, province), postal=COALESCE(?, postal) WHERE id=?",
                (listing["price"], listing.get("km"), listing.get("year"), now, listing.get("image"),
                 listing["images"], listing.get("description"), listing.get("province"),
                 listing.get("postal"), listing["id"]),
            )
            return False
        cols = ["id", "source", "title", "make", "model", "year", "km", "price",
                "fuel", "gearbox", "location", "body", "url", "image", "images", "description", "province", "postal"]
        c.execute(
            f"INSERT INTO listings ({','.join(cols)}, first_seen, last_seen) "
            f"VALUES ({','.join('?' * len(cols))}, ?, ?)",
            [listing.get(k) for k in cols] + [now, now],
        )
        return True


def all_rows():
    with conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM listings WHERE COALESCE(damaged, 0) = 0")]
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


def has_description(lid: str) -> bool:
    """True si ya se leyó la descripción de este anuncio (aunque estuviera vacía)."""
    with conn() as c:
        row = c.execute("SELECT description FROM listings WHERE id=?", (lid,)).fetchone()
    return bool(row and row["description"] is not None)


def mark_notified(lid: str):
    with conn() as c:
        c.execute("UPDATE listings SET notified=1 WHERE id=?", (lid,))


def mark_damaged(lid: str):
    with conn() as c:
        c.execute("UPDATE listings SET damaged=1, is_deal=0 WHERE id=?", (lid,))


def save_snapshots(snaps):
    """Un registro por día y modelo: conserva el mínimo del día y la última mediana."""
    with conn() as c:
        c.executemany(
            "INSERT INTO price_history (day, model_key, label, min_price, median_price, count) "
            "VALUES (:day, :model_key, :label, :min_price, :median_price, :count) "
            "ON CONFLICT(day, model_key) DO UPDATE SET label=excluded.label, "
            "min_price=MIN(min_price, excluded.min_price), median_price=excluded.median_price, count=excluded.count",
            snaps,
        )


def price_history(model_key: str):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT day, min_price, median_price, count FROM price_history WHERE model_key=? ORDER BY day",
            (model_key,))]
