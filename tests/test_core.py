import pytest
from pydantic import ValidationError

from app import scoring, telegram, vehicle
from app.config import DEFAULT_CONFIG, ConfigIn


def test_classify_excludes_motos():
    assert vehicle.classify({"title": "Yamaha moto 125", "body": "suv"}) is None


def test_classify_by_body_and_model():
    assert vehicle.classify({"title": "Algo", "body": "SUV"}) == "suv"
    assert vehicle.classify({"title": "Skoda Octavia Combi 2.0"}) == "familiar"
    assert vehicle.classify({"title": "Seat Ibiza", "body": "small_car"}) is None


def test_deal_detection():
    rows = [{"id": str(i), "make": "Seat", "model": "Ateca", "year": 2021, "price": p}
            for i, p in enumerate([10000, 10000, 10000, 7000])]
    out = {r["id"]: r for r in scoring.compute(rows, DEFAULT_CONFIG)}
    assert out["3"]["is_deal"] == 1
    assert out["0"]["is_deal"] == 0


def test_deal_message_escapes_html():
    msg = telegram.deal_message({
        "source": "wallapop", "title": "Coche <b>&</b>, bueno", "price": 8500, "median_price": 10000,
        "discount_pct": 15.0, "year": 2021, "km": 30000, "fuel": None, "location": "A<B",
        "monthly_profit": 300, "payback_months": 28.0, "url": "https://x.es/?a=1&b=2"})
    assert "<b>&</b>" not in msg and "&lt;b&gt;" in msg
    assert "8.500 €" in msg and "bueno" in msg


def test_config_validation():
    ok = {k: DEFAULT_CONFIG[k] for k in ConfigIn.model_fields if k in DEFAULT_CONFIG}
    ConfigIn(**ok)
    with pytest.raises(ValidationError):
        ConfigIn(**{**ok, "sources": ["nope"]})
    with pytest.raises(ValidationError):
        ConfigIn(**{**ok, "deal_threshold_pct": 500})


def _rows(model, prices, year=2021):
    return [{"id": f"{model}{i}", "make": "VW", "model": model, "year": year, "price": p}
            for i, p in enumerate(prices)]


def test_median_does_not_mix_versions():
    rows = _rows("Golf GTI", [20000, 20000, 20000]) + _rows("Golf 1.0", [10000, 10000, 10000, 8000])
    out = {r["id"]: r for r in scoring.compute(rows, DEFAULT_CONFIG)}
    assert out["Golf 1.03"]["median_price"] == 10000
    assert out["Golf GTI0"]["median_price"] == 20000


def test_median_year_tolerance_and_no_data():
    rows = _rows("Ateca", [10000, 10000], 2021) + _rows("Ateca", [10000], 2022)
    out = {r["id"]: r for r in scoring.compute(rows, DEFAULT_CONFIG)}
    assert out["Ateca0"]["median_price"] == 10000
    lonely = scoring.compute(_rows("Raro", [9000]), DEFAULT_CONFIG)[0]
    assert lonely["median_price"] is None and lonely["is_deal"] == 0


@pytest.mark.parametrize("title,desc,expected", [
    ("VW Tiguan 2022 ACCIDENTADO", "", True),
    ("Skoda Octavia 2023 , Motor averiado", "", True),
    ("Peugeot e-2008 2023", "coche estaba dentro inundado hasta los asientos", True),
    ("Citroen C4 2023", "Vehículo con golpe, arranca sin problema", True),
    ("Seat Ateca 2022", "Siempre en garaje, sin accidentes ni golpes", False),
    ("Opel Corsa 2026", "NO VENDEMOS PIEZAS !! documentación en regla", False),
    ("Kia Sportage 2022", "Único dueño, revisiones al día", False),
])
def test_is_damaged(title, desc, expected):
    assert vehicle.is_damaged({"title": title, "description": desc}) is expected


def test_suspect_listings():
    from datetime import date
    y = date.today().year
    assert vehicle.implausibly_cheap({"year": y - 2, "price": 5700})
    assert not vehicle.implausibly_cheap({"year": y - 2, "price": 13000})
    assert vehicle.implausibly_cheap({"year": y - 4, "price": 7000})  # Kona 2022 siniestrado
    assert not vehicle.implausibly_cheap({"year": y - 7, "price": 5000})
    assert vehicle.is_suspect({"year": y - 7, "price": 5000, "discount_pct": 40})
    assert not vehicle.is_suspect({"year": y - 7, "price": 5000, "discount_pct": 20})


