"""FX Fundamental Strength & Macro Bias Engine — manual-input first edition."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from components.currency_detail import render_detail
from components.dashboard import render_dashboard
from components.input_forms import render_inputs
from components.matrix import render_matrix
from config import ASSETS, CATEGORY_WEIGHTS, GOLD_CATEGORY_WEIGHTS
from providers.manual import ManualInputProvider
from scoring_engine import score_asset
from utils.validation import validate_rows


st.set_page_config(page_title="FX Fundamental Strength & Macro Bias Engine", page_icon="🌐", layout="wide")
st.title("FX Fundamental Strength & Macro Bias Engine")
st.caption("Rules-based macro assessment · Fundamental bias only · No trading signals")
st.warning("This model ranks entered fundamental evidence. It does not forecast price returns or recommend trades.")

tab_dashboard, tab_inputs, tab_detail, tab_matrix, tab_method = st.tabs(
    ["Global dashboard", "Manual inputs", "Asset detail", "Currency matrix", "Methodology"]
)

with tab_inputs:
    render_inputs()

# Construct records through the provider interface; calculation code has no ingestion-source dependency.
all_records = []
validation_errors = []
for asset in ASSETS:
    state_key = f"manual_rows_{asset}"
    if state_key not in st.session_state:
        st.session_state[state_key] = ManualInputProvider.blank_frame(asset)
    rows = st.session_state[state_key]
    validation_errors.extend(validate_rows(asset, rows))
    all_records.extend(ManualInputProvider(rows).fetch_records())

scores = {}
for asset in ASSETS:
    weight_map = st.session_state.get(f"weights_{asset}")
    defaults = GOLD_CATEGORY_WEIGHTS if asset == "XAU" else CATEGORY_WEIGHTS
    if not weight_map or abs(sum(weight_map.values()) - 100) > 0.01:
        weight_map = defaults
    scores[asset] = score_asset(asset, all_records, weight_map)

with tab_dashboard:
    render_dashboard(scores)
    if validation_errors:
        with st.expander(f"Input warnings ({len(validation_errors)})", expanded=False):
            for error in validation_errors:
                st.warning(error)

with tab_detail:
    asset = st.selectbox("Asset detail", ASSETS, key="detail_asset")
    render_detail(asset, scores[asset])

with tab_matrix:
    render_matrix(scores)
    available = [(a, r["score"]) for a, r in scores.items() if a != "XAU" and r["score"] is not None]
    if available:
        ranked = sorted(available, key=lambda x: x[1], reverse=True)
        st.markdown("**Current model ranking — not a price forecast**")
        st.write(" → ".join(f"{asset} ({score:+.1f})" for asset, score in ranked))
    st.markdown("**Pair comparison**")
    base, quote = st.columns(2)
    base_asset = base.selectbox("Base", [a for a in ASSETS if a != "XAU"], index=6, key="pair_base")
    quote_asset = quote.selectbox("Quote", [a for a in ASSETS if a != "XAU"], index=0, key="pair_quote")
    a_score, b_score = scores[base_asset]["score"], scores[quote_asset]["score"]
    if a_score is None or b_score is None:
        st.info("Pair score unavailable until both assets have scorable inputs.")
    else:
        relative = max(-100, min(100, a_score - b_score))
        st.metric(f"{base_asset}/{quote_asset} relative fundamental score", f"{relative:+.1f}",
                  "Fundamental advantage to base" if relative > 0 else "Fundamental advantage to quote" if relative < 0 else "No score difference")
        record_index = {(r.asset, r.metric_id): r.value for r in all_records}
        st.markdown("**Entered rate and yield differentials (base − quote)**")
        differential_rows = []
        for metric_id, label in [
            ("policy_rate", "Current policy rate"), ("expected_rate_3m", "Expected policy rate · 3M"),
            ("expected_rate_6m", "Expected policy rate · 6M"), ("expected_rate_12m", "Expected policy rate · 12M"),
            ("yield_2y_level", "2-year yield"), ("yield_10y_level", "10-year yield"),
        ]:
            left = record_index.get((base_asset, metric_id))
            right = record_index.get((quote_asset, metric_id))
            try:
                difference = float(left) - float(right) if left is not None and right is not None else None
            except (TypeError, ValueError):
                difference = None
            differential_rows.append({"Metric": label, "Differential": difference})
        st.dataframe(pd.DataFrame(differential_rows), hide_index=True, use_container_width=True)

with tab_method:
    st.subheader("Architecture and model methodology")
    st.markdown("**Provider boundary**\n\n`DataProvider.fetch_records()` returns canonical `MetricRecord` objects. Version 1 uses `ManualInputProvider`; the scoring and display layers consume only that schema. A future provider can implement the same interface without edits to normalization, scoring, weights, or dashboard components.")
    st.markdown("**Canonical metric schema**\n\n`metric_name`, `asset`, `category`, `value`, `previous_value`, `forecast`, `unit`, `date`, `source`, `frequency`, `raw_score`, `weight`, `contribution`, `confidence`, and `notes`. Catalog metadata adds stable metric ID, aggregation group, polarity, and normalization scale.")
    st.markdown("**Scoring**\n\nEach metric gets a documented −100…+100 normalized score. PMI measures distance from 50; directional categories use explicit −100/0/+100 mappings; continuous fields use a catalog scale and direction. Raw level is not treated as a cross-currency signal where level alone is misleading (for example policy rates and CPI).")
    st.markdown("**No double counting**\n\nRelated observations are averaged within a driver group, then driver groups within categories. Category weights are applied only after aggregation. This limits repeated measures of the same macro driver from creating extra weight. Available category weights renormalize over scorable observations; blank values remain unavailable.")
    st.markdown("**Confidence**\n\nConfidence combines data coverage (45%), freshness (20%), input reliability (15%), category alignment (15%), and signal magnitude (5%). It remains separate from the direction score. Dated records are fresh through 35 days, aging through 90 days, then stale; undated values reduce freshness confidence.")
    st.markdown("**Limitations / manual data**\n\nThe current version requires the user to enter observations, dates, sources, and any available previous/forecast values. If an expected rate path has no prior observation, that field is not scored. Category-level availability is transparent; confidence and coverage should be interpreted alongside the entered sample.")
    st.markdown("**Default category weights**")
    st.dataframe(pd.DataFrame([{"Category": c, "Currency weight": w, "Gold weight": GOLD_CATEGORY_WEIGHTS.get(c, 0)}
                               for c, w in CATEGORY_WEIGHTS.items()]), hide_index=True, use_container_width=True)

with st.sidebar:
    st.header("Data state")
    entered = sum(1 for r in all_records if r.value is not None)
    st.metric("Values entered", entered)
    st.caption("Data is manually entered and remains in this browser session.")
    export_rows = [r.to_dict() for r in all_records if r.value is not None]
    st.download_button("Download entered data (JSON)", json.dumps(export_rows, indent=2, default=str),
                       file_name="fx_fundamental_manual_inputs.json", mime="application/json")
