"""
Institutional News Engine — orchestrates calendar, classification and analysis.

Workflow:
  1. Load recent events (mock calendar or real API in production)
  2. Classify each event: hawkish/dovish + impact score
  3. Aggregate Fed stance from weighted recent events
  4. Derive gold news bias
  5. Return NewsAnalysis
"""

from datetime import UTC, datetime
from typing import List

from app.core.logger import get_logger
from app.services.news.calendar import get_mock_calendar, get_mock_events
from app.services.news.classifier import aggregate_fed_stance, classify_text
from app.services.news.schemas import NewsAnalysis, NewsEvent

logger = get_logger(__name__)


class NewsEngine:
    """
    Classifies institutional news events and derives a macro-level
    Fed stance and gold news bias.

    Currently uses a mock calendar with realistic 2025-2026 event data.
    Replace `_load_events()` with a live feed (Forex Factory, FRED, etc.)
    when API keys are available.
    """

    async def analyze(self) -> NewsAnalysis:
        now = datetime.now(UTC)

        events = self._load_events()
        calendar = get_mock_calendar()

        # High-impact events only for aggregation
        high_impact = [e for e in events if e.impact_score >= 60]

        fed_stance, fed_score, fed_conf = aggregate_fed_stance(high_impact or events)

        # Gold news bias: inverse of Fed stance (hawkish Fed → bearish gold)
        gold_bias = (
            "bearish"  if fed_stance == "hawkish" else
            "bullish"  if fed_stance == "dovish"  else
            "neutral"
        )

        # News impact score for gold: 0=very bullish, 50=neutral, 100=very bearish
        news_impact = int(50 + (fed_score - 50) * -1)   # invert: hawkish=high=bearish
        news_impact = max(0, min(100, news_impact))

        headlines = [e.summary for e in events[-5:] if e.summary]
        risk_events = [
            f"{e.event_type}: {e.title} ({e.sentiment.upper()}, impact={e.impact_score})"
            for e in events
            if e.impact_score >= 80
        ]
        last_major = events[-1].title if events else None

        return NewsAnalysis(
            timestamp=now,
            events=events,
            fed_stance=fed_stance,
            fed_score=fed_score,
            fed_confidence=fed_conf,
            news_gold_bias=gold_bias,
            news_impact_score=news_impact,
            upcoming_events=calendar,
            last_major_event=last_major,
            key_headlines=headlines,
            risk_events=risk_events,
        )

    def _load_events(self) -> List[NewsEvent]:
        """Load events. Swap this method for a live feed in production."""
        try:
            return get_mock_events()
        except Exception as e:
            logger.error(f"Failed to load news events: {e}")
            return []

    async def classify_text(self, text: str, event_type: str = "OTHER") -> dict:
        """Ad-hoc text classification endpoint."""
        return classify_text(text, event_type)
