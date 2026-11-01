"""AI Assistant page — Interactive conversational research with allowlisted analytical tools."""

import streamlit as st
from app.utils.session_state import init_session_state

from election_research.ai.assistant import ElectionAIAssistant

st.set_page_config(page_title="Assistente de IA — Brazil Election Insights", layout="wide")
init_session_state()

st.title("🤖 Assistente de Investigação Eleitoral")
st.markdown(
    """
    Tire dúvidas sobre os resultados eleitorais. O assistente é **estritamente ancorado**
    em ferramentas analíticas autorizadas sobre o banco de dados DuckDB, garantindo que
    toda informação numérica seja verificável e auditável.
    """
)

# Guardrail notice
with st.expander("ℹ️ Como funciona o Assistente e suas Diretrizes de Rigor"):
    st.markdown(
        """
        - **Ferramentas Auditadas**: O assistente não executa SQL livre ou Python arbitrário. Ele seleciona funções pré-aprovadas.
        - **Sem Fraude ou Julgamentos Políticos**: Anomalias estatísticas são descritas como hipóteses para análise metodológica.
        - **Dados Reais**: Nenhuma estatística é estimada ou inventada pela IA.
        """
    )

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools_executed"):
            with st.expander("🛠️ Ferramentas Analíticas Executadas"):
                st.json(msg["tools_executed"])

# Chat input
if prompt := st.chat_input("Ex: Quais municípios tiveram as maiores taxas de abstenção?"):
    # Render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process via Assistant
    assistant = ElectionAIAssistant()
    with st.chat_message("assistant"):
        with st.spinner("Consultando dados oficiais..."):
            response = assistant.process_query(
                user_message=prompt,
                conversation_history=st.session_state.messages[:-1],
            )
            st.markdown(response["content"])
            if response.get("tools_executed"):
                with st.expander("🛠️ Ferramentas Analíticas Executadas"):
                    st.json(response["tools_executed"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response["content"],
            "tools_executed": response.get("tools_executed"),
        }
    )
