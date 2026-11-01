"""Statistical Analysis page — Distribution exploration and anomaly detection signals."""

import streamlit as st
from app.components.charts import create_metric_histogram
from app.components.filters import render_election_filters
from app.components.tables import render_dataframe_with_download
from app.utils.session_state import get_cached_database, init_session_state

from election_research.analytics.anomalies import (
    NEUTRAL_DISCLAIMER,
    detect_anomalies_iqr,
    detect_anomalies_isolation_forest,
    detect_anomalies_zscore,
)
from election_research.analytics.statistical_tests import compute_distribution_summary
from election_research.database.queries import query_municipality_results

st.set_page_config(page_title="Análise Estatística — Brazil Election Insights", layout="wide")
init_session_state()

st.title("📈 Análise Estatística e Sinais de Anomalia")
st.markdown(
    "Explore distribuições estatísticas municipais e identifique desvios empíricos com rigor metodológico."
)

st.info(f"⚖️ **Nota Metodológica Fundamental:** {NEUTRAL_DISCLAIMER}")

filters = render_election_filters(include_uf=True)
conn = get_cached_database()

# Fetch municipality dataset
munis_df = query_municipality_results(
    conn,
    year=filters["year"],
    election_round=filters["round"],
    office_code=filters["office_code"],
    uf=filters["uf"],
    limit=10000,
)

if len(munis_df) == 0:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# Metric selection
metric_options = {
    "Taxa de Abstenção (%)": "abstention_rate_pct",
    "Taxa de Comparecimento (%)": "turnout_rate_pct",
    "Taxa de Votos em Branco (%)": "blank_vote_rate_pct",
    "Taxa de Votos Nulos (%)": "null_vote_rate_pct",
}
selected_metric_label = st.selectbox("Selecione a Métrica Analítica:", list(metric_options.keys()))
selected_metric_col = metric_options[selected_metric_label]

tab_dist, tab_anom = st.tabs(["📊 Distribuição Estatística", "🎯 Detecção de Sinais de Anomalia"])

with tab_dist:
    st.subheader(f"Distribuição: {selected_metric_label}")
    summary = compute_distribution_summary(munis_df[selected_metric_col])

    if summary:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Média", f"{summary['mean']:.2f}%")
        col2.metric("Desvio Padrão", f"{summary['std']:.2f}%")
        col3.metric("Mediana", f"{summary['median']:.2f}%")
        col4.metric("Intervalo Interquartil (IQR)", f"{summary['iqr']:.2f}%")
        col5.metric("Assimetria (Skewness)", f"{summary['skewness']:.2f}")

    fig_hist = create_metric_histogram(
        munis_df,
        col_name=selected_metric_col,
        title=f"Histograma e Boxplot — {selected_metric_label} ({len(munis_df)} municípios)",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with tab_anom:
    st.subheader("Identificação de Sinais de Anomalia")
    st.markdown(
        """
        Esta ferramenta utiliza múltiplos algoritmos estatísticos complementares para sinalizar
        observações empíricas que se distanciam significativamente dos padrões esperados.
        """
    )

    col_algo, col_thresh = st.columns(2)
    with col_algo:
        algo_choice = st.selectbox(
            "Método de Detecção:",
            [
                "Z-Score (Desvio Paramétrico)",
                "IQR (Não-Paramétrico)",
                "Isolation Forest (Multivariado)",
            ],
        )

    if "Z-Score" in algo_choice:
        with col_thresh:
            z_thresh = st.slider(
                "Limiar Z (desvios padrão):", min_value=2.0, max_value=5.0, value=3.0, step=0.5
            )
        flagged_df = detect_anomalies_zscore(
            munis_df, metric_col=selected_metric_col, threshold=z_thresh
        )

    elif "IQR" in algo_choice:
        with col_thresh:
            iqr_factor = st.slider(
                "Fator multiplicador do IQR:", min_value=1.5, max_value=3.0, value=1.5, step=0.5
            )
        flagged_df = detect_anomalies_iqr(
            munis_df, metric_col=selected_metric_col, factor=iqr_factor
        )

    else:
        with col_thresh:
            contam = st.slider(
                "Taxa de contaminação esperada:",
                min_value=0.005,
                max_value=0.05,
                value=0.01,
                step=0.005,
            )
        features = ["abstention_rate_pct", "turnout_rate_pct", "valid_vote_rate_pct"]
        flagged_df = detect_anomalies_isolation_forest(
            munis_df, feature_cols=features, contamination=contam
        )

    st.write(f"Sinais estatísticos identificados: **{len(flagged_df)}** município(s)")

    if len(flagged_df) > 0:
        render_dataframe_with_download(
            flagged_df,
            filename=f"sinais_anomalia_{selected_metric_col}.csv",
        )
    else:
        st.success("Nenhuma anomalia identificada com os parâmetros e limiares configurados.")
