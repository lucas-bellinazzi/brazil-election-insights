"""Methodology page — Documentation of sources, data processing, and statistical rigor."""

import streamlit as st

st.set_page_config(page_title="Metodologia — Brazil Election Insights", layout="wide")

st.title("📚 Metodologia e Integridade dos Dados")
st.markdown("Transparência, rastreabilidade e rigor científico no tratamento dos dados eleitorais.")

st.markdown(
    """
    ### 1. Fonte Oficial dos Dados
    Todos os dados primários utilizados nesta plataforma são gerados e disponibilizados oficialmente pelo
    **Tribunal Superior Eleitoral (TSE)** através do Portal de Dados Abertos:
    - **Conjunto de Dados**: *Boletim de Urna na Web (BWeb)*
    - **Unidade Básica de Análise**: Boletim de Urna (BU) emitido ao encerramento da votação em cada seção eleitoral física.
    - **Abrangência**: Todos os 26 estados brasileiros, o Distrito Federal e as seções de votação no exterior (ZZ).

    ---

    ### 2. Arquitetura de Dados Medalhão (Medallion)
    A integridade e reprodutibilidade dos dados são asseguradas por uma estrutura em três camadas:
    1. **Camada Bronze (Dados Brutos)**:
       - Armazenamento dos arquivos originais em formato CSV (`bweb_*.csv`).
       - Imutabilidade absoluta: os arquivos originais nunca são modificados ou reescritos.
       - Cálculo de hashes criptográficos **SHA-512** para cada arquivo e registro em manifestos de integridade.
    2. **Camada Silver (Dados Estruturados e Normalizados)**:
       - Decodificação em codificação `ISO-8859-1` e normalização para schemas canônicos tipados.
       - Separação em entidades dimensionais (`elections`, `polling_sections`, `candidates`) e tabela de fatos (`votes`).
       - Armazenamento em arquivos colunares particionados **Apache Parquet**.
    3. **Camada Gold (Dados Analíticos e Agregados)**:
       - Consolidação de totais nacionais, estaduais e municipais.
       - Cálculo determinístico de taxas de comparecimento, abstenção, votos nominais, votos em branco e nulos.

    ---

    ### 3. Invariantes Matemáticos e Validação
    Durante o processamento da camada Silver, cada seção eleitoral é submetida a verificações estritas:
    - **Identidade de Comparecimento**:
      $$\\text{Eleitores Aptos} = \\text{Comparecimento Total} + \\text{Abstenções}$$
    - **Identidade de Votação (Cargos Majoritários)**:
      $$\\text{Comparecimento Total} = \\text{Votos Válidos} + \\text{Votos em Branco} + \\text{Votos Nulos}$$
    - Registros com inconsistências ou campos obrigatórios ausentes são direcionados para quarentena auditável.

    ---

    ### 4. Diretrizes Éticas e Detecção de Anomalias
    - **Definição de Anomalia**: Um desvio estatístico atípico (detectado por Z-Score, IQR ou Isolation Forest)
      é estritamente um **sinal numérico para investigação exploratória**, como diferenças demográficas,
      geográficas ou logísticas entre municípios.
    - **Proibição de Alegações de Fraude**: Esta plataforma adota rigor metodológico e **nunca** classifica
      anomalias matemáticas como prova ou indício conclusivo de fraude eleitoral.
    - **Transparência na Inteligência Artificial**: O assistente de IA consulta unicamente ferramentas analíticas
      autorizadas e auditadas sobre a base DuckDB, sendo proibido de inventar estimativas ou executar código arbitrário.
    """
)
