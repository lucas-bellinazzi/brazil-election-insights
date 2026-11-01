"""Data Explorer page — Interactive drill-down into municipalities and polling stations."""

import streamlit as st
from app.components.filters import render_election_filters
from app.components.tables import render_dataframe_with_download
from app.utils.session_state import get_cached_database, init_session_state

from election_research.database.queries import (
    query_municipality_results,
    query_polling_sections,
)

st.set_page_config(page_title="Explorador de Dados — Brazil Election Insights", layout="wide")
init_session_state()

st.title("🔍 Explorador de Dados Eleitorais")
st.markdown("Investigue resultados no nível municipal e explore urnas eletrônicas individuais.")

filters = render_election_filters(include_uf=True)
conn = get_cached_database()

tab_munis, tab_sections = st.tabs(["🏛️ Resultados por Município", "🗳️ Boletins de Urna (BUs)"])

with tab_munis:
    st.subheader("Resultados Municipais")
    search_query = st.text_input(
        "Filtrar por nome do município:",
        placeholder="Ex: RIO BRANCO, CAMPINAS, SÃO PAULO...",
    )

    munis_df = query_municipality_results(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        office_code=filters["office_code"],
        uf=filters["uf"],
        name_filter=search_query if search_query else None,
        limit=200,
    )

    if len(munis_df) > 0:
        st.write(f"Exibindo **{len(munis_df)}** municípios:")
        render_dataframe_with_download(
            munis_df,
            filename=f"municipios_{filters['year']}_{filters['round']}t.csv",
        )
    else:
        st.info("Nenhum município encontrado com os filtros aplicados.")

with tab_sections:
    st.subheader("Auditoria de Seções e Urnas Eletrônicas")
    target_uf = filters["uf"] or "AC"
    st.markdown(f"Exibindo seções para a Unidade Federativa: **{target_uf}**")

    col_zone, col_limit = st.columns(2)
    with col_zone:
        zone_input = st.number_input("Zona Eleitoral (0 para todas):", min_value=0, value=0, step=1)
    with col_limit:
        limit_input = st.slider("Limite de seções:", min_value=10, max_value=500, value=50, step=10)

    selected_zone = zone_input if zone_input > 0 else None
    sections_df = query_polling_sections(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        uf=target_uf,
        zone=selected_zone,
        limit=limit_input,
    )

    if len(sections_df) > 0:
        st.write(f"Exibindo **{len(sections_df)}** seções eleitorais:")
        render_dataframe_with_download(
            sections_df,
            filename=f"secoes_{target_uf}_{filters['year']}_{filters['round']}t.csv",
        )
    else:
        st.info("Nenhuma seção encontrada para a zona especificada.")
