"""Orchestrator for AI-assisted electoral investigation with controlled tool execution."""

import json
from typing import Any

from election_research.ai.prompts import SYSTEM_PROMPT
from election_research.ai.provider import AIProvider, OpenAIProvider
from election_research.ai.tools import TOOL_DEFINITIONS, execute_tool_call
from election_research.core.exceptions import AIProviderError
from election_research.core.logging import get_logger

logger = get_logger(__name__)


class ElectionAIAssistant:
    """Conversational assistant grounded in official electoral data queries."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or OpenAIProvider()

    def process_query(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process user message, execute allowlisted analytical tools, and return grounded response."""
        history = list(conversation_history or [])

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tools_executed: list[dict[str, Any]] = []

        try:
            # 1. Ask model (with tool definitions)
            response = self.provider.chat_completion(messages, tools=TOOL_DEFINITIONS)

            # 2. Handle tool calls if requested by the model
            if response.get("tool_calls"):
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.get("content") or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": json.dumps(tc["function"]["arguments"]),
                                },
                            }
                            for tc in response["tool_calls"]
                        ],
                    }
                )

                for tc in response["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    fn_args = tc["function"]["arguments"]
                    logger.info("Executing AI tool: %s with args %s", fn_name, fn_args)

                    result = execute_tool_call(fn_name, fn_args)
                    tools_executed.append(
                        {
                            "tool_name": fn_name,
                            "arguments": fn_args,
                            "output": result,
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

                # 3. Final call to obtain grounded explanation
                final_resp = self.provider.chat_completion(messages)
                final_text = final_resp.get("content") or "Consulta executada com sucesso."

                return {
                    "content": final_text,
                    "tools_executed": tools_executed,
                }

            return {
                "content": response.get("content") or "",
                "tools_executed": [],
            }

        except AIProviderError as e:
            # Graceful local fallback when OpenAI key is absent or unreachable
            logger.info(
                "AI provider unavailable, falling back to deterministic keyword query: %s", e
            )
            fallback_res = self._deterministic_fallback(user_message)
            return fallback_res

    def _deterministic_fallback(self, query: str) -> dict[str, Any]:
        """Local deterministic analytical lookup when no external AI provider is configured."""
        q = query.lower()

        if any(w in q for w in ["abstenção", "abstencoes", "abstenções", "maior"]):
            data = execute_tool_call("get_top_abstention_municipalities", {"top_n": 5})
            text = "Aqui estão os municípios com maiores taxas de abstenção identificados via ferramenta oficial:"
            return {
                "content": f"{text}\n\n*(Executado via ferramenta analítica determinística DuckDB)*",
                "tools_executed": [
                    {"tool_name": "get_top_abstention_municipalities", "output": data}
                ],
            }

        if any(w in q for w in ["candidato", "ranking", "vencedor", "lula", "bolsonaro"]):
            data = execute_tool_call("get_candidate_rankings", {"office_code": 1})
            text = "Aqui está o ranking oficial de votação para Presidente:"
            return {
                "content": f"{text}\n\n*(Executado via ferramenta analítica determinística DuckDB)*",
                "tools_executed": [{"tool_name": "get_candidate_rankings", "output": data}],
            }

        # Default overview
        data = execute_tool_call("get_election_overview", {})
        return {
            "content": (
                "Visão geral dos resultados oficiais consolidados da Eleição 2026 (2º Turno):\n\n"
                f"- **Eleitorado Apto**: {data.get('total_eligible_voters', 0):,}\n"
                f"- **Comparecimento**: {data.get('turnout_rate_pct', 0):.2f}%\n"
                f"- **Abstenção**: {data.get('abstention_rate_pct', 0):.2f}%\n"
                f"- **Votos Válidos**: {data.get('valid_vote_rate_pct', 0):.2f}%\n\n"
                "*(Consulta analítica determinística DuckDB)*"
            ),
            "tools_executed": [{"tool_name": "get_election_overview", "output": data}],
        }
