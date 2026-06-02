"""
Unit tests for News Engine — Module 6.
"""

import pytest

from app.services.news.classifier import (
    classify_text, classify_economic_release, aggregate_fed_stance,
)
from app.services.news.engine import NewsEngine
from app.services.news.schemas import NewsEvent
from datetime import UTC, datetime


# ── Text classifier ───────────────────────────────────────────────

@pytest.mark.unit
def test_classify_hawkish_powell_speech():
    text = (
        "Inflation remains elevated and above target. "
        "We need to maintain restrictive policy. "
        "The labor market remains strong and robust employment continues. "
        "Higher for longer is the appropriate stance. "
        "We are vigilant about upside risks to inflation. "
        "Rates sufficiently restrictive to bring inflation down."
    )
    result = classify_text(text, "POWELL")
    assert result["sentiment"] == "hawkish"
    assert result["gold_impact"] == "bearish"
    assert result["impact_score"] >= 80
    assert result["confidence"] > 50


@pytest.mark.unit
def test_classify_dovish_powell_speech():
    text = (
        "The Fed will begin cutting rates as inflation has returned to 2 percent. "
        "The labor market is cooling and unemployment rising signals downside risks to growth. "
        "Easing monetary policy is appropriate given progress made on inflation. "
        "Soft landing achieved. Inflation sustainably at 2 percent target."
    )
    result = classify_text(text, "POWELL")
    assert result["sentiment"] == "dovish"
    assert result["gold_impact"] == "bullish"
    assert result["confidence"] > 50


@pytest.mark.unit
def test_classify_neutral_statement():
    text = "The Committee will remain data dependent and assess incoming economic data at each meeting."
    result = classify_text(text, "FED_SPEAKER")
    assert result["sentiment"] == "neutral"
    assert result["gold_impact"] == "neutral"


@pytest.mark.unit
def test_classify_empty_text():
    result = classify_text("", "OTHER")
    assert result["sentiment"] in ("hawkish", "neutral", "dovish")
    assert 0 <= result["impact_score"] <= 100
    assert 0 <= result["confidence"] <= 100


@pytest.mark.unit
def test_classify_fed_score_range():
    for text in [
        "raise rates tighten restrictive inflation above target higher for longer",
        "neutral data dependent monitor",
        "cut rates ease dovish inflation falling below target labor market cooling",
    ]:
        r = classify_text(text, "FOMC")
        assert 0 <= r["fed_score"] <= 100
        assert 0 <= r["impact_score"] <= 100
        assert 0 <= r["confidence"] <= 100


# ── Economic data release classifier ─────────────────────────────

@pytest.mark.unit
def test_cpi_beat_is_hawkish():
    """CPI above forecast → hawkish → bearish gold."""
    r = classify_economic_release("CPI", actual=3.5, forecast=3.0, previous=3.1)
    assert r["sentiment"] == "hawkish"
    assert r["gold_impact"] == "bearish"
    assert r["surprise_pct"] > 0


@pytest.mark.unit
def test_cpi_miss_is_dovish():
    """CPI below forecast → dovish → bullish gold."""
    r = classify_economic_release("CPI", actual=2.5, forecast=3.0, previous=3.1)
    assert r["sentiment"] == "dovish"
    assert r["gold_impact"] == "bullish"
    assert r["surprise_pct"] < 0


@pytest.mark.unit
def test_nfp_beat_is_hawkish():
    r = classify_economic_release("NFP", actual=250000, forecast=180000, previous=200000)
    assert r["sentiment"] == "hawkish"
    assert r["gold_impact"] == "bearish"


@pytest.mark.unit
def test_nfp_miss_is_dovish():
    r = classify_economic_release("NFP", actual=100000, forecast=180000, previous=200000)
    assert r["sentiment"] == "dovish"
    assert r["gold_impact"] == "bullish"


@pytest.mark.unit
def test_inline_surprise_neutral():
    """Very small surprise → neutral."""
    r = classify_economic_release("CPI", actual=3.0, forecast=3.0, previous=2.9)
    assert r["sentiment"] == "neutral"


@pytest.mark.unit
def test_economic_release_scores_bounded():
    r = classify_economic_release("CPI", actual=4.0, forecast=2.0, previous=3.0)
    assert 0 <= r["impact_score"] <= 100
    assert 0 <= r["confidence"] <= 100


# ── Aggregate Fed stance ──────────────────────────────────────────

def _make_event(sentiment: str, impact: int) -> NewsEvent:
    return NewsEvent(
        id="test", title="Test", event_type="FOMC",
        timestamp=datetime.now(UTC),
        sentiment=sentiment, impact_score=impact,
        gold_impact="neutral", confidence=80.0,
    )


