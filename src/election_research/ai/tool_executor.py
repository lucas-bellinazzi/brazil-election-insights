"""Controlled tool executor running validated analytical operations against DuckDB."""

import time
from typing import Any

import duckdb
import polars as pl
from pydantic import ValidationError

from election_research.ai.exceptions import InvalidToolCallError
from election_research.ai.schemas import ToolCall, ToolResult
from election_research.ai.tool_registry import (
    AbstentionAnalysisArgs,
    CandidateResultsArgs,
    ClosingTimesAnalysisArgs,
    CompareGeographicResultsArgs,
    DetectAnomaliesArgs,
    MunicipalitySummaryArgs,
    NationalSummaryArgs,
    PollingSectionDetailsArgs,
    StateSummaryArgs,
    ToolRegistry,
)
from election_research.analytics.anomalies import (
    NEUTRAL_DISCLAIMER,
    detect_anomalies_iqr,
    detect_anomalies_isolation_forest,
    detect_anomalies_zscore,
)
from election_research.core.config import get_settings
from election_research.core.exceptions import SecurityError
from election_research.core.logging import get_logger
from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_candidate_rankings,
    query_closing_time_candidates,
    query_closing_time_overview,
    query_electoral_overview,
    query_municipality_results,
    query_polling_section_detail,
    query_single_municipality,
    query_single_state,
    query_state_results,
    query_top_abstention_municipalities,
)

logger = get_logger(__name__)


