"""Global dashboard renderer."""

import streamlit as st
import pandas as pd
import plotly.express as px

from config import ASSETS


def render_dashboard(scores):
    st.subheader("Global fundamental dashboard")
    st.caption("MODEL RANKING — NOT A PRICE FORECAST")
    cols = st.columns(3)
    for i, asset in enumerate(ASSETS):
        item = scores[asset]
        score = item["score"]
        with cols[i % 3]:
            st.metric(asset, "Unavailable" if score is None else f"{score:+.1f}", item["bias"])
            st.caption(f"Confidence {item['confidence']:.0f}% · Coverage {item['coverage']:.0%}")
    available = [(a, s["score"]) for a, s in scores.items() if s["score"] is not None]
    if available:
        strongest = max(available, key=lambda x: x[1])
        weakest = min(available, key=lambda x: x[1])
        a, b = st.columns(2)
        a.info(f"Strongest model score: {strongest[0]} ({strongest[1]:+.1f})")
        b.info(f"Weakest model score: {weakest[0]} ({weakest[1]:+.1f})")
        frame = pd.DataFrame([{"Asset": asset, "Score": score} for asset, score in available]).sort_values("Score")
        fig = px.bar(frame, x="Score", y="Asset", color="Score", color_continuous_scale="RdYlGn",
                     range_color=(-100, 100), range_x=(-100, 100), title="Entered-data fundamental scores")
        fig.update_layout(height=360, coloraxis_showscale=False, xaxis_title="Score (−100 to +100)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
