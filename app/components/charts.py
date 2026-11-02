"""Plotly visualization components for Brazilian election insights."""

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import polars as pl


def create_candidate_ranking_chart(
    df: pl.DataFrame, title: str = "Votação por Candidato"
) -> go.Figure:
    """Horizontal bar chart showing candidate votes and vote percentages."""
    p_df = df.to_pandas()
    # Sort for bottom-up horizontal bar
    p_df = p_df.sort_values(by="total_candidate_votes", ascending=True)

    fig = px.bar(
        p_df,
        x="total_candidate_votes",
        y="candidate_name",
        orientation="h",
        text="valid_vote_share_pct",
        color="party_abbreviation",
        title=title,
        labels={
            "total_candidate_votes": "Total de Votos",
            "candidate_name": "Candidato",
            "valid_vote_share_pct": "% Votos Válidos",
            "party_abbreviation": "Partido",
        },
    )
    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Votos: %{x:,}<br>Percentual Válidos: %{text:.2f}%<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white",
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 20, "r": 40, "t": 50, "b": 20},
    )
    return fig


def create_vote_composition_donut(valid_votes: int, blank_votes: int, null_votes: int) -> go.Figure:
    """Donut chart illustrating proportion of Valid vs Blank vs Null votes."""
    labels = ["Votos Válidos", "Votos em Branco", "Votos Nulos"]
    values = [valid_votes, blank_votes, null_votes]
    colors = ["#2b5c8f", "#d3d3d3", "#e05252"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker={"colors": colors},
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Votos: %{value:,}<br>Proporção: %{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Composição dos Votos Totais",
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def create_state_turnout_bar_chart(df: pl.DataFrame) -> go.Figure:
    """Bar chart comparing turnout and abstention rates across UFs."""
    p_df = df.to_pandas()
    p_df = p_df.sort_values(by="turnout_rate_pct", ascending=False)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=p_df["state_abbreviation"],
            y=p_df["turnout_rate_pct"],
            name="Comparecimento (%)",
            marker_color="#2b5c8f",
        )
    )
    fig.add_trace(
        go.Bar(
            x=p_df["state_abbreviation"],
            y=p_df["abstention_rate_pct"],
            name="Abstenção (%)",
            marker_color="#e05252",
        )
    )
    fig.update_layout(
        barmode="stack",
        title="Taxas de Comparecimento e Abstenção por UF",
        yaxis={"title": "Percentual (%)", "range": [0, 100]},
        xaxis={"title": "UF"},
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def create_metric_histogram(
    df: pl.DataFrame, col_name: str, title: str, nbins: int = 30
) -> go.Figure:
    """Histogram for analyzing metric distributions (e.g. abstention rates)."""
    p_df = df.to_pandas()
    fig = px.histogram(
        p_df,
        x=col_name,
        nbins=nbins,
        marginal="box",
        title=title,
        color_discrete_sequence=["#2b5c8f"],
    )
    fig.update_layout(
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        xaxis={"title": col_name},
        yaxis={"title": "Frequência"},
    )
    return fig


def create_closing_timeline_chart(
    df: pl.DataFrame, title: str = "Fluxo Temporal de Encerramento das Urnas (Horário de Brasília)"
) -> go.Figure:
    """Dynamic combo chart showing polling section closure velocity and cumulative completion in BRT."""
    p_df = df.to_pandas()
    fig = go.Figure()

    # Bar chart for interval count
    fig.add_trace(
        go.Bar(
            x=p_df["bin_time"],
            y=p_df["num_sections"],
            name="Urnas Encerradas no Intervalo",
            marker_color="#2b5c8f",
            yaxis="y",
            hovertemplate="<b>Horário: %{x} BRT</b><br>Urnas encerradas: %{y:,}<extra></extra>",
        )
    )

    # Line chart for cumulative percentage on secondary axis
    fig.add_trace(
        go.Scatter(
            x=p_df["bin_time"],
            y=p_df["cumulative_pct"],
            name="% Acumulado de Urnas",
            line={"color": "#e05252", "width": 3},
            yaxis="y2",
            hovertemplate="<b>Horário: %{x} BRT</b><br>Total acumulado: %{y:.2f}%<extra></extra>",
        )
    )

    # Add milestone vertical markers
    if "17:00" in p_df["bin_time"].values:
        fig.add_shape(
            type="line",
            x0="17:00",
            x1="17:00",
            y0=0,
            y1=1,
            yref="paper",
            line={"dash": "dot", "color": "#d62728", "width": 2},
        )
        fig.add_annotation(
            x="17:00",
            y=1,
            yref="paper",
            text="17:00 (Padrão Regular)",
            showarrow=False,
            xanchor="left",
            font={"color": "#d62728", "size": 11},
        )
    if "19:00" in p_df["bin_time"].values:
        fig.add_shape(
            type="line",
            x0="19:00",
            x1="19:00",
            y0=0,
            y1=1,
            yref="paper",
            line={"dash": "dash", "color": "#2ca02c", "width": 2},
        )
        fig.add_annotation(
            x="19:00",
            y=1,
            yref="paper",
            text="19:00 (Fim da Prorrogação de 2h)",
            showarrow=False,
            xanchor="right",
            font={"color": "#2ca02c", "size": 11},
        )

    fig.update_layout(
        title=title,
        template="plotly_white",
        xaxis={
            "title": "Horário de Fechamento (Fuso Normalizado — Brasília/BRT)",
            "tickangle": -45,
        },
        yaxis={"title": "Quantidade de Urnas Encerradas", "showgrid": True},
        yaxis2={
            "title": "% Acumulado",
            "overlaying": "y",
            "side": "right",
            "range": [0, 105],
            "showgrid": False,
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"l": 40, "r": 40, "t": 70, "b": 50},
        hovermode="x unified",
    )
    return fig


def create_closing_regime_donut(
    overview: dict[str, Any], title: str = "Distribuição dos Regimes de Encerramento"
) -> go.Figure:
    """Donut chart partitioning sections into standard 17h close vs exceptional extension windows."""
    labels = [
        "Horário Regular (17:00 - 17:09)",
        "Prorrogação Inicial (17:10 - 18:29)",
        "Prorrogação Integral (18:30 - 19:05)",
        "Filas com Senha (> 19:05)",
    ]

    regular = overview.get("regular_count", 0)
    full_ext = overview.get("full_extended_count", 0)
    late = overview.get("late_queues_count", 0)
    total_ext = overview.get("extended_count", 0)
    early_ext = max(0, total_ext - full_ext - late)

    values = [regular, early_ext, full_ext, late]
    colors = ["#2b5c8f", "#f59f00", "#2b8a3e", "#c92a2a"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker={"colors": colors},
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Urnas: %{value:,}<br>Fatia: %{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def create_state_extension_bar_chart(
    df: pl.DataFrame, title: str = "Percentual de Urnas com Horário Prorrogado por UF"
) -> go.Figure:
    """Horizontal bar chart ranking Brazilian states by proportion of extended polling sections."""
    p_df = df.to_pandas().sort_values(by="pct_extended", ascending=True)

    fig = px.bar(
        p_df,
        x="pct_extended",
        y="state_abbreviation",
        orientation="h",
        color="pct_extended",
        color_continuous_scale="Reds",
        title=title,
        labels={
            "pct_extended": "% Urnas Prorrogadas",
            "state_abbreviation": "UF",
            "total_sections": "Total de Seções",
        },
    )
    fig.update_traces(
        texttemplate="%{x:.2f}%",
        textposition="outside",
        hovertemplate="<b>UF: %{y}</b><br>% Prorrogadas: %{x:.2f}%<br>Urnas Prorrogadas: %{customdata[0]:,}<br>Total de Urnas: %{customdata[1]:,}<extra></extra>",
        customdata=p_df[["extended_sections", "total_sections"]].values,
    )
    fig.update_layout(
        template="plotly_white",
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending", "title": "Unidade Federativa"},
        xaxis={"title": "% de Seções com Fechamento após 17:10 BRT"},
        margin={"l": 30, "r": 50, "t": 60, "b": 30},
        height=750,
    )
    return fig


def create_candidate_by_closing_regime_chart(
    df: pl.DataFrame, title: str = "Votação dos Candidatos por Regime de Encerramento"
) -> go.Figure:
    """Grouped bar chart showing candidate valid vote shares across closing time regimes."""
    p_df = df.to_pandas()

    color_map = {
        "LULA": "#c92a2a",
        "FLAVIO BOLSONARO": "#1971c2",
    }

    fig = px.bar(
        p_df,
        x="closing_regime",
        y="vote_pct",
        color="candidate_name",
        barmode="group",
        text="vote_pct",
        title=title,
        color_discrete_map=color_map,
        labels={
            "closing_regime": "Regime de Encerramento da Seção",
            "vote_pct": "% Votos Válidos",
            "candidate_name": "Candidato",
            "vote_count": "Total de Votos",
        },
    )
    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate="<b>%{data.name}</b><br>Regime: %{x}<br>Percentual: %{y:.2f}%<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white",
        yaxis={"title": "% dos Votos Válidos no Regime", "range": [0, 75]},
        xaxis={"title": "Regime de Encerramento"},
        legend={
            "title": "Candidato",
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        margin={"l": 30, "r": 30, "t": 70, "b": 30},
    )
    return fig
