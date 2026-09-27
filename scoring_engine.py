"""Deterministic, provider-neutral score aggregation."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from config import CATEGORY_WEIGHTS, GOLD_CATEGORY_WEIGHTS, metric_catalog
from utils.normalization import freshness, normalize


def _weights(asset: str) -> dict[str, float]:
    return GOLD_CATEGORY_WEIGHTS if asset == "XAU" else CATEGORY_WEIGHTS


def _contextual_normalize(record, by_id: dict) -> float | None:
    """Score inflation levels/surprises only when an observable policy response is entered."""
    if record.metric_id in {"cpi_yoy", "core_cpi_yoy", "ppi_yoy", "pce_yoy", "wage_inflation", "inflation_surprise"}:
        stance = by_id.get("policy_stance")
        repricing = by_id.get("rate_expectation_change")
        response = 0
        if repricing is not None and repricing.value is not None:
            try:
                repricing_value = float(repricing.value)
                response = 1 if repricing_value > 0 else -1 if repricing_value < 0 else 0
            except (TypeError, ValueError):
                response = 0
        elif stance is not None and stance.value is not None:
            response = 1 if str(stance.value) in {"Hawkish", "Very hawkish"} else -1 if str(stance.value) in {"Dovish", "Very dovish"} else 0
        if not response:
            return None
        if record.metric_id == "inflation_surprise":
            if record.forecast is None:
                return None
            import utils.normalization as norm
            try:
                surprise = float(record.value) - float(record.forecast)
            except (TypeError, ValueError):
                return None
            return norm.clamp(surprise / max(float(record.scale), 1e-9) * 100 * response)
        target = by_id.get("inflation_target")
        if target is None or target.value is None:
            return None
        import utils.normalization as norm
        try:
            gap = float(record.value) - float(target.value)
        except (TypeError, ValueError):
            return None
        # Above-target inflation supports currency only when the observed policy reaction is hawkish.
        return norm.clamp(gap / max(float(record.scale), 1e-9) * 100 * response)
    return normalize(record)


def score_asset(asset: str, records, custom_weights: dict[str, float] | None = None) -> dict:
    """Aggregate metrics within groups, groups within categories, then categories."""
    catalog = metric_catalog(asset)
    by_id = {r.metric_id: r for r in records if r.asset == asset}
    groups: dict[str, dict[str, list[tuple]]] = defaultdict(lambda: defaultdict(list))
    all_freshness, input_reliability, scored_count = [], [], 0
    for spec in catalog:
        r = by_id.get(spec["metric_id"])
        if r is None:
            continue
        s = _contextual_normalize(r, by_id)
        if s is None:
            continue
        scored_count += 1
        freshness_label, freshness_factor = freshness(r.date)
        all_freshness.append(freshness_factor)
        input_reliability.append(max(0.0, min(1.0, float(r.confidence))))
        groups[r.category][r.group].append((s, r, freshness_label))

    categories = {}
    for category, group_map in groups.items():
        group_results = []
        for group, values in group_map.items():
            avg = sum(x[0] for x in values) / len(values)
            group_results.append({"group": group, "score": avg, "metrics": values})
        categories[category] = {
            "score": sum(g["score"] for g in group_results) / len(group_results),
            "groups": group_results,
        }

    weights = dict(custom_weights or _weights(asset))
    applicable_categories = {item["category"] for item in catalog if item["category"] in weights}
    applicable_weight = sum(weights.get(c, 0) for c in applicable_categories)
    used_weight = sum(weights.get(c, 0) for c in categories)
    if used_weight:
        score = float(np.average([categories[c]["score"] for c in categories],
                                 weights=[weights.get(c, 0) for c in categories]))
    else:
        score = None
    # Coverage accounts for entered/scorable fields within each applicable category.
    catalog_counts = defaultdict(int)
    scored_by_category = defaultdict(int)
    for spec in catalog:
        catalog_counts[spec["category"]] += 1
    for category, group_map in groups.items():
        scored_by_category[category] = sum(len(v) for v in group_map.values())
    coverage = (sum(weights.get(c, 0) * scored_by_category.get(c, 0) / max(catalog_counts[c], 1)
                    for c in applicable_categories) / applicable_weight) if applicable_weight else 0.0
    if categories and score is not None:
        alignment = sum(weights.get(c, 0) for c, d in categories.items()
                        if abs(d["score"]) >= 10 and d["score"] * score > 0) / used_weight
    else:
        alignment = 0.0
    magnitude = (sum(weights.get(c, 0) * abs(d["score"]) for c, d in categories.items()) /
                 used_weight / 100) if used_weight else 0.0
    fresh = sum(all_freshness) / len(all_freshness) if all_freshness else 0.0
    reliability = sum(input_reliability) / len(input_reliability) if input_reliability else 0.0
    # Confidence is evidence quality, not a transformation of score magnitude.
    confidence = 100 * (0.45 * coverage + 0.20 * fresh + 0.15 * reliability + 0.15 * alignment + 0.05 * magnitude)
    contributions = []
    metric_rows = []
    for category, details in categories.items():
        weight = weights.get(category, 0) / used_weight if used_weight else 0
        contributions.append({"category": category, "score": details["score"],
                              "weight": weight, "contribution": details["score"] * weight})
        group_count = len(details["groups"])
        for group in details["groups"]:
            for metric_score, record, freshness_label in group["metrics"]:
                metric_weight = weight / group_count / len(group["metrics"])
                metric_rows.append({"category": category, "group": group["group"],
                    "metric": record.metric_name, "raw_value": record.value,
                    "date": record.date or "Undated", "freshness": freshness_label,
                    "score": metric_score, "weight": metric_weight,
                    "contribution": metric_score * metric_weight,
                    "previous": record.previous_value, "forecast": record.forecast,
                    "source": record.source, "frequency": record.frequency,
                    "input confidence": record.confidence})
    return {
        "asset": asset, "score": score, "bias": bias_label(score),
        "confidence": confidence, "coverage": coverage, "alignment": alignment, "signal_magnitude": magnitude,
        "categories": categories, "contributions": contributions,
        "metric_rows": metric_rows,
        "scored_metrics": scored_count,
        "crowding": cot_crowding(by_id.get("cot_percentile")),
    }


def bias_label(score: float | None) -> str:
    if score is None:
        return "Unavailable"
    if score >= 75: return "Very Bullish"
    if score >= 50: return "Bullish"
    if score >= 25: return "Moderately Bullish"
    if score > -25: return "Neutral"
    if score > -50: return "Moderately Bearish"
    if score > -75: return "Bearish"
    return "Very Bearish"


def cot_crowding(record) -> str:
    if record is None or record.value is None:
        return "Unavailable"
    p = float(record.value)
    if p >= 90: return "Extreme net-long crowding risk"
    if p <= 10: return "Extreme net-short crowding risk"
    return "No extreme percentile crowding"


def build_relative_matrix(scores: dict[str, dict]):
    import pandas as pd
    assets = [a for a in scores if a != "XAU"]
    matrix = pd.DataFrame(index=assets, columns=assets, dtype=float)
    for base in assets:
        for quote in assets:
            a, b = scores[base]["score"], scores[quote]["score"]
            matrix.loc[base, quote] = None if a is None or b is None else max(-100, min(100, a - b))
    return matrix


def driver_lists(result: dict, limit: int = 5) -> tuple[list, list]:
    drivers = []
    for category, detail in result["categories"].items():
        for group in detail["groups"]:
            drivers.append({"name": f"{category} — {group['group']}", "score": group["score"]})
    return sorted([d for d in drivers if d["score"] > 0], key=lambda d: d["score"], reverse=True)[:limit], sorted(
        [d for d in drivers if d["score"] < 0], key=lambda d: d["score"])
