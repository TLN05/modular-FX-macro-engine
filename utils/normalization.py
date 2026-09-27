"""Documented metric-specific conversions to the common -100..+100 scale."""

from __future__ import annotations

from datetime import date, datetime
import math

STANCE_SCORE = {"Very dovish": -100, "Dovish": -50, "Neutral": 0, "Hawkish": 50, "Very hawkish": 100}
DIRECTION_SCORE = {"Negative": -100, "Neutral": 0, "Positive": 100}


def clamp(value: float) -> float:
    return max(-100.0, min(100.0, float(value)))


def freshness(date_value: str | None) -> tuple[str, float]:
    if not date_value:
        return "Undated", 0.45
    try:
        parsed = datetime.strptime(str(date_value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "Invalid date", 0.0
    age = max(0, (date.today() - parsed).days)
    if age <= 35:
        return "Fresh", 1.0
    if age <= 90:
        return "Aging", 0.7
    return "Stale", 0.35


def normalize(record) -> float | None:
    """Map catalogued inputs to scores. PMI uses 50 as neutral; percentile uses 50."""
    value = record.value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if record.metric_id == "policy_stance":
        return float(STANCE_SCORE.get(str(value), 0))
    if record.metric_id in {"inflation_trend", "safe_haven_demand", "geopolitical_impact", "china_stimulus", "expected_next_move", "central_bank_communication"}:
        return float(DIRECTION_SCORE.get(str(value), 0))
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if record.metric_id in {"manufacturing_pmi", "services_pmi", "china_pmi"}:
        return clamp((x - 50.0) / 10.0 * 100)
    if record.metric_id == "cot_percentile":
        # Directional positioning is positive when net long; extreme tails increase crowding risk.
        return clamp((x - 50.0) * 2)
    if record.metric_id == "reer_percentile":
        # An expensive currency is a mild valuation headwind; never treated as a reversal forecast.
        return clamp((50.0 - x) * 1.0)
    if record.metric_id in {"expected_rate_3m", "expected_rate_6m", "expected_rate_12m"}:
        # Absolute level has no cross-asset meaning; when prior is supplied, score path repricing.
        if record.previous_value is None:
            return None
        x -= float(record.previous_value)
    if record.metric_id == "inflation_surprise" and record.forecast is not None:
        x -= float(record.forecast)
    if record.polarity == 0:
        return None
    return clamp((x / max(float(record.scale), 1e-9)) * 100 * int(record.polarity))
