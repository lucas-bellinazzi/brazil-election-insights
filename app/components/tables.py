"""Reusable table components and CSV download exporters."""

import polars as pl
import streamlit as st


def render_dataframe_with_download(
    df: pl.DataFrame,
    filename: str = "election_data.csv",
    use_container_width: bool = True,
    height: int | None = None,
) -> None:
    """Display a Polars dataframe with a direct CSV export download button."""
    p_df = df.to_pandas()
    st.dataframe(p_df, use_container_width=use_container_width, height=height)

    csv_bytes = df.write_csv().encode("utf-8")
    st.download_button(
        label="📥 Exportar Dados para CSV",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
    )
