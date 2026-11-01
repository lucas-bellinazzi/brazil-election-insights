"""Brazil Election Insights — Main Application Landing Page."""

import streamlit as st
from app.utils.session_state import get_cached_database, init_session_state

from election_research.database.queries import query_electoral_overview

st.set_page_config(
    page_title="Brazil Election Insights",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

st.title("🗳️ Brazil Election Insights")
st.subheader("Plataforma de Engenharia de Dados e Pesquisa Eleitoral Brasileira")

st.markdown(
    """
    O **Brazil Election Insights** é uma plataforma de código aberto dedicada à exploração,
    investigação e análise estatística de dados eleitorais oficiais publicados pelo
    **Tribunal Superior Eleitoral (TSE)**, com ênfase detalhada nos **Boletins de Urna (BUs)**.

    ---
    """
)

# Quick KPI Metrics
conn = get_cached_database()
overview = query_electoral_overview(conn, year=2026, election_round=2, office_code=1)

if overview:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total de Eleitores Aptos",
            value=f"{overview.get('total_eligible_voters', 0):,}".replace(",", "."),
        )
    with col2:
        st.metric(
            label="Comparecimento Geral",
            value=f"{overview.get('turnout_rate_pct', 0):.2f}%",
            delta=f"{overview.get('total_actual_turnout', 0):,}".replace(",", ".") + " votos",
        )
    with col3:
        st.metric(
            label="Abstenção Geral",
            value=f"{overview.get('abstention_rate_pct', 0):.2f}%",
            delta=f"-{overview.get('total_abstentions', 0):,}".replace(",", "."),
            delta_color="inverse",
        )
    with col4:
        st.metric(
            label="Seções Eleitorais Processadas",
            value=f"{overview.get('total_sections', 0):,}".replace(",", "."),
            delta="100% das urnas apuradas",
        )

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🏛️ Módulos de Pesquisa")
    st.markdown(
        """
        - **[01. Panorama Geral (Overview)](Overview)**: Indicadores eleitorais consolidados, totais de votos e ranking dos candidatos.
        - **[02. Explorador de Dados (Data Explorer)](Data_Explorer)**: Filtros por estado, município, zona eleitoral e urna individual.
        - **[03. Análise Estatística (Statistical Analysis)](Statistical_Analysis)**: Distribuições de votos, dispersão e detecção de sinais de anomalia.
        - **[04. Assistente de IA (AI Assistant)](AI_Assistant)**: Investigação interativa com ferramentas analíticas determinísticas.
        - **[05. Metodologia e Integridade (Methodology)](Methodology)**: Dicionário de dados, auditoria de hashes SHA-512 e regras matemáticas.
        """
    )

with col_right:
    st.markdown("### 🔒 Princípios de Integridade")
    st.markdown(
        """
        1. **Imutabilidade**: Os arquivos CSV brutos baixados do TSE nunca são modificados.
        2. **Rastreabilidade**: Hashes criptográficos SHA-512 garantem a integridade de ponta a ponta.
        3. **Rigor Metodológico**: Sinais estatísticos e anomalias são tratados como hipóteses de investigação, **nunca** como prova de fraude.
        4. **Auditabilidade**: Resultados analíticos reproduzíveis a partir de código aberto e dados abertos.
        """
    )
