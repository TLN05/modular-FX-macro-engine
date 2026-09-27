"""Per-asset score transparency and explanations."""

import streamlit as st

from scoring_engine import driver_lists


def render_detail(asset, result):
    st.subheader(f"{asset} fundamental detail")
    if result["score"] is None:
        st.info("No scorable data is available yet. Enter dated values in Manual inputs.")
        return
    a, b, c, d, e = st.columns(5)
    a.metric("Fundamental score", f"{result['score']:+.1f}", result["bias"])
    b.metric("Confidence", f"{result['confidence']:.0f}%")
    c.metric("Data coverage", f"{result['coverage']:.0%}")
    d.metric("Category alignment", f"{result['alignment']:.0%}")
    e.metric("Signal magnitude", f"{result['signal_magnitude']:.0%}")
    if result["alignment"] < 0.58:
        st.warning("Mixed fundamental environment: major categories show limited agreement.")
    positive, negative = driver_lists(result)
    left, right = st.columns(2)
    with left:
        st.markdown("**Top supportive drivers**")
        st.write("\n".join(f"• {d['name']}: {d['score']:+.0f}" for d in positive) if positive else "No positive scored drivers.")
    with right:
        st.markdown("**Top adverse drivers**")
        st.write("\n".join(f"• {d['name']}: {d['score']:+.0f}" for d in negative) if negative else "No negative scored drivers.")
    if result["crowding"] != "Unavailable":
        st.caption(f"COT crowding condition: {result['crowding']}. Direction and crowding are displayed separately.")
    st.markdown("**Category breakdown**")
    st.dataframe(result["contributions"], hide_index=True, use_container_width=True)
    with st.expander("Score calculation", expanded=False):
        st.dataframe(result["metric_rows"], hide_index=True, use_container_width=True)
        st.caption("Metric weights divide category weight across driver groups and then across metrics in each group. The displayed contributions sum to the final score. Active category weights are renormalized to 100%.")
