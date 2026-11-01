"""Plotly visualization components for Brazilian election insights."""

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
