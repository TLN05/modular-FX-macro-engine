"""Input checks that return actionable messages instead of silently coercing values."""

from datetime import datetime
import math

from config import metric_catalog


def validate_rows(asset: str, rows) -> list[str]:
    messages = []
    valid_ids = {m["metric_id"] for m in metric_catalog(asset)}
    for i, row in enumerate(rows.to_dict("records"), 1):
        mid = row.get("metric_id")
        if mid not in valid_ids:
            messages.append(f"Row {i}: metric is not in the {asset} catalog.")
            continue
        value = row.get("value")
        if value is None or (isinstance(value, float) and math.isnan(value)) or value == "":
            continue
        if row.get("date") is None or str(row.get("date")) in {"", "NaT", "nan"}:
            messages.append(f"{row.get('metric_name')}: add the observation date; undated data reduces confidence.")
        if not str(row.get("source") or "").strip():
            messages.append(f"{row.get('metric_name')}: add the data source for traceability.")
        if not str(row.get("frequency") or "").strip():
            messages.append(f"{row.get('metric_name')}: add the reporting frequency.")
        try:
            numeric = float(value)
        except (ValueError, TypeError):
            if mid not in {"policy_stance", "inflation_trend", "safe_haven_demand", "geopolitical_impact", "china_stimulus", "expected_next_move", "central_bank_communication"}:
                messages.append(f"{row.get('metric_name')}: enter a number or leave it blank.")
            continue
        if not math.isfinite(numeric):
            messages.append(f"{row.get('metric_name')}: value must be finite.")
        if mid.endswith("_pmi") or mid in {"manufacturing_pmi", "services_pmi", "china_pmi"}:
            if not 0 <= numeric <= 100:
                messages.append(f"{row.get('metric_name')}: expected a value between 0 and 100.")
        if mid in {"cot_percentile", "reer_percentile"} and not 0 <= numeric <= 100:
            messages.append(f"{row.get('metric_name')}: percentile must be from 0 to 100.")
        if mid in {"policy_rate", "expected_rate_3m", "expected_rate_6m", "expected_rate_12m", "inflation_target", "yield_2y_level", "yield_10y_level"} and not -5 <= numeric <= 50:
            messages.append(f"{row.get('metric_name')}: value is outside the supported -5% to 50% range.")
        d = row.get("date")
        if d is not None and str(d) not in {"", "NaT", "nan"}:
            try:
                datetime.strptime(str(d)[:10], "%Y-%m-%d")
            except ValueError:
                messages.append(f"{row.get('metric_name')}: use a valid date in YYYY-MM-DD format.")
    return messages
