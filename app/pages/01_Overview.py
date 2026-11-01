"""Overview page — Consolidated national indicators and candidate rankings."""

import streamlit as st
from app.components.charts import (
    create_candidate_ranking_chart,
    create_state_turnout_bar_chart,
    create_vote_composition_donut,
)
from app.components.filters import render_election_filters
from app.components.tables import render_dataframe_with_download
from app.utils.session_state import get_cached_database, init_session_state

from election_research.database.queries import (
    query_candidate_rankings,
    query_electoral_overview,
    query_state_results,
)

st.set_page_config(page_title="Panorama Geral — Brazil Election Insights", layout="wide")
init_session_state()

st.title("📊 Panorama Geral Eleitoral")
st.markdown("Consolidação dos resultados apurados a partir dos Boletins de Urna oficiais do TSE.")

filters = render_election_filters(include_uf=False)
conn = get_cached_database()

overview = query_electoral_overview(
    conn,
    year=filters["year"],
    election_round=filters["round"],
    office_code=filters["office_code"],
)

if not overview:
    st.warning("Nenhum dado analítico encontrado para os parâmetros selecionados.")
    st.stop()

# 1. Main KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "Eleitorado Apto",
        f"{overview['total_eligible_voters']:,}".replace(",", "."),
    )
with col2:
    st.metric(
        "Comparecimento Total",
        f"{overview['total_actual_turnout']:,}".replace(",", "."),
        delta=f"{overview['turnout_rate_pct']:.2f}% dos aptos",
    )
with col3:
    st.metric(
        "Abstenções",
        f"{overview['total_abstentions']:,}".replace(",", "."),
        delta=f"{overview['abstention_rate_pct']:.2f}% dos aptos",
        delta_color="inverse",
    )
with col4:
    st.metric(
        "Seções Apuradas",
        f"{overview['total_sections']:,}".replace(",", "."),
        delta="100% processadas",
    )

st.markdown("---")

# 2. Candidate Rankings & Vote Composition
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader(f"🏆 Resultado para {filters['office_name']}")
    cand_df = query_candidate_rankings(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        office_code=filters["office_code"],
    )
    if len(cand_df) > 0:
        fig_cand = create_candidate_ranking_chart(
            cand_df, title=f"Votação — {filters['office_name']}"
        )
        st.plotly_chart(fig_cand, use_container_width=True)
    else:
        st.info("Nenhum candidato registrado para este cargo.")

with col_right:
    st.subheader("🥧 Distribuição de Votos")
    fig_donut = create_vote_composition_donut(
        valid_votes=overview["total_valid_votes"],
        blank_votes=overview["total_blank_votes"],
        null_votes=overview["total_null_votes"],
    )
    st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("---")

# 3. State-by-State Comparison
st.subheader("🗺️ Comparecimento e Abstenção por Unidade Federativa")
states_df = query_state_results(
    conn,
    year=filters["year"],
    election_round=filters["round"],
    office_code=filters["office_code"],
)

if len(states_df) > 0:
    fig_states = create_state_turnout_bar_chart(states_df)
    st.plotly_chart(fig_states, use_container_width=True)

    with st.expander("📋 Ver Tabela Detalhada por Estado (UF)"):
        render_dataframe_with_download(
            states_df,
            filename=f"resumo_estados_{filters['year']}_{filters['round']}t.csv",
        )
