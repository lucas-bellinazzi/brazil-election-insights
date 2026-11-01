"""Allowlisted analytical tools exposed to the AI Assistant."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from election_research.core.config import get_settings
from election_research.core.security import sanitize_uf
from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_candidate_rankings,
    query_electoral_overview,
    query_municipality_results,
    query_state_results,
    query_top_abstention_municipalities,
)


class BaseToolArgs(BaseModel):
    """Strict configuration rejecting unauthorized argument injection."""

    model_config = ConfigDict(extra="forbid")


class StandardElectionArgs(BaseToolArgs):
    year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)
    office_code: int = Field(default=1, ge=1, le=13)


class TopAbstentionToolArgs(StandardElectionArgs):
    min_voters: int = Field(default=5000, ge=0, le=100_000_000)
    top_n: int = Field(default=10, ge=1, le=100)


class MunicipalityToolArgs(StandardElectionArgs):
    municipality_name: str = Field(default="", max_length=150)
    uf: str | None = Field(default=None, max_length=2)

    @field_validator("uf")
    @classmethod
    def check_uf(cls, v: str | None) -> str | None:
        return sanitize_uf(v) if v else None


# Tool JSON schemas for OpenAI function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_election_overview",
            "description": "Obtém os indicadores eleitorais consolidados em nível nacional (aptos, comparecimento, abstenção, válidos, brancos e nulos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Ano da eleição (ex: 2026)",
                        "default": 2026,
                    },
                    "election_round": {
                        "type": "integer",
                        "description": "Turno da eleição (1 ou 2)",
                        "default": 2,
                    },
                    "office_code": {
                        "type": "integer",
                        "description": "Código do cargo (1=Presidente, 3=Governador)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_candidate_rankings",
            "description": "Obtém a lista ordenada de candidatos por votação e percentual de votos válidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Ano da eleição", "default": 2026},
                    "election_round": {
                        "type": "integer",
                        "description": "Turno da eleição (1 ou 2)",
                        "default": 2,
                    },
                    "office_code": {
                        "type": "integer",
                        "description": "Código do cargo (1=Presidente)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_state_results",
            "description": "Obtém os resultados e taxas de comparecimento e abstenção por Unidade Federativa (UF).",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "default": 2026},
                    "election_round": {"type": "integer", "default": 2},
                    "office_code": {"type": "integer", "default": 1},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_abstention_municipalities",
            "description": "Retorna os municípios com as maiores taxas de abstenção eleitoral.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "default": 2026},
                    "election_round": {"type": "integer", "default": 2},
                    "min_voters": {
                        "type": "integer",
                        "description": "Eleitorado mínimo apto",
                        "default": 5000,
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Quantidade de municípios",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_municipality_result",
            "description": "Consulta o resultado eleitoral de um município específico por nome ou UF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipality_name": {
                        "type": "string",
                        "description": "Nome do município (ex: RIO BRANCO, CAMPINAS)",
                    },
                    "uf": {"type": "string", "description": "Sigla da UF (ex: AC, SP)"},
                    "year": {"type": "integer", "default": 2026},
                    "election_round": {"type": "integer", "default": 2},
                },
                "required": ["municipality_name"],
            },
        },
    },
]


def execute_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a strictly validated analytical tool call against DuckDB and return structured data."""
    settings = get_settings()
    conn = get_connection(db_path=settings.duckdb_path, read_only=False, register_views=True)

    try:
        if tool_name == "get_election_overview":
            args = StandardElectionArgs.model_validate(arguments)
            return query_electoral_overview(
                conn,
                year=args.year,
                election_round=args.election_round,
                office_code=args.office_code,
            )

        if tool_name == "get_candidate_rankings":
            args = StandardElectionArgs.model_validate(arguments)
            df = query_candidate_rankings(
                conn,
                year=args.year,
                election_round=args.election_round,
                office_code=args.office_code,
            )
            return {"candidates": df.to_dicts()}

        if tool_name == "get_state_results":
            args = StandardElectionArgs.model_validate(arguments)
            df = query_state_results(
                conn,
                year=args.year,
                election_round=args.election_round,
                office_code=args.office_code,
            )
            return {"states": df.to_dicts()}

        if tool_name == "get_top_abstention_municipalities":
            args = TopAbstentionToolArgs.model_validate(arguments)
            df = query_top_abstention_municipalities(
                conn,
                year=args.year,
                election_round=args.election_round,
                office_code=args.office_code,
                min_voters=args.min_voters,
                top_n=args.top_n,
            )
            return {"top_abstentions": df.to_dicts()}

        if tool_name == "get_municipality_result":
            args = MunicipalityToolArgs.model_validate(arguments)
            df = query_municipality_results(
                conn,
                year=args.year,
                election_round=args.election_round,
                office_code=args.office_code,
                uf=args.uf,
                name_filter=args.municipality_name,
                limit=5,
            )
            return {"municipalities": df.to_dicts()}

        return {"error": f"Tool '{tool_name}' is not recognized or permitted."}

    except ValidationError as e:
        return {"error": f"Invalid tool arguments provided: {e.errors()}"}
    except Exception as e:
        return {"error": f"Execution error in tool '{tool_name}': {str(e)}"}