@pytest.mark.unit
def test_aggregate_all_hawkish():
    events = [_make_event("hawkish", 85) for _ in range(5)]
    stance, score, conf = aggregate_fed_stance(events)
    assert stance == "hawkish"
    assert score > 50


@pytest.mark.unit
def test_aggregate_all_dovish():
    events = [_make_event("dovish", 80) for _ in range(5)]
    stance, score, conf = aggregate_fed_stance(events)
    assert stance == "dovish"
    assert score < 50


@pytest.mark.unit
def test_aggregate_empty():
    stance, score, conf = aggregate_fed_stance([])
    assert stance == "neutral"
    assert score == 50


@pytest.mark.unit
def test_aggregate_mixed():
    events = [
        _make_event("hawkish", 90),
        _make_event("dovish", 50),
        _make_event("hawkish", 85),
        _make_event("neutral", 60),
    ]
    stance, score, conf = aggregate_fed_stance(events)
    # Hawkish dominates by impact weight
    assert stance in ("hawkish", "neutral")
    assert 0 <= score <= 100


# ── Engine integration ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_analyze_returns_valid():
    engine = NewsEngine()
    r = await engine.analyze()

    assert r.fed_stance in ("hawkish", "neutral", "dovish")
    assert 0 <= r.fed_score <= 100
    assert 0 <= r.fed_confidence <= 100
    assert r.news_gold_bias in ("bullish", "neutral", "bearish")
    assert 0 <= r.news_impact_score <= 100
    assert len(r.events) > 0
    assert len(r.upcoming_events) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_events_all_valid():
    engine = NewsEngine()
    r = await engine.analyze()
    for ev in r.events:
        assert ev.sentiment in ("hawkish", "neutral", "dovish")
        assert ev.gold_impact in ("bullish", "neutral", "bearish")
        assert 0 <= ev.impact_score <= 100
        assert ev.event_type in (
            "FOMC", "POWELL", "FED_SPEAKER", "CPI", "PCE",
            "NFP", "TREASURY", "GDP", "RETAIL_SALES", "ISM", "OTHER"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_classify_text():
    engine = NewsEngine()
    r = await engine.classify_text(
        "The Fed will cut rates as inflation has fallen toward 2 percent.", "POWELL"
    )
    assert r["sentiment"] in ("hawkish", "neutral", "dovish")
    assert 0 <= r["impact_score"] <= 100


# ── HTTP endpoints ────────────────────────────────────────────────

@pytest.mark.unit
def test_news_fed_endpoint(client):
    res = client.get("/api/v1/news/fed")
    assert res.status_code == 200
    d = res.json()
    assert d["fed_stance"] in ("hawkish", "neutral", "dovish")
    assert 0 <= d["fed_score"] <= 100
    assert d["news_gold_bias"] in ("bullish", "neutral", "bearish")


@pytest.mark.unit
def test_news_events_endpoint(client):
    res = client.get("/api/v1/news/events")
    assert res.status_code == 200
    d = res.json()
    assert "events" in d
    assert d["count"] > 0
    for ev in d["events"]:
        assert ev["sentiment"] in ("hawkish", "neutral", "dovish")
        assert 0 <= ev["impact_score"] <= 100


@pytest.mark.unit
def test_news_calendar_endpoint(client):
    res = client.get("/api/v1/news/calendar")
    assert res.status_code == 200
    d = res.json()
    assert "upcoming" in d
    assert d["count"] > 0


@pytest.mark.unit
def test_news_classify_endpoint(client):
    payload = {
        "text": (
            "The Fed must raise rates to fight inflation. "
            "Restrictive policy is needed. Higher for longer. "
            "Inflation elevated above target. Tightening continues."
        ),
        "event_type": "FOMC"
    }
    res = client.post("/api/v1/news/classify", json=payload)
    assert res.status_code == 200
    d = res.json()
    assert d["sentiment"] == "hawkish"
    assert d["gold_impact"] == "bearish"


@pytest.mark.unit
def test_news_classify_dovish(client):
    payload = {
        "text": (
            "The Fed will begin cutting rates. Easing monetary policy is appropriate. "
            "Inflation sustainably at 2 percent. Soft landing achieved. "
            "Downside risks to growth warrant accommodation."
        ),
        "event_type": "POWELL"
    }
    res = client.post("/api/v1/news/classify", json=payload)
    assert res.status_code == 200
    d = res.json()
    assert d["sentiment"] == "dovish"
    assert d["gold_impact"] == "bullish"


@pytest.mark.unit
def test_news_analysis_endpoint(client):
    res = client.get("/api/v1/news/analysis")
    assert res.status_code == 200
    d = res.json()
    assert "fed_stance" in d
    assert "events" in d
    assert "upcoming_events" in d
    assert "key_headlines" in d
