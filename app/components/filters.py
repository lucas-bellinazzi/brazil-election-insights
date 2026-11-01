"""Reusable sidebar and top-level filter controls for Streamlit."""

from typing import Any

import streamlit as st

UF_LIST = [
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
    "ZZ",
]

OFFICE_MAP = {
    "Presidente": 1,
    "Governador": 3,
    "Senador": 5,
    "Deputado Federal": 6,
    "Deputado Estadual": 7,
}


def render_election_filters(include_uf: bool = True) -> dict[str, Any]:
    """Render standardized election scope filters in the Streamlit sidebar."""
    st.sidebar.header("🎯 Parâmetros Eleitorais")

    # Year
    year = st.sidebar.selectbox("Ano da Eleição", options=[2026], index=0)

    # Round
    round_label = st.sidebar.selectbox("Turno", options=["2º Turno (2t)", "1º Turno (1t)"], index=0)
    selected_round = 2 if "2t" in round_label else 1

    # Office
    office_names = list(OFFICE_MAP.keys())
    office_name = st.sidebar.selectbox("Cargo", options=office_names, index=0)
    office_code = OFFICE_MAP[office_name]

    # UF
    selected_uf = None
    if include_uf:
        uf_options = ["Todos os Estados (Nacional)"] + UF_LIST
        uf_choice = st.sidebar.selectbox("Unidade Federativa (UF)", options=uf_options, index=0)
        if uf_choice != "Todos os Estados (Nacional)":
            selected_uf = uf_choice

    return {
        "year": year,
        "round": selected_round,
        "office_code": office_code,
        "office_name": office_name,
        "uf": selected_uf,
    }
