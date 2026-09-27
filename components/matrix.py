"""Relative currency matrix."""

import streamlit as st

from scoring_engine import build_relative_matrix


def render_matrix(scores):
    st.subheader("Relative fundamental matrix")
    st.caption("Cell = row currency score − column currency score. Ranking is not a return forecast.")
    matrix = build_relative_matrix(scores)
    st.dataframe(matrix.style.format("{:+.1f}", na_rep="—").background_gradient(cmap="RdYlGn", vmin=-100, vmax=100),
                 use_container_width=True)
