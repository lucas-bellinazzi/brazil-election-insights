"""Closing Times Analysis page — Exploration of voting machine closing times, extensions, and patterns."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from app.components.charts import (
    create_candidate_by_closing_regime_chart,
    create_closing_regime_donut,
    create_closing_timeline_chart,
    create_state_extension_bar_chart,
)
from app.components.filters import render_election_filters
from app.components.tables import render_dataframe_with_download
from app.utils.session_state import get_cached_database, init_session_state

from election_research.analytics.closing_times import compute_geographic_extension_disparity
from election_research.database.queries import (
    query_closing_time_by_state,
    query_closing_time_candidates,
    query_closing_time_municipalities,
    query_closing_time_overview,
    query_closing_time_timeline,
)

st.set_page_config(
    page_title="Horários de Encerramento — Brazil Election Insights",
    page_icon="⏰",
    layout="wide",
)

init_session_state()

st.title("⏰ Análise dos Horários de Encerramento das Urnas")
st.markdown(
    """
    Investigação empírica da distribuição temporal de encerramento das urnas eletrônicas e emissão
    dos Boletins de Urna (BUs) no território nacional, com normalização de fusos horários para o
    **Horário Oficial de Brasília (BRT)**.
    """
)

# 1. Sidebar Filters
conn = get_cached_database()
filters = render_election_filters(conn)

selected_uf = filters["uf"]

# 2. Query Overview Data
overview = query_closing_time_overview(
    conn,
    year=filters["year"],
    election_round=filters["round"],
    uf=selected_uf,
)

if not overview or overview.get("total_sections", 0) == 0:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# 3. Contextual Callout
st.info(
    """
    📌 **Contexto Eleitoral & Regra de Integridade**:
    O horário padrão de votação no Brasil é das 8h às 17h. Excepcionalmente no 2º turno de 2026,
    o encerramento foi estendido por 2 horas (até às 19h BRT). Contudo, em decorrência da arquitetura
    de segurança criptográfica da urna eletrônica, as seções que já haviam emitido o Boletim de Urna
    às 17h não puderam ser reabertas. Esta análise mapeia a divisão empírica resultante desse evento.
    """
)

# 4. KPI Metrics Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total de Seções Mapeadas",
        value=f"{overview['total_sections']:,}".replace(",", "."),
        help="Total de urnas eletrônicas processadas com registro de encerramento.",
    )

with col2:
    st.metric(
        label="Urnas no Horário Regular",
        value=f"{overview['regular_count']:,}".replace(",", "."),
        delta=f"{overview['regular_pct']:.2f}% do total (17h00 - 17h09)",
        delta_color="normal",
        help="Urnas encerradas no horário convencional padrão.",
    )

with col3:
    st.metric(
        label="Urnas com Prorrogação",
        value=f"{overview['extended_count']:,}".replace(",", "."),
        delta=f"{overview['extended_pct']:.2f}% do total (17h10 - 19h05+)",
        delta_color="inverse",
        help="Urnas que continuaram operando aproveitando a prorrogação decretada.",
    )

with col4:
    turnout_diff = overview["extended_turnout_pct"] - overview["regular_turnout_pct"]
    delta_str = f"{turnout_diff:+.2f} p.p. vs regular" if turnout_diff != 0 else "0.0 p.p."
    st.metric(
        label="Comparecimento Prorrogadas",
        value=f"{overview['extended_turnout_pct']:.2f}%",
        delta=delta_str,
        delta_color="normal",
        help="Taxa de comparecimento observada nas seções que permaneceram abertas.",
    )

st.markdown("---")

# 5. Tabbed Detailed Analysis
tab_timeline, tab_geo, tab_candidates, tab_methodology = st.tabs(
    [
        "📈 Linha do Tempo & Fluxo",
        "🗺️ Disparidade Territorial (UFs e Municípios)",
        "🗳️ Votação dos Candidatos",
        "📚 Normalização & Metodologia",
    ]
)

# -------------------------------------------------------------
# TAB 1: Timeline & Flow
# -------------------------------------------------------------
with tab_timeline:
    st.subheader("Fluxo Temporal de Fechamento das Seções")
    st.markdown(
        """
        O gráfico dinâmico abaixo exibe o número de urnas fechadas a cada intervalo de 5 minutos,
        acompanhado da curva de percentual acumulado de seções apuradas no país.
        """
    )

    timeline_df = query_closing_time_timeline(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        uf=selected_uf,
        bucket_minutes=5,
    )

    if not timeline_df.is_empty():
        fig_timeline = create_closing_timeline_chart(
            timeline_df,
            title=f"Velocidade de Encerramento das Urnas — {selected_uf or 'Brasil'} ({filters['year']} / {filters['round']}º Turno)",
        )
        st.plotly_chart(fig_timeline, width="stretch")

    col_donut, col_kpis_regime = st.columns([1, 1])
    with col_donut:
        fig_donut = create_closing_regime_donut(
            overview,
            title=f"Divisão dos Regimes de Fechamento ({selected_uf or 'Brasil'})",
        )
        st.plotly_chart(fig_donut, width="stretch")

    with col_kpis_regime:
        st.subheader("Detalhamento por Janela Temporal")
        early_ext = max(
            0,
            overview["extended_count"]
            - overview["full_extended_count"]
            - overview["late_queues_count"],
        )
        st.markdown(
            f"""
            - **Horário Regular (17:00 às 17:09)**: **{overview["regular_count"]:,}** urnas ({overview["regular_pct"]:.2f}%)
              - *Comparecimento*: `{overview["regular_turnout_pct"]:.2f}%` | *Abstenção*: `{overview["regular_abstention_pct"]:.2f}%`
            - **Prorrogação Inicial (17:10 às 18:29)**: **{early_ext:,}** urnas ({early_ext * 100.0 / overview["total_sections"]:.2f}%)
              - Seções que estenderam a votação mas encerraram antes do teto final.
            - **Prorrogação Integral (18:30 às 19:05)**: **{overview["full_extended_count"]:,}** urnas ({overview["full_extended_count"] * 100.0 / overview["total_sections"]:.2f}%)
              - Seções que absorveram integralmente as 2 horas adicionais decretadas.
            - **Filas com Senha (> 19:05)**: **{overview["late_queues_count"]:,}** urnas ({overview["late_queues_count"] * 100.0 / overview["total_sections"]:.2f}%)
              - Seções com contingência de atendimento até o esgotamento das filas.
            """.replace(",", ".")
        )

# -------------------------------------------------------------
# TAB 2: Geographic Disparity (States & Municipalities)
# -------------------------------------------------------------
with tab_geo:
    st.subheader("Concentração Territorial da Prorrogação de Horário")
    st.markdown(
        """
        A adesão e absorção da prorrogação de 2 horas apresentou intensa variação regional, refletindo
        fatores como densidade populacional, tempo de espera prévio e dinâmicas dos polos de votação.
        """
    )

    states_closing_df = query_closing_time_by_state(
        conn,
        year=filters["year"],
        election_round=filters["round"],
    )

    if not states_closing_df.is_empty():
        disparity_metrics = compute_geographic_extension_disparity(states_closing_df)
        if disparity_metrics:
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric(
                    label="UF com Maior % de Prorrogação",
                    value=f"{disparity_metrics['highest_state']} ({disparity_metrics['highest_pct']:.2f}%)",
                )
            with m_col2:
                st.metric(
                    label="UF com Menor % de Prorrogação",
                    value=f"{disparity_metrics['lowest_state']} ({disparity_metrics['lowest_pct']:.2f}%)",
                )
            with m_col3:
                st.metric(
                    label="Razão de Disparidade Inter-Estadual",
                    value=f"{disparity_metrics['disparity_ratio']}x",
                    help="Fator multiplicativo entre o estado com maior e menor adesão à prorrogação.",
                )

        fig_states = create_state_extension_bar_chart(
            states_closing_df,
            title="Ranking das UFs por Percentual de Urnas com Prorrogação de Horário",
        )
        st.plotly_chart(fig_states, width="stretch")

    st.markdown("---")
    st.subheader("Municípios com Maior Concentração de Seções Prorrogadas")
    muni_closing_df = query_closing_time_municipalities(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        uf=selected_uf,
        top_n=30,
    )

    if not muni_closing_df.is_empty():
        render_dataframe_with_download(
            muni_closing_df,
            filename=f"municipios_prorrogados_{filters['year']}_{filters['round']}t.csv",
        )

# -------------------------------------------------------------
# TAB 3: Candidate Voting Patterns
# -------------------------------------------------------------
with tab_candidates:
    st.subheader("Desempenho dos Candidatos por Regime de Encerramento")
    st.markdown(
        """
        Comparativo da proporção de votos válidos obtida pelos candidatos nos diferentes regimes
        operacionais de encerramento da urna.
        """
    )

    cand_closing_df = query_closing_time_candidates(
        conn,
        year=filters["year"],
        election_round=filters["round"],
        office_code=1,
        uf=selected_uf,
    )

    if not cand_closing_df.is_empty():
        fig_cand_regimes = create_candidate_by_closing_regime_chart(
            cand_closing_df,
            title=f"Votos Válidos (%) por Regime de Encerramento — {selected_uf or 'Brasil'}",
        )
        st.plotly_chart(fig_cand_regimes, width="stretch")

        st.subheader("Tabela de Votação Nominal e Percentual")
        render_dataframe_with_download(
            cand_closing_df,
            filename=f"candidatos_regimes_fechamento_{filters['year']}_{filters['round']}t.csv",
        )
    else:
        st.info("Nenhum registro de votação encontrado para os critérios selecionados.")

# -------------------------------------------------------------
# TAB 4: Methodology & Timezone Normalization
# -------------------------------------------------------------
with tab_methodology:
    st.subheader("Metodologia de Normalização dos Fusos Horários")
    st.markdown(
        """
        O Brasil abrange múltiplos fusos horários. A urna eletrônica registra internamente os campos
        `DT_ABERTURA` e `DT_ENCERRAMENTO` de acordo com a hora local configurada no município durante a
        cerimônia de carga e lacre:

        | Fuso Oficial | Estados / Regiões | Diferença p/ Horário de Brasília | Horário Local de 17h BRT |
        | :--- | :--- | :--- | :--- |
        | **UTC-3** | Maioria dos Estados (SP, RJ, MG, BA, RS, PR, etc.) | 0h (Mesmo Horário) | **17:00** |
        | **UTC-4** | Mato Grosso (MT), Mato Grosso do Sul (MS), Rondônia (RO), Roraima (RR), Leste do Amazonas (AM) | -1 hora | **16:00** |
        | **UTC-5** | Acre (AC) e Sudoeste do Amazonas (Tabatinga, Benjamin Constant, Eirunepé, etc.) | -2 horas | **15:00** |

        ### Regra de Normalização Determinística Aplicada
        Para que todas as urnas possam ser analisadas e comparadas sob a mesma régua temporal,
        o sistema aplica a seguinte conversão determinística em SQL sobre a coluna `poll_closed_at`:

        ```sql
        CASE 
            WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
            WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
            ELSE CAST(poll_closed_at AS TIMESTAMP)
        END AS poll_closed_brt
        ```

        ### O Princípio da Irreversibilidade do Boletim de Urna
        Conforme a especificação de segurança do Tribunal Superior Eleitoral (TSE), o encerramento da urna
        é uma operação criptograficamente definitiva:
        1. A chave de votação é finalizada e as assinaturas digitais do BU são geradas via hardware de segurança.
        2. A mídia de resultado é gerada e o arquivo assinado.
        3. O sistema operacional da urna não prevê, por projeto, mecanismo de desfazimento ou reabertura.
        
        Isso fundamenta empiricamente por que as urnas encerradas pontualmente no horário regular não puderam
        ser reabertas quando a decisão judicial de prorrogação entrou em vigor.
        """
    )
