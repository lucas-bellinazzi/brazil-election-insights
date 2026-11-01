"""Unit tests for data normalizer."""

import polars as pl

from election_research.data.normalizer import normalize_bu_dataframe


def test_normalize_bu_dataframe_columns_and_types():
    raw_dict = {
        "DT_GERACAO": ["26/10/2026"],
        "HH_GERACAO": ["07:42:38"],
        "ANO_ELEICAO": [2026],
        "CD_TIPO_ELEICAO": [0],
        "NM_TIPO_ELEICAO": ["Eleição Ordinária"],
        "CD_PLEITO": [3221],
        "DT_PLEITO": ["2026-10-25 00:00:00"],
        "NR_TURNO": [2],
        "CD_ELEICAO": [6258],
        "DS_ELEICAO": ["Eleição Geral Federal 2026"],
        "SG_UF": ["AC"],
        "CD_MUNICIPIO": [1392],
        "NM_MUNICIPIO": ["RIO BRANCO"],
        "NR_ZONA": [1],
        "NR_SECAO": [10],
        "NR_LOCAL_VOTACAO": [1001],
        "CD_CARGO_PERGUNTA": [1],
        "DS_CARGO_PERGUNTA": ["Presidente"],
        "NR_PARTIDO": [-1],
        "SG_PARTIDO": ["#NULO#"],
        "NM_PARTIDO": ["#NULO#"],
        "DT_BU_RECEBIDO": ["2026-10-25 20:00:00"],
        "QT_APTOS": [400],
        "QT_COMPARECIMENTO": [320],
        "QT_ABSTENCOES": [80],
        "CD_TIPO_URNA": [1],
        "DS_TIPO_URNA": ["Apurada"],
        "CD_TIPO_VOTAVEL": [2],
        "DS_TIPO_VOTAVEL": ["Branco"],
        "NR_VOTAVEL": [95],
        "NM_VOTAVEL": ["Branco"],
        "QT_VOTOS": [12],
        "NR_URNA_EFETIVADA": [123456],
        "CD_CARGA_1_URNA_EFETIVADA": ["HASH1"],
        "CD_CARGA_2_URNA_EFETIVADA": ["HASH2"],
        "CD_FLASHCARD_URNA_EFETIVADA": ["FLASH1"],
        "DT_CARGA_URNA_EFETIVADA": ["2026-09-15 10:00:00"],
        "DS_CARGO_PERGUNTA_SECAO": ["1 - 10"],
        "DS_SECOES_AGREGADAS": ["#NULO#"],
        "DT_ABERTURA": ["2026-10-25 08:00:00"],
        "DT_ENCERRAMENTO": ["2026-10-25 17:00:00"],
        "QT_ELEI_BIOM_SEM_HABILITACAO": [0],
        "DT_EMISSAO_BU": ["2026-10-25 17:05:00"],
        "NR_JUNTA_APURADORA": [-1],
        "NR_TURMA_APURADORA": [-1],
    }
    raw_df = pl.DataFrame(raw_dict)
    normalized = normalize_bu_dataframe(raw_df, "bweb_2t_AC.csv")

    assert "state_abbreviation" in normalized.columns
    assert "party_abbreviation" in normalized.columns
    assert normalized["party_abbreviation"][0] is None
    assert normalized["party_number"][0] is None
    assert normalized["source_file"][0] == "bweb_2t_AC.csv"
    assert normalized["eligible_voters"][0] == 400
    assert normalized["vote_count"][0] == 12