class ToolExecutor:
    """Safe analytical executor enforcing strict schemas, query bounds, and provenance tracking."""

    def __init__(
        self, registry: ToolRegistry | None = None, conn: duckdb.DuckDBPyConnection | None = None
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.settings = get_settings()
        self._conn = conn

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = get_connection(
                db_path=self.settings.duckdb_path, read_only=True, register_views=True
            )
        return self._conn

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call with Pydantic validation and error handling."""
        start_time = time.perf_counter()
        name = tool_call.name
        args = tool_call.arguments

        if not self.registry.is_tool_allowed(name):
            duration = time.perf_counter() - start_time
            return ToolResult(
                tool_name=name,
                arguments=args,
                success=False,
                error=f"Tool '{name}' is not recognized or permitted / Ferramenta não permitida.",
                duration_seconds=duration,
            )

        model_cls = self.registry.get_argument_model(name)
        if model_cls is None:
            duration = time.perf_counter() - start_time
            return ToolResult(
                tool_name=name,
                arguments=args,
                success=False,
                error=f"Modelo de validação ausente para '{name}'.",
                duration_seconds=duration,
            )

        try:
            validated_args = model_cls.model_validate(args)
        except (ValidationError, SecurityError, ValueError) as e:
            duration = time.perf_counter() - start_time
            err_msg = e.errors() if isinstance(e, ValidationError) else str(e)
            return ToolResult(
                tool_name=name,
                arguments=args,
                success=False,
                error=f"Invalid tool arguments provided / Argumentos inválidos para '{name}': {err_msg}",
                duration_seconds=duration,
            )

        conn = self._get_connection()

        try:
            if name == "get_national_summary":
                data, prov, count = self._exec_national_summary(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_state_summary":
                data, prov, count = self._exec_state_summary(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_municipality_summary":
                data, prov, count = self._exec_municipality_summary(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_candidate_results":
                data, prov, count = self._exec_candidate_results(conn, validated_args)  # type: ignore[arg-type]
            elif name == "compare_geographic_results":
                data, prov, count = self._exec_compare_geographic_results(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_abstention_analysis":
                data, prov, count = self._exec_abstention_analysis(conn, validated_args)  # type: ignore[arg-type]
            elif name == "detect_statistical_anomalies":
                data, prov, count = self._exec_detect_anomalies(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_polling_section_details":
                data, prov, count = self._exec_polling_section_details(conn, validated_args)  # type: ignore[arg-type]
            elif name == "get_closing_times_analysis":
                data, prov, count = self._exec_closing_times_analysis(conn, validated_args)  # type: ignore[arg-type]
            else:
                raise InvalidToolCallError(f"Tool handler not implemented for '{name}'")

            duration = time.perf_counter() - start_time
            return ToolResult(
                tool_name=name,
                arguments=validated_args.model_dump(),
                success=True,
                data=data,
                provenance=prov,
                record_count=count,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error("Tool execution failed for %s: %s", name, e)
            return ToolResult(
                tool_name=name,
                arguments=args,
                success=False,
                error=f"Falha na execução analítica de '{name}': {str(e)}",
                duration_seconds=duration,
            )

    def _exec_national_summary(
        self, conn: duckdb.DuckDBPyConnection, args: NationalSummaryArgs
    ) -> tuple[Any, dict, int]:
        overview = query_electoral_overview(
            conn, year=args.election_year, election_round=args.election_round
        )
        # Add completeness indicator
        try:
            st_count = conn.sql(
                "SELECT count(distinct state_abbreviation) FROM gold_state_summary WHERE election_year = ? AND election_round = ?",
                params=[args.election_year, args.election_round],
            ).fetchone()[0]  # type: ignore[index]
            mun_count = conn.sql(
                "SELECT count(distinct municipality_name) FROM gold_municipality_summary WHERE election_year = ? AND election_round = ?",
                params=[args.election_year, args.election_round],
            ).fetchone()[0]  # type: ignore[index]
            overview["states_represented"] = st_count
            overview["municipalities_represented"] = mun_count
            overview["dataset_completeness"] = "100% dos BUs processados da camada Gold"
        except Exception:
            pass

        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_national_summary",
            "year": args.election_year,
            "round": args.election_round,
            "aggregation": "Nacional consolidada",
        }
        return overview, prov, 1

    def _exec_state_summary(
        self, conn: duckdb.DuckDBPyConnection, args: StateSummaryArgs
    ) -> tuple[Any, dict, int]:
        data = query_single_state(
            conn,
            state_code=args.state_code,
            year=args.election_year,
            election_round=args.election_round,
        )
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_state_summary",
            "state": args.state_code,
            "year": args.election_year,
            "round": args.election_round,
        }
        return data, prov, 1 if data else 0

    def _exec_municipality_summary(
        self, conn: duckdb.DuckDBPyConnection, args: MunicipalitySummaryArgs
    ) -> tuple[Any, dict, int]:
        data = query_single_municipality(
            conn,
            municipality_code_or_name=args.municipality_code,
            year=args.election_year,
            election_round=args.election_round,
        )
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_municipality_summary",
            "municipality_query": args.municipality_code,
            "year": args.election_year,
            "round": args.election_round,
        }
        return data, prov, 1 if data else 0

    def _exec_candidate_results(
        self, conn: duckdb.DuckDBPyConnection, args: CandidateResultsArgs
    ) -> tuple[Any, dict, int]:
        df = query_candidate_rankings(
            conn, year=args.election_year, election_round=args.election_round
        )
        if args.candidate_id:
            cid = args.candidate_id.strip().upper()
            df = df.filter(
                (pl.col("candidate_name").str.contains(cid))
                | (pl.col("ballot_number").cast(pl.Utf8) == cid)
            )
        records = df.to_dicts()
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_candidate_summary",
            "year": args.election_year,
            "round": args.election_round,
        }
        return records, prov, len(records)

    def _exec_compare_geographic_results(
        self, conn: duckdb.DuckDBPyConnection, args: CompareGeographicResultsArgs
    ) -> tuple[Any, dict, int]:
        idents = [i.strip().upper() for i in args.geographic_identifiers if i.strip()]
        if args.geographic_level == "state":
            df = query_state_results(
                conn, year=args.election_year, election_round=args.election_round
            )
            if idents:
                df = df.filter(pl.col("state_abbreviation").is_in(idents))
            records = df.to_dicts()
        else:
            df = query_municipality_results(
                conn, year=args.election_year, election_round=args.election_round, limit=50
            )
            if idents:
                df = df.filter(pl.col("municipality_name").is_in(idents))
            records = df.to_dicts()

        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": f"Gold - gold_{args.geographic_level}_summary",
            "comparison_metric": args.metric,
            "geographic_level": args.geographic_level,
        }
        return records[:50], prov, len(records)

    def _exec_abstention_analysis(
        self, conn: duckdb.DuckDBPyConnection, args: AbstentionAnalysisArgs
    ) -> tuple[Any, dict, int]:
        if args.geographic_level == "national":
            overview = query_electoral_overview(
                conn, year=args.election_year, election_round=args.election_round
            )
            res = {
                "scope": "Brasil (Nacional)",
                "total_eligible_voters": overview.get("total_eligible_voters", 0),
                "total_abstentions": overview.get("total_abstentions", 0),
                "abstention_rate_pct": overview.get("abstention_rate_pct", 0.0),
                "turnout_rate_pct": overview.get("turnout_rate_pct", 0.0),
            }
            return res, {"source": "Gold - gold_national_summary"}, 1

        if args.geographic_level == "state" and args.geographic_identifier:
            st = query_single_state(
                conn,
                state_code=args.geographic_identifier,
                year=args.election_year,
                election_round=args.election_round,
            )
            return (
                st,
                {"source": "Gold - gold_state_summary", "state": args.geographic_identifier},
                1 if st else 0,
            )

        # Default: Top abstention municipalities
        df = query_top_abstention_municipalities(
            conn, year=args.election_year, election_round=args.election_round, top_n=15
        )
        records = df.to_dicts()
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_municipality_summary",
            "method": "Ranking de taxa de abstenção (eleitorado >= 5.000)",
        }
        return records, prov, len(records)

    def _exec_detect_anomalies(
        self, conn: duckdb.DuckDBPyConnection, args: DetectAnomaliesArgs
    ) -> tuple[Any, dict, int]:
        # Query base dataset
        sql = """
        SELECT
            state_abbreviation,
            municipality_name,
            total_eligible_voters,
            total_actual_turnout,
            total_abstentions,
            turnout_rate_pct,
            abstention_rate_pct,
            valid_vote_rate_pct
        FROM gold_municipality_summary
        WHERE election_year = ? AND election_round = ?
        """
        params: list[Any] = [args.election_year, args.election_round]
        if args.geographic_identifier:
            sql += " AND state_abbreviation = ?"
            params.append(args.geographic_identifier.upper())

        df = conn.sql(sql, params=params).pl()

        target_metric = args.metric if args.metric in df.columns else "abstention_rate_pct"

        if args.method == "iqr":
            flagged = detect_anomalies_iqr(df, metric_col=target_metric, factor=args.threshold)
        elif args.method == "isolation_forest":
            flagged = detect_anomalies_isolation_forest(df, feature_cols=[target_metric])
        else:
            flagged = detect_anomalies_zscore(
                df, metric_col=target_metric, threshold=args.threshold
            )

        records = flagged.head(25).to_dicts()
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Gold - gold_municipality_summary",
            "method": f"Detecção de atipicidades ({args.method})",
            "metric": target_metric,
            "threshold": args.threshold,
            "disclaimer": NEUTRAL_DISCLAIMER,
        }
        return records, prov, len(records)

    def _exec_polling_section_details(
        self, conn: duckdb.DuckDBPyConnection, args: PollingSectionDetailsArgs
    ) -> tuple[Any, dict, int]:
        data = query_polling_section_detail(
            conn,
            state_code=args.state_code,
            section_number=args.polling_section_number,
            municipality_code=args.municipality_code,
            year=args.election_year,
            election_round=args.election_round,
        )
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Silver - silver_polling_sections",
            "uf": args.state_code,
            "section": args.polling_section_number,
        }
        return data, prov, 1 if data else 0

    def _exec_closing_times_analysis(
        self, conn: duckdb.DuckDBPyConnection, args: ClosingTimesAnalysisArgs
    ) -> tuple[Any, dict, int]:
        overview = query_closing_time_overview(
            conn,
            year=args.election_year,
            election_round=args.election_round,
            uf=args.state_code,
        )
        candidates_df = query_closing_time_candidates(
            conn,
            year=args.election_year,
            election_round=args.election_round,
            office_code=1,
            uf=args.state_code,
        )
        data = {
            "overview": overview,
            "candidates_by_closing_regime": candidates_df.to_dicts()
            if not candidates_df.is_empty()
            else [],
        }
        prov = {
            "source": "TSE - Boletins de Urna (BUs)",
            "layer": "Silver - silver_polling_sections & silver_votes",
            "scope": args.state_code or "Nacional (Brasil)",
            "method": "Normalização para Horário de Brasília (BRT) e estratificação por regimes",
        }
        return data, prov, 1 if overview else 0