def test_wreck_price_is_not_a_deal():
    from datetime import date
    y = date.today().year
    rows = [{"id": str(i), "make": "Seat", "model": "Arona", "year": y - 2, "price": p}
            for i, p in enumerate([14000, 14000, 14000, 5000])]
    out = {r["id"]: r for r in scoring.compute(rows, DEFAULT_CONFIG)}
    assert out["3"]["is_deal"] == 0


def _cn_page(items):
    import json
    props = json.dumps({"initialResults": {"items": items}})
    return "<html><script>window.__INITIAL_PROPS__ = JSON.parse(" + json.dumps(props) + ");</script></html>"


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_cochesnet_parses_and_filters(monkeypatch):
    from app.scrapers.cochesnet import CochesNetScraper
    good = {"id": "1", "make": "JEEP", "model": "Renegade", "title": "JEEP Renegade", "year": 2023, "km": 20000,
            "price": 8000, "fuelType": "Gasolina", "photos": ["https://a/1.jpg"], "url": "/x-1.aspx",
            "location": {"mainProvince": "Madrid"}}
    old = {**good, "id": "2", "year": 2015}
    s = CochesNetScraper()
    monkeypatch.setattr(s, "polite_sleep", lambda: None)
    pages = iter([_cn_page([good, old]), "<html>Ups, verificación anti-bot</html>"])
    monkeypatch.setattr(s.client, "get", lambda *a, **k: _Resp(next(pages)))
    out = s.search(5000, 9000, 2022, 60000)
    assert [o["id"] for o in out] == ["cochesnet:1"]
    assert out[0]["image"] == "https://a/1.jpg" and out[0]["url"] == "https://www.coches.net/x-1.aspx"


def test_flexicar_parses_and_paginates(monkeypatch):
    from app.scrapers.flexicar import FlexicarScraper

    def v(i, **kw):
        return {"id": i, "brand": "Seat", "model": "Ateca", "version": "1.0", "year": 2023, "km": 20000,
                "price": 14000, "fuel": "Gasolina", "transmission": "Manual", "carDealership": "Ourense",
                "slug": f"seat-ateca_{i}", "image": f"https://f/{i}.jpg", "images": [f"https://f/{i}.jpg"], **kw}

    pages = iter([{"hasNext": True, "results": [v(1), v(2, reserved=True)]},
                  {"hasNext": False, "results": [v(3)]}])

    class R:
        def __init__(self, d):
            self.d = d

        def raise_for_status(self):
            pass

        def json(self):
            return self.d

    s = FlexicarScraper()
    monkeypatch.setattr(s, "polite_sleep", lambda: None)
    monkeypatch.setattr(s.client, "get", lambda *a, **k: R(next(pages)))
    out = s.search(11000, 15000, 2022, 60000)
    assert [o["id"] for o in out] == ["flexicar:1", "flexicar:3"]
    assert out[0]["url"] == "https://www.flexicar.es/coches-ocasion/seat-ateca_1"
    assert out[0]["title"] == "Seat Ateca 1.0" and out[0]["location"] == "Ourense"


def _car(i, city, **kw):
    return {"id": i, "make": "Citroën", "model": "C3 Aircross", "title": "Citroën C3 Aircross", "year": 2023,
            "km": 50689, "price": 9390, "location": city, "images": ["a"] * kw.pop("n", 1), **kw}


def test_dedupe_same_car_in_several_cities():
    from app.dedupe import dedupe
    rows = [_car("a", "Madrid"), _car("b", "Vigo", n=3), _car("c", "Leon"),
            _car("d", "Madrid", km=50700)]
    kept, dups = dedupe(rows)
    assert [r["id"] for r in kept] == ["b", "d"]  # b tiene más fotos
    assert sorted(c["id"] for c in dups["b"]) == ["a", "c"]


def test_dedupe_round_km_requires_same_title():
    from app.dedupe import dedupe
    a = _car("a", "Madrid", km=20000)
    b = _car("b", "Vigo", km=20000, title="Citroën C3 Aircross Shine")
    kept, _ = dedupe([a, b])
    assert len(kept) == 2


def test_duplicates_do_not_skew_median():
    from app.dedupe import dedupe
    dup = [_car(f"x{i}", f"C{i}", price=10000, km=30123) for i in range(6)]
    others = [_car(f"o{i}", "M", price=p, km=40000 + i) for i, p in enumerate([14000, 14000, 14000])]
    kept, _ = dedupe(dup + others)
    assert len(kept) == 4
    out = {r["id"]: r for r in scoring.compute(kept, DEFAULT_CONFIG)}
    assert out[kept[0]["id"]]["median_price"] == 14000
