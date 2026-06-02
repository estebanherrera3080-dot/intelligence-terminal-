"""
Economic calendar — mock data for development.

In production this would connect to:
  - Forex Factory API
  - Trading Economics API
  - FRED (Federal Reserve Economic Data)
  - Bloomberg Economic Calendar

The mock calendar provides realistic Fed cycle events for 2025-2026.
"""

from datetime import UTC, datetime, timedelta
from typing import List

from app.services.news.schemas import EconomicCalendarEntry, NewsEvent
from app.services.news.classifier import classify_text, classify_economic_release


def _dt(days_ago: int, hour: int = 14) -> datetime:
    """Return a UTC datetime N days ago at a given hour."""
    return datetime.now(UTC).replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)


def _dt_future(days: int, hour: int = 14) -> datetime:
    return datetime.now(UTC).replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days)


# ── Mock recent events (realistic 2025-2026 Fed cycle) ────────────

_MOCK_EVENTS_RAW = [
    {
        "id": "fomc-2026-03",
        "title": "FOMC Meeting Minutes — March 2026",
        "event_type": "FOMC",
        "days_ago": 12,
        "text": (
            "The Committee decided to maintain the target range for the federal funds rate "
            "at 4.25 to 4.50 percent. Inflation has eased substantially but remains somewhat "
            "elevated relative to the 2 percent objective. The Committee remains attentive to "
            "inflation risks. Most participants indicated it would be appropriate to hold rates "
            "at their current level until there is greater confidence that inflation is moving "
            "sustainably toward 2 percent. The labor market remains robust."
        ),
    },
    {
        "id": "cpi-2026-mar",
        "title": "CPI March 2026",
        "event_type": "CPI",
        "days_ago": 8,
        "text": None,   # data release — use numeric classifier
        "actual": 3.1, "forecast": 2.9, "previous": 3.0,
    },
    {
        "id": "nfp-2026-apr",
        "title": "Non-Farm Payrolls April 2026",
        "event_type": "NFP",
        "days_ago": 4,
        "text": None,
        "actual": 175000, "forecast": 185000, "previous": 203000,
    },
    {
        "id": "powell-2026-apr-15",
        "title": "Powell Speech — Economic Outlook",
        "event_type": "POWELL",
        "days_ago": 2,
        "text": (
            "The Federal Reserve remains committed to our 2 percent inflation goal. "
            "Inflation has come down significantly but the last mile is proving more difficult. "
            "We will need to see more good data before we can be confident that inflation is "
            "moving sustainably toward 2 percent. It would not be appropriate to cut rates "
            "until we have gained that confidence. The labor market is strong and the economy "
            "is performing well. We are prepared to maintain the current rate level for as "
            "long as appropriate."
        ),
    },
    {
        "id": "pce-2026-mar",
        "title": "PCE Price Index March 2026",
        "event_type": "PCE",
        "days_ago": 1,
        "text": None,
        "actual": 2.7, "forecast": 2.6, "previous": 2.5,
    },
]

_MOCK_UPCOMING = [
    {
        "event_type": "FOMC",
        "title": "FOMC Rate Decision — May 2026",
        "days_ahead": 8,
    },
    {
        "event_type": "CPI",
        "title": "CPI April 2026",
        "days_ahead": 12,
    },
    {
        "event_type": "NFP",
        "title": "Non-Farm Payrolls May 2026",
        "days_ahead": 18,
    },
    {
        "event_type": "POWELL",
        "title": "Powell Congressional Testimony",
        "days_ahead": 22,
    },
    {
        "event_type": "PCE",
        "title": "PCE Price Index April 2026",
        "days_ahead": 28,
    },
]


def get_mock_events() -> List[NewsEvent]:
    events = []
    for raw in _MOCK_EVENTS_RAW:
        ts = _dt(raw["days_ago"])

        if raw.get("text"):
            cl = classify_text(raw["text"], raw["event_type"])
        else:
            cl = classify_economic_release(
                raw["event_type"],
                raw.get("actual", 0),
                raw.get("forecast", 0),
                raw.get("previous", 0),
            )

        summary = _auto_summary(raw, cl)

        events.append(NewsEvent(
            id=raw["id"],
            title=raw["title"],
            event_type=raw["event_type"],
            timestamp=ts,
            sentiment=cl["sentiment"],
            impact_score=cl["impact_score"],
            gold_impact=cl["gold_impact"],
            confidence=cl["confidence"],
            summary=summary,
            raw_text=raw.get("text"),
            source="mock_calendar",
        ))

    return sorted(events, key=lambda e: e.timestamp)


def get_mock_calendar() -> List[EconomicCalendarEntry]:
    entries = []
    for ev in _MOCK_UPCOMING:
        entries.append(EconomicCalendarEntry(
            event_type=ev["event_type"],
            title=ev["title"],
            scheduled=_dt_future(ev["days_ahead"]),
            released=False,
        ))
    return entries


def _auto_summary(raw: dict, classification: dict) -> str:
    sentiment = classification["sentiment"].upper()
    impact = classification["impact_score"]
    gold = classification["gold_impact"].upper()

    if raw.get("actual") is not None:
        actual, forecast = raw["actual"], raw["forecast"]
        surprise_dir = "beat" if actual > forecast else "missed"
        return (
            f"{raw['title']}: {actual} vs {forecast} expected ({surprise_dir}). "
            f"Classified {sentiment} (impact={impact}/100) → gold {gold}."
        )

    return (
        f"{raw['title']} classified as {sentiment} "
        f"(impact={impact}/100). Gold outlook: {gold}."
    )
