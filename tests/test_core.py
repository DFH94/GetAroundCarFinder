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
