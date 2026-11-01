"""CLI tool to generate reproducible, automated analytical reports."""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from election_research.analytics.anomalies import detect_anomalies_iqr, detect_anomalies_zscore
from election_research.core.config import get_settings
from election_research.core.logging import get_logger, setup_logging
from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_candidate_rankings,
    query_electoral_overview,
    query_municipality_results,
    query_state_results,
)

logger = get_logger("generate_report")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate comprehensive, reproducible analytical reports in Markdown and JSON."
    )
    parser.add_argument("--year", type=int, default=2026, help="Election year (default: 2026)")
    parser.add_argument("--round", choices=["1t", "2t"], default="2t", help="Election round")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Target reports directory (default: reports/analysis)",
    )
    return parser.parse_args()


def generate_analytical_report(
    year: int = 2026, election_round: str = "2t", output_dir: Path | None = None
) -> Path:
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / "reports" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    rnd_int = 2 if "2" in election_round else 1
    conn = get_connection(db_path=settings.duckdb_path, read_only=False, register_views=True)

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"election_report_{year}_{election_round}_{timestamp_str}.md"

    logger.info("Generating analytical report for Year %d, Round %s...", year, election_round)

    overview = query_electoral_overview(conn, year=year, election_round=rnd_int, office_code=1)
    cand_df = query_candidate_rankings(conn, year=year, election_round=rnd_int, office_code=1)
    query_state_results(conn, year=year, election_round=rnd_int, office_code=1)
    munis_df = query_municipality_results(
        conn, year=year, election_round=rnd_int, office_code=1, limit=10000
    )

    # Stratified Anomaly signals: Domestic (BR without ZZ) vs. Abroad (ZZ)
    domestic_munis = munis_df.filter(pl.col("state_abbreviation") != "ZZ")
    abroad_munis = munis_df.filter(pl.col("state_abbreviation") == "ZZ")

    # Domestic anomalies
    z_anom_dom = detect_anomalies_zscore(
        domestic_munis, metric_col="abstention_rate_pct", threshold=3.0
    )
    iqr_anom_dom = detect_anomalies_iqr(
        domestic_munis, metric_col="abstention_rate_pct", factor=1.5
    )

    # Abroad ranking
    z_anom_abroad = abroad_munis.sort("abstention_rate_pct", descending=True)

    md_lines = [
        f"# Relatório Analítico Oficial — Eleições {year} ({election_round.upper()})",
        "",
        f"- **Data de Emissão**: {datetime.now(UTC).isoformat()}",
        "- **Fonte de Dados**: Tribunal Superior Eleitoral (TSE) — Boletins de Urna",
        "- **Engine Analítica**: DuckDB / Polars / Apache Parquet",
        "",
        "---",
        "",
        "## 1. Indicadores Consolidados Nacionais",
        "",
        f"- **Total de Seções Eleitorais**: {overview.get('total_sections', 0):,}",
        f"- **Eleitorado Apto Total**: {overview.get('total_eligible_voters', 0):,}",
        f"- **Comparecimento**: {overview.get('total_actual_turnout', 0):,} ({overview.get('turnout_rate_pct', 0.0):.2f}%)",
        f"- **Abstenções**: {overview.get('total_abstentions', 0):,} ({overview.get('abstention_rate_pct', 0.0):.2f}%)",
        f"- **Votos Válidos**: {overview.get('total_valid_votes', 0):,} ({overview.get('valid_vote_rate_pct', 0.0):.2f}%)",
        f"- **Votos em Branco**: {overview.get('total_blank_votes', 0):,} ({overview.get('blank_vote_rate_pct', 0.0):.2f}%)",
        f"- **Votos Nulos**: {overview.get('total_null_votes', 0):,} ({overview.get('null_vote_rate_pct', 0.0):.2f}%)",
        "",
        "---",
        "",
        "## 2. Votação Oficial por Candidato (Presidente)",
        "",
        "| Rank | Número | Candidato | Partido | Votos Totais | % Votos Válidos |",
        "| :---: | :---: | :--- | :---: | :---: | :---: |",
    ]

    for row in cand_df.to_dicts():
        md_lines.append(
            f"| {row['rank']} | {row['ballot_number']} | {row['candidate_name']} | "
            f"{row['party_abbreviation']} | {row['total_candidate_votes']:,} | {row['valid_vote_share_pct']:.2f}% |"
        )

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Investigação de Sinais Estatísticos de Anomalia — Território Nacional (Brasil)",
            "",
            "> [!NOTE]",
            "> Sinais estatísticos indicam observações atípicas para investigação metodológica e empírica.",
            "> **Nunca constituem prova ou indício de manipulação ou fraude eleitoral.**",
            "> Para evitar distorções de escala demográfica e logística, a análise abaixo isola os municípios do território nacional brasileiro (excluindo postos no exterior ZZ).",
            "",
            f"### A. Desvios Paramétricos Nacionais (Z-Score >= 3.0): {len(z_anom_dom)} municípios sinalizados",
            "",
            "| UF | Município | Eleitores | Abstenção (%) | Z-Score |",
            "| :---: | :--- | :---: | :---: | :---: |",
        ]
    )

    for row in z_anom_dom.head(10).to_dicts():
        md_lines.append(
            f"| {row['state_abbreviation']} | {row['municipality_name']} | "
            f"{row['total_eligible_voters']:,} | {row['abstention_rate_pct']:.2f}% | {row['anomaly_score']:.2f} |"
        )

    md_lines.extend(
        [
            "",
            f"### B. Desvios Não-Paramétricos Nacionais (IQR 1.5x): {len(iqr_anom_dom)} municípios sinalizados",
            "",
            "| UF | Município | Eleitores | Abstenção (%) | Limite Superior |",
            "| :---: | :--- | :---: | :---: | :---: |",
        ]
    )

    for row in iqr_anom_dom.head(10).to_dicts():
        md_lines.append(
            f"| {row['state_abbreviation']} | {row['municipality_name']} | "
            f"{row['total_eligible_voters']:,} | {row['abstention_rate_pct']:.2f}% | {row['upper_bound']:.2f}% |"
        )

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Comportamento Eleitoral no Exterior (UF ZZ — Embaixadas e Consulados)",
            "",
            "Postos no exterior operam sob dinâmica logística e demográfica distinta (grandes distâncias físicas até consulados, custos de viagem, ausência de voto obrigatório efetivo com multa simbólica).",
            "",
            "| Posto no Exterior | Eleitores Aptos | Comparecimento | Abstenção (%) |",
            "| :--- | :---: | :---: | :---: |",
        ]
    )

    for row in z_anom_abroad.head(10).to_dicts():
        md_lines.append(
            f"| {row['municipality_name']} | {row['total_eligible_voters']:,} | "
            f"{row['total_actual_turnout']:,} | {row['abstention_rate_pct']:.2f}% |"
        )

    md_lines.append("")
    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Report written to %s", report_file)
    print(f"\nAnalytical report generated: {report_file.name}")
    return report_file


def main() -> int:
    setup_logging()
    args = parse_args()
    generate_analytical_report(
        year=args.year, election_round=args.round, output_dir=args.output_dir
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
