"""API FastAPI + scheduler + servidor del dashboard."""
import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, scoring, telegram, vehicle
from .config import ConfigIn, ROOT, SCRAPE_INTERVAL_MIN, load_config, min_year, save_config
from .scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="GetAround Car Finder")
STATE = {"running": False, "last_run": None, "last_new": 0, "last_deals": 0}
_lock = threading.Lock()


def rescore(cfg):
    rows = db.all_rows()
    db.update_scores(scoring.compute(rows, cfg))


def run_scrape():
    if not _lock.acquire(blocking=False):
        return
    STATE["running"] = True
    try:
        cfg = load_config()
        new = 0
        for budget in [b for b in cfg["budgets"] if b.get("active")]:
            for name in cfg["sources"]:
                scraper = SCRAPERS[name]()
                for l in scraper.run(min_price=budget["min"], max_price=budget["max"],
                                     min_year=min_year(cfg), max_km=cfg["max_km"]):
                    if not (l.get("price") and l.get("year") and l.get("km") is not None and l.get("image")):
                        continue
                    if vehicle.is_damaged(l):
                        db.mark_damaged(l["id"])
                        continue
                    btype = vehicle.classify(l)
                    if btype and btype in cfg["body_types"]:
                        l["body"] = btype
                        new += db.upsert(l)
        rescore(cfg)
        deals = 0
        for l in db.all_rows():
            if l["is_deal"] and not l["notified"]:
                if telegram.send(telegram.deal_message(l)):
                    db.mark_notified(l["id"])
                    deals += 1
        STATE.update(last_run=datetime.now().isoformat(timespec="seconds"), last_new=new, last_deals=deals)
        log.info("Scrape terminado: %d nuevos, %d gangas", new, deals)
    finally:
        STATE["running"] = False
        _lock.release()


@app.on_event("startup")
def startup():
    db.init()
    for r in db.all_rows():  # los ya guardados: se revisa el título
        if vehicle.is_damaged(r):
            db.mark_damaged(r["id"])
    sched = BackgroundScheduler()
    sched.add_job(run_scrape, "interval", minutes=SCRAPE_INTERVAL_MIN, next_run_time=datetime.now())
    sched.start()


@app.get("/api/listings")
def listings():
    cfg = load_config()
    my = min_year(cfg)
    rows = [r for r in db.all_rows()
            if r["year"] and r["km"] is not None and r["image"]
            and r["year"] >= my and (r["km"] or 0) <= cfg["max_km"]
            and r["body"] in cfg["body_types"]]
    return rows


@app.get("/api/body-types")
def body_types():
    return vehicle.BODY_TYPES


@app.get("/api/status")
def status():
    return {**STATE, "telegram": telegram.enabled(), "interval_min": SCRAPE_INTERVAL_MIN}


@app.post("/api/scrape")
def scrape():
    if STATE["running"]:
        return {"ok": False, "msg": "Ya hay una búsqueda en curso"}
    threading.Thread(target=run_scrape, daemon=True).start()
    return {"ok": True}


@app.get("/api/config")
def get_config():
    return load_config()


@app.put("/api/config")
def put_config(cfg: ConfigIn):
    saved = save_config(cfg.model_dump())
    rescore(saved)
    return saved


@app.post("/api/telegram/test")
def tg_test():
    return {"ok": telegram.send("✅ GetAround Car Finder conectado. Te avisaré de las gangas.")}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
