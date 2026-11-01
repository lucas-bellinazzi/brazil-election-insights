"""Orchestration service for the AI Assistant with Qwen3.5-4B and controlled tool execution."""

import time
from typing import Any

from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.context_manager import ContextManager
from election_research.ai.conversation import Conversation
from election_research.ai.exceptions import AIError
from election_research.ai.provider import AIProvider
from election_research.ai.provider_factory import create_ai_provider
from election_research.ai.schemas import ChatMessage, ToolCall, ToolResult
from election_research.ai.tool_executor import ToolExecutor
from election_research.ai.tool_registry import ToolRegistry
from election_research.core.logging import get_logger

logger = get_logger(__name__)


class ElectionAIAssistant:
    """Conversational analytical assistant grounded in official TSE electoral data via DuckDB."""

    def __init__(
        self,
        provider: AIProvider | None = None,
        registry: ToolRegistry | None = None,
        executor: ToolExecutor | None = None,
        context_manager: ContextManager | None = None,
        settings: AISettings | None = None,
    ) -> None:
        self.settings = settings or get_ai_settings()
        self.provider = provider or (
            create_ai_provider(self.settings) if self.settings.ai_enabled else None
        )
        self.registry = registry or ToolRegistry()
        self.executor = executor or ToolExecutor(registry=self.registry)
        self.context_manager = context_manager or ContextManager(settings=self.settings)

    def process_query(
        self,
        user_message: str,
        conversation: Conversation | None = None,
    ) -> dict[str, Any]:
        """Execute the multi-turn interaction loop with Qwen3.5-4B and deterministic tools."""
        start_turn = time.perf_counter()
        conv = conversation or Conversation()

        tools_executed_log: list[dict[str, Any]] = []

        # If AI is globally disabled or provider is not configured, fall back immediately to deterministic engine
        if not self.settings.ai_enabled or self.provider is None:
            logger.info("AI subsystem disabled; executing deterministic analytical fallback.")
            fallback = self._deterministic_fallback(user_message)
            conv.add_user_message(user_message)
            conv.add_assistant_message(fallback["content"])
            fallback["duration_seconds"] = time.perf_counter() - start_turn
            return fallback

        # 1. Build initial prompt messages
        messages = self.context_manager.build_prompt_messages(
            history=conv.get_messages(),
            current_user_message=user_message,
        )
        conv.add_user_message(user_message)

        tool_defs = self.registry.list_tools()
        executed_signatures: set[str] = set()

        max_iterations = self.settings.ai_max_tool_iterations
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            for iteration in range(max_iterations):
                logger.debug(
                    "AI loop iteration %d/%d for query '%s'",
                    iteration + 1,
                    max_iterations,
                    user_message[:40],
                )

                # Send request to Hugging Face provider
                response = self.provider.generate_response(messages=messages, tools=tool_defs)

                if response.token_usage:
                    total_tokens["prompt_tokens"] += response.token_usage.get("prompt_tokens", 0)
                    total_tokens["completion_tokens"] += response.token_usage.get(
                        "completion_tokens", 0
                    )
                    total_tokens["total_tokens"] += response.token_usage.get("total_tokens", 0)

                # Case A: Model responded with no tool calls -> Completed answer
                if not response.tool_calls:
                    final_text = (
                        response.content
                        if response.content
                        else "Não foi possível obter uma resposta para a consulta."
                    )
                    conv.add_assistant_message(final_text)

                    turn_duration = time.perf_counter() - start_turn
                    return {
                        "content": final_text,
                        "tools_executed": tools_executed_log,
                        "duration_seconds": turn_duration,
                        "provider": self.provider.provider_id,
                        "model": self.provider.model_id,
                        "token_usage": total_tokens,
                        "iterations": iteration + 1,
                    }

                # Case B: Model requested one or more tool calls
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=response.content,
                        tool_calls=response.tool_calls,
                    )
                )

                for call in response.tool_calls:
                    signature = f"{call.name}:{sorted(call.arguments.items())}"

                    # Prevent repeated identical calls in the same turn
                    if signature in executed_signatures:
                        logger.warning("Prevented duplicate tool call: %s", call.name)
                        tool_res = ToolResult(
                            tool_name=call.name,
                            arguments=call.arguments,
                            success=False,
                            error="Chamada de ferramenta duplicada ignorada.",
                        )
                    else:
                        executed_signatures.add(signature)
                        logger.info("Executing analytical tool: %s", call.name)
                        tool_res = self.executor.execute(call)

                    tools_executed_log.append(
                        {
                            "tool_name": tool_res.tool_name,
                            "arguments": tool_res.arguments,
                            "success": tool_res.success,
                            "output": tool_res.data,
                            "provenance": tool_res.provenance,
                            "error": tool_res.error,
                            "duration_seconds": tool_res.duration_seconds,
                        }
                    )

                    formatted_result = self.context_manager.format_tool_result_content(tool_res)
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=formatted_result,
                            tool_call_id=call.id,
                            name=call.name,
                        )
                    )

            # If iteration limit reached without terminal answer, request final summary
            logger.warning(
                "Reached maximum tool iterations (%d). Forcing final answer.", max_iterations
            )
            final_resp = self.provider.generate_response(messages=messages, tools=None)
            final_text = (
                final_resp.content
                if final_resp.content
                else "Concluído o limite de operações analíticas para esta consulta."
            )
            conv.add_assistant_message(final_text)

            turn_duration = time.perf_counter() - start_turn
            return {
                "content": final_text,
                "tools_executed": tools_executed_log,
                "duration_seconds": turn_duration,
                "provider": self.provider.provider_id,
                "model": self.provider.model_id,
                "token_usage": total_tokens,
                "iterations": max_iterations,
            }

        except AIError as e:
            logger.warning(
                "Hugging Face provider error (%s). Falling back to deterministic mode: %s",
                type(e).__name__,
                e,
            )
            fallback = self._deterministic_fallback(user_message)
            conv.add_assistant_message(fallback["content"])
            fallback["duration_seconds"] = time.perf_counter() - start_turn
            fallback["warning"] = f"Aviso do Provedor AI: {str(e)}"
            return fallback

        except Exception as e:
            logger.error("Unexpected error in AI Assistant: %s", e, exc_info=True)
            fallback = self._deterministic_fallback(user_message)
            conv.add_assistant_message(fallback["content"])
            fallback["duration_seconds"] = time.perf_counter() - start_turn
            fallback["warning"] = f"Erro na inferência: {str(e)}"
            return fallback

    def _deterministic_fallback(self, query: str) -> dict[str, Any]:
        """Deterministic keyword-based query execution ensuring 100% functionality without LLM."""
        q = query.lower()

        if any(w in q for w in ["abstenção", "abstencoes", "abstenções", "maior"]):
            call = ToolCall(
                id="fallback_call",
                name="get_abstention_analysis",
                arguments={"geographic_level": "municipality"},
            )
            res = self.executor.execute(call)
            text = (
                "**Municípios com maiores taxas de abstenção identificados via ferramenta oficial:**\n\n"
                "*(Consulta analítica determinística DuckDB — Modo de contingência sem IA)*"
            )
            return {
                "content": text,
                "tools_executed": [
                    {
                        "tool_name": "get_abstention_analysis",
                        "arguments": res.arguments,
                        "output": res.data,
                        "provenance": res.provenance,
                        "success": res.success,
                    }
                ],
                "provider": "deterministic_fallback",
                "model": "DuckDB-SQL",
            }

        if any(w in q for w in ["candidato", "ranking", "vencedor", "lula", "bolsonaro"]):
            call = ToolCall(
                id="fallback_call",
                name="get_candidate_results",
                arguments={"election_year": 2026, "election_round": 2},
            )
            res = self.executor.execute(call)
            text = (
                "**Ranking oficial consolidado para a Eleição Presidencial 2026 (2º Turno):**\n\n"
                "*(Consulta analítica determinística DuckDB — Modo de contingência sem IA)*"
            )
            return {
                "content": text,
                "tools_executed": [
                    {
                        "tool_name": "get_candidate_results",
                        "arguments": res.arguments,
                        "output": res.data,
                        "provenance": res.provenance,
                        "success": res.success,
                    }
                ],
                "provider": "deterministic_fallback",
                "model": "DuckDB-SQL",
            }

        # Default: National Overview
        call = ToolCall(
            id="fallback_call",
            name="get_national_summary",
            arguments={"election_year": 2026, "election_round": 2},
        )
        res = self.executor.execute(call)
        data = res.data or {}

        summary_text = (
            "**Visão Geral Nacional Consolidada da Eleição 2026 (2º Turno):**\n\n"
            f"- **Eleitorado Apto**: {data.get('total_eligible_voters', 0):,}\n"
            f"- **Comparecimento**: {data.get('turnout_rate_pct', 0):.2f}%\n"
            f"- **Abstenção**: {data.get('abstention_rate_pct', 0):.2f}%\n"
            f"- **Votos Válidos**: {data.get('valid_vote_rate_pct', 0):.2f}%\n"
            f"- **Votos Nulos**: {data.get('null_vote_rate_pct', 0):.2f}%\n"
            f"- **Votos em Branco**: {data.get('blank_vote_rate_pct', 0):.2f}%\n\n"
            "*(Consulta analítica determinística DuckDB — Modo de contingência sem IA)*"
        )
        return {
            "content": summary_text,
            "tools_executed": [
                {
                    "tool_name": "get_national_summary",
                    "arguments": res.arguments,
                    "output": res.data,
                    "provenance": res.provenance,
                    "success": res.success,
                }
            ],
            "provider": "deterministic_fallback",
            "model": "DuckDB-SQL",
        }
