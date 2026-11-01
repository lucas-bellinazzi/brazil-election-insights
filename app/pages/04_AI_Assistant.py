"""AI Assistant page — Conversational electoral research powered by Hugging Face and Qwen3.5-4B."""

import streamlit as st
from app.utils.session_state import init_session_state

from election_research.ai.assistant import ElectionAIAssistant
from election_research.ai.config import get_ai_settings
from election_research.ai.conversation import Conversation
from election_research.ai.provider_factory import get_cached_ai_provider

st.set_page_config(page_title="Assistente de IA — Brazil Election Insights", layout="wide")
init_session_state()

settings = get_ai_settings()

st.title("🤖 Assistente de Investigação Eleitoral")
st.caption(f"Alimentado pelo ecossistema Hugging Face • Modelo padrão: **{settings.ai_model_id}**")

st.markdown(
    """
    Explore e investigue resultados eleitorais com auxílio de IA. O assistente é **estritamente ancorado**
    em ferramentas analíticas auditadas sobre o banco DuckDB, garantindo que toda informação numérica
    seja comprovada por dados oficiais do TSE.
    """
)

# Sidebar with Model status and Health Check
with st.sidebar:
    st.subheader("⚙️ Configuração da IA")
    st.write(f"**Modelo**: `{settings.ai_model_id}`")
    st.write(f"**Provedor**: `{settings.ai_provider}`")
    st.write(f"**Status da IA**: {'🟢 Ativo' if settings.ai_enabled else '🔴 Desativado'}")

    if st.button("🔍 Testar Conectividade com Modelo"):
        with st.spinner("Testando provedor de inferência..."):
            try:
                provider = get_cached_ai_provider()
                health = provider.health_check()
                if health.is_available:
                    st.success(f"{health.status_message}")
                else:
                    st.warning(f"{health.status_message}")
            except Exception as e:
                st.error(f"Erro no teste: {e}")

    if st.button("🗑️ Limpar Conversa"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        "🔗 **Dica**: Inspecione os dados brutos ou desagregados diretamente na página **02 Data Explorer**."
    )

# Guidelines expander
with st.expander("ℹ️ Diretrizes de Rigor e Auditoria do Assistente"):
    st.markdown(
        """
        - **Sem SQL arbitrário**: O assistente invoca apenas ferramentas pré-validadas do registro oficial.
        - **Sem conclusões infundadas de fraude**: Discrepâncias estatísticas e atipicidades são descritas exclusivamente como hipóteses metodológicas para investigação empírica.
        - **Dados Oficiais**: Todo valor numérico é calculado determinística e diretamente sobre a camada Gold/Silver do TSE.
        """
    )

# Display existing conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools_executed"):
            with st.expander("🛠️ Análise realizada"):
                for tool in msg["tools_executed"]:
                    st.markdown(f"**Ferramenta**: `{tool.get('tool_name')}`")
                    prov = tool.get("provenance", {})
                    st.markdown(
                        f"- **Fonte/Camada**: {prov.get('source', 'TSE')} ({prov.get('layer', 'Gold')})\n"
                        f"- **Escopo**: {prov.get('aggregation', prov.get('geographic_level', 'Oficial'))}\n"
                        f"- **Método**: {prov.get('method', 'Consulta estruturada DuckDB')}"
                    )
                    if tool.get("output"):
                        st.json(tool["output"])

# Chat input
if prompt := st.chat_input("Ex: Quais municípios tiveram as maiores taxas de abstenção em 2026?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    assistant = ElectionAIAssistant()
    conv = Conversation()
    for m in st.session_state.messages[:-1]:
        if m["role"] == "user":
            conv.add_user_message(m["content"])
        elif m["role"] == "assistant":
            conv.add_assistant_message(m["content"])

    with st.chat_message("assistant"):
        with st.spinner("Processando pergunta e consultando dados oficiais via Qwen3.5-4B..."):
            response = assistant.process_query(
                user_message=prompt,
                conversation=conv,
            )
            st.markdown(response["content"])

            if response.get("warning"):
                st.warning(response["warning"])

            if response.get("tools_executed"):
                with st.expander("🛠️ Análise realizada"):
                    for tool in response["tools_executed"]:
                        st.markdown(f"**Ferramenta executada**: `{tool.get('tool_name')}`")
                        prov = tool.get("provenance", {})
                        st.markdown(
                            f"- **Fonte**: {prov.get('source', 'TSE')}\n"
                            f"- **Camada**: {prov.get('layer', 'Gold')}\n"
                            f"- **Método**: {prov.get('method', 'Consulta agregada')}"
                        )
                        if tool.get("output"):
                            st.json(tool["output"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response["content"],
            "tools_executed": response.get("tools_executed"),
        }
    )
