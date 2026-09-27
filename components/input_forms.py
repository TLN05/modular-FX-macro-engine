"""Structured manual-entry form backed by the shared metric catalog."""

import streamlit as st

from config import ASSETS, DIRECTION_OPTIONS, STANCE_OPTIONS, metric_catalog
from providers.manual import ManualInputProvider
from utils.validation import validate_rows


def render_inputs():
    st.subheader("Manual data entry")
    st.caption("Blank values remain unavailable. Include a date and source so freshness and evidence quality are visible.")
    selected = st.selectbox("Asset to edit", ASSETS, key="input_asset")
    key = f"manual_rows_{selected}"
    if key not in st.session_state:
        st.session_state[key] = ManualInputProvider.blank_frame(selected)
    frame = st.session_state[key].copy()
    frame["date"] = frame["date"].astype("object")
    with st.expander("Metric guide", expanded=False):
        st.markdown("PMI scores compare the level with 50. REER percentile is a mild valuation headwind when elevated. Policy stance and directional fields use explicit categories. Change fields use the catalogued favorable/adverse direction. A current policy-rate or inflation level alone is not scored without suitable context.")
    edited = st.data_editor(
        frame,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=["metric_id", "metric_name", "category", "group", "polarity", "scale", "unit", "asset"],
        column_config={
            "metric_id": None, "asset": None, "group": None, "polarity": None, "scale": None,
            "metric_name": st.column_config.TextColumn("Metric", help="Standard catalog label"),
            "category": st.column_config.TextColumn("Category"),
            "value": st.column_config.TextColumn("Value", help="Enter a number or a documented category label; leave blank when unavailable"),
            "previous_value": st.column_config.NumberColumn("Previous", help="Optional previous observation"),
            "forecast": st.column_config.NumberColumn("Forecast", help="Optional consensus forecast"),
            "unit": st.column_config.TextColumn("Unit"),
            "date": st.column_config.DateColumn("Data date", format="YYYY-MM-DD"),
            "source": st.column_config.TextColumn("Source"),
            "frequency": st.column_config.SelectboxColumn("Frequency", options=["", "Daily", "Weekly", "Monthly", "Quarterly", "Event-driven"], required=False),
            "confidence": st.column_config.NumberColumn("Input reliability", min_value=0.0, max_value=1.0, step=0.05, help="Your assessment of input reliability"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        key=f"editor_{selected}",
    )
    st.session_state[key] = edited
    for warning in validate_rows(selected, edited):
        st.warning(warning)
    st.caption(f"{len(metric_catalog(selected))} standardized fields available for {selected}; unentered fields are not treated as zero.")

    # Category weights are editable, while the engine renormalizes after unavailable categories are removed.
    from config import CATEGORY_WEIGHTS, GOLD_CATEGORY_WEIGHTS
    base = GOLD_CATEGORY_WEIGHTS if selected == "XAU" else CATEGORY_WEIGHTS
    with st.expander("Model settings — category weights", expanded=False):
        st.caption("Weights must total 100%. The scoring engine renormalizes only across categories with valid observations.")
        weight_rows = st.session_state.setdefault(f"weight_rows_{selected}", dict(base))
        weights = {}
        cols = st.columns(3)
        for i, (category, default) in enumerate(base.items()):
            weights[category] = cols[i % 3].number_input(category, min_value=0.0, max_value=100.0,
                value=float(weight_rows.get(category, default)), step=1.0, key=f"weight_{selected}_{category}")
        st.session_state[f"weights_{selected}"] = weights
        total = sum(weights.values())
        if abs(total - 100) > 0.01:
            st.error(f"Weights currently total {total:.1f}%. Adjust them to total 100% before scoring.")
