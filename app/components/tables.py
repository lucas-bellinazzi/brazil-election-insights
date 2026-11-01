"""Reusable table components and CSV download exporters."""

from typing import Any

import polars as pl
import streamlit as st


def render_dataframe_with_download(
    df: pl.DataFrame,
    filename: str = "election_data.csv",
    use_container_width: bool | None = None,
    width: str | int | None = None,
    height: int | str | None = None,
) -> None:
    """Display a Polars dataframe with a direct CSV export download button."""
    p_df = df.to_pandas()

    effective_width = width
    if effective_width is None:
        if use_container_width is not None:
            effective_width = "stretch" if use_container_width else "content"
        else:
            effective_width = "stretch"

    dataframe_kwargs: dict[str, Any] = {"width": effective_width}
    if height is not None:
        dataframe_kwargs["height"] = height

    st.dataframe(p_df, **dataframe_kwargs)

    csv_bytes = df.write_csv().encode("utf-8")
    st.download_button(
        label="📥 Exportar Dados para CSV",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
    )
