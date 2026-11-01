"""Registry of authorized analytical tools exposed to Qwen3.5-4B."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from election_research.ai.schemas import ToolDefinition
from election_research.core.security import sanitize_uf


class BaseToolArgs(BaseModel):
    """Base tool arguments strictly rejecting extraneous fields."""

    model_config = ConfigDict(extra="forbid")


class NationalSummaryArgs(BaseToolArgs):
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)


class StateSummaryArgs(BaseToolArgs):
    state_code: str = Field(description="2-letter Brazilian state abbreviation (ex: 'SP', 'AC')")
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)

    @field_validator("state_code")
    @classmethod
    def check_state(cls, v: str) -> str:
        res = sanitize_uf(v)
        if not res:
            raise ValueError("state_code is required")
        return res


class MunicipalitySummaryArgs(BaseToolArgs):
    municipality_code: str = Field(description="TSE municipality code or municipality name")
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)


class CandidateResultsArgs(BaseToolArgs):
    candidate_id: str | None = Field(default=None, description="Candidate name or ballot number")
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)
    geographic_filter: str | None = Field(default=None, description="Optional UF state code")


class CompareGeographicResultsArgs(BaseToolArgs):
    geographic_level: Literal["state", "municipality"] = Field(default="state")
    geographic_identifiers: list[str] = Field(
        description="List of state codes or municipality names"
    )
    metric: str = Field(
        default="turnout_rate_pct",
        description="Metric to compare (turnout_rate_pct, abstention_rate_pct, etc.)",
    )
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)


class AbstentionAnalysisArgs(BaseToolArgs):
    geographic_level: Literal["national", "state", "municipality"] = Field(default="state")
    geographic_identifier: str | None = Field(
        default=None, description="Optional UF code or municipality name"
    )
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)


class DetectAnomaliesArgs(BaseToolArgs):
    geographic_level: Literal["municipality", "state"] = Field(default="municipality")
    geographic_identifier: str | None = Field(
        default=None, description="Filter to a specific state (e.g. 'AC') or None for all"
    )
    metric: str = Field(
        default="abstention_rate_pct", description="Target metric for outlier detection"
    )
    method: Literal["zscore", "iqr", "isolation_forest"] = Field(default="zscore")
    threshold: float = Field(default=3.0, ge=0.5, le=10.0)
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)


class PollingSectionDetailsArgs(BaseToolArgs):
    state_code: str = Field(description="2-letter Brazilian state abbreviation (e.g. 'AC')")
    polling_section_number: int = Field(ge=1, le=100000, description="Polling section number")
    municipality_code: str | None = Field(
        default=None, description="Optional TSE municipality code or name"
    )
    election_year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)

    @field_validator("state_code")
    @classmethod
    def check_state(cls, v: str) -> str:
        res = sanitize_uf(v)
        if not res:
            raise ValueError("state_code is required")
        return res


# Tool specifications with JSON Schema for model consumption
TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_national_summary",
        description="Retorna o resumo consolidado nacional da eleição (aptos, comparecimento, abstenção, válidos, brancos, nulos e completude).",
        parameters={
            "type": "object",
            "properties": {
                "election_year": {
                    "type": "integer",
                    "description": "Ano eleitoral (ex: 2026)",
                    "default": 2026,
                },
                "election_round": {
                    "type": "integer",
                    "description": "Turno eleitoral (1 ou 2)",
                    "default": 2,
                },
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_state_summary",
        description="Retorna os indicadores eleitorais oficiais consolidados de uma Unidade Federativa (UF).",
        parameters={
            "type": "object",
            "properties": {
                "state_code": {
                    "type": "string",
                    "description": "Sigla de 2 letras da UF (ex: 'SP', 'AC', 'RJ')",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": ["state_code"],
        },
    ),
    ToolDefinition(
        name="get_municipality_summary",
        description="Retorna as estatísticas eleitorais de um município brasileiro por código TSE ou nome.",
        parameters={
            "type": "object",
            "properties": {
                "municipality_code": {
                    "type": "string",
                    "description": "Código TSE do município ou nome do município (ex: 'RIO BRANCO')",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": ["municipality_code"],
        },
    ),
    ToolDefinition(
        name="get_candidate_results",
        description="Retorna a votação oficial e classificação dos candidatos para o cargo presidencial.",
        parameters={
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": "Nome do candidato ou número de urna (ex: 'LULA', 'BOLSONARO', '13', '22')",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
                "geographic_filter": {
                    "type": "string",
                    "description": "Sigla de UF para filtrar resultados estaduais",
                },
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="compare_geographic_results",
        description="Compara métricas eleitorais (comparecimento, abstenção, votos) entre múltiplos estados ou municípios.",
        parameters={
            "type": "object",
            "properties": {
                "geographic_level": {
                    "type": "string",
                    "enum": ["state", "municipality"],
                    "default": "state",
                },
                "geographic_identifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de siglas de estados ou nomes de municípios",
                },
                "metric": {
                    "type": "string",
                    "default": "turnout_rate_pct",
                    "description": "Métrica a comparar",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": ["geographic_identifiers"],
        },
    ),
    ToolDefinition(
        name="get_abstention_analysis",
        description="Retorna estatísticas detalhadas e ranking de abstenção eleitoral para um nível geográfico.",
        parameters={
            "type": "object",
            "properties": {
                "geographic_level": {
                    "type": "string",
                    "enum": ["national", "state", "municipality"],
                    "default": "state",
                },
                "geographic_identifier": {
                    "type": "string",
                    "description": "Sigla da UF ou nome do município",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="detect_statistical_anomalies",
        description="Executa algoritmos de detecção de anomalias estatísticas (Z-Score, IQR, Isolation Forest) sobre os indicadores eleitorais.",
        parameters={
            "type": "object",
            "properties": {
                "geographic_level": {
                    "type": "string",
                    "enum": ["municipality", "state"],
                    "default": "municipality",
                },
                "geographic_identifier": {
                    "type": "string",
                    "description": "Sigla da UF para isolar análise (ex: 'AC') ou vazio para todos",
                },
                "metric": {"type": "string", "default": "abstention_rate_pct"},
                "method": {
                    "type": "string",
                    "enum": ["zscore", "iqr", "isolation_forest"],
                    "default": "zscore",
                },
                "threshold": {
                    "type": "number",
                    "default": 3.0,
                    "description": "Limiar estatístico para flag",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_polling_section_details",
        description="Retorna os dados cadastrais e apuração de uma seção eleitoral individual a partir dos Boletins de Urna (BUs).",
        parameters={
            "type": "object",
            "properties": {
                "state_code": {"type": "string", "description": "Sigla da UF (ex: 'AC')"},
                "polling_section_number": {
                    "type": "integer",
                    "description": "Número da seção eleitoral",
                },
                "municipality_code": {
                    "type": "string",
                    "description": "Código TSE ou nome do município",
                },
                "election_year": {"type": "integer", "default": 2026},
                "election_round": {"type": "integer", "default": 2},
            },
            "required": ["state_code", "polling_section_number"],
        },
    ),
]


class ToolRegistry:
    """Central catalog of analytical tools allowed for Qwen3.5-4B execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {t.name: t for t in TOOL_DEFINITIONS}
        self._arg_models: dict[str, type[BaseModel]] = {
            "get_national_summary": NationalSummaryArgs,
            "get_state_summary": StateSummaryArgs,
            "get_municipality_summary": MunicipalitySummaryArgs,
            "get_candidate_results": CandidateResultsArgs,
            "compare_geographic_results": CompareGeographicResultsArgs,
            "get_abstention_analysis": AbstentionAnalysisArgs,
            "detect_statistical_anomalies": DetectAnomaliesArgs,
            "get_polling_section_details": PollingSectionDetailsArgs,
        }

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Lookup tool definition by name."""
        return self._tools.get(name)

    def get_argument_model(self, name: str) -> type[BaseModel] | None:
        """Lookup Pydantic argument validator for tool."""
        return self._arg_models.get(name)

    def is_tool_allowed(self, name: str) -> bool:
        """Check whether requested tool is in the strict allowlist."""
        return name in self._tools
