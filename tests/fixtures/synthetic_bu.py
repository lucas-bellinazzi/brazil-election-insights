"""Synthetic generator for official TSE Boletim de Urna (BU) CSV test fixtures."""

import csv
from io import StringIO
from pathlib import Path
from typing import Any

TSE_BWEB_COLUMNS = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "CD_PLEITO",
    "DT_PLEITO",
    "NR_TURNO",
    "CD_ELEICAO",
    "DS_ELEICAO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "NR_LOCAL_VOTACAO",
    "CD_CARGO_PERGUNTA",
    "DS_CARGO_PERGUNTA",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "DT_BU_RECEBIDO",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "CD_TIPO_URNA",
    "DS_TIPO_URNA",
    "CD_TIPO_VOTAVEL",
    "DS_TIPO_VOTAVEL",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "QT_VOTOS",
    "NR_URNA_EFETIVADA",
    "CD_CARGA_1_URNA_EFETIVADA",
    "CD_CARGA_2_URNA_EFETIVADA",
    "CD_FLASHCARD_URNA_EFETIVADA",
    "DT_CARGA_URNA_EFETIVADA",
    "DS_CARGO_PERGUNTA_SECAO",
    "DS_SECOES_AGREGADAS",
    "DT_ABERTURA",
    "DT_ENCERRAMENTO",
    "QT_ELEI_BIOM_SEM_HABILITACAO",
    "DT_EMISSAO_BU",
    "NR_JUNTA_APURADORA",
    "NR_TURMA_APURADORA",
]


def generate_synthetic_bu_rows(
    ano: int = 2026,
    turno: int = 2,
    uf: str = "AC",
    cd_municipio: int = 1392,
    nm_municipio: str = "RIO BRANCO",
    secoes: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Generate realistic rows matching the TSE 45-column layout for testing."""
    if secoes is None:
        secoes = [1, 2]

    rows = []
    for secao in secoes:
        aptos = 400
        comparecimento = 320
        abstencoes = 80

        # Presidential candidate A (Nominal)
        rows.append(
            {
                "DT_GERACAO": "26/10/2026",
                "HH_GERACAO": "07:42:38",
                "ANO_ELEICAO": ano,
                "CD_TIPO_ELEICAO": 0,
                "NM_TIPO_ELEICAO": "Eleição Ordinária",
                "CD_PLEITO": 3221 if turno == 2 else 3220,
                "DT_PLEITO": "2026-10-25 00:00:00" if turno == 2 else "2026-10-04 00:00:00",
                "NR_TURNO": turno,
                "CD_ELEICAO": 6258 if turno == 2 else 6257,
                "DS_ELEICAO": "Eleição Geral Federal 2026",
                "SG_UF": uf,
                "CD_MUNICIPIO": cd_municipio,
                "NM_MUNICIPIO": nm_municipio,
                "NR_ZONA": 1,
                "NR_SECAO": secao,
                "NR_LOCAL_VOTACAO": 1001,
                "CD_CARGO_PERGUNTA": 1,
                "DS_CARGO_PERGUNTA": "Presidente",
                "NR_PARTIDO": 13,
                "SG_PARTIDO": "PT",
                "NM_PARTIDO": "PARTIDO DOS TRABALHADORES",
                "DT_BU_RECEBIDO": "2026-10-25 20:00:00",
                "QT_APTOS": aptos,
                "QT_COMPARECIMENTO": comparecimento,
                "QT_ABSTENCOES": abstencoes,
                "CD_TIPO_URNA": 1,
                "DS_TIPO_URNA": "Apurada",
                "CD_TIPO_VOTAVEL": 1,
                "DS_TIPO_VOTAVEL": "Nominal",
                "NR_VOTAVEL": 13,
                "NM_VOTAVEL": "CANDIDATO A",
                "QT_VOTOS": 180,
                "NR_URNA_EFETIVADA": 1234567,
                "CD_CARGA_1_URNA_EFETIVADA": "123.456.789.000.111.222.",
                "CD_CARGA_2_URNA_EFETIVADA": "999.888",
                "CD_FLASHCARD_URNA_EFETIVADA": "ABC12345",
                "DT_CARGA_URNA_EFETIVADA": "2026-09-15 10:00:00",
                "DS_CARGO_PERGUNTA_SECAO": f"1 - {secao}",
                "DS_SECOES_AGREGADAS": "#NULO#",
                "DT_ABERTURA": "2026-10-25 08:00:00",
                "DT_ENCERRAMENTO": "2026-10-25 17:00:00",
                "QT_ELEI_BIOM_SEM_HABILITACAO": 0,
                "DT_EMISSAO_BU": "2026-10-25 17:05:00",
                "NR_JUNTA_APURADORA": -1,
                "NR_TURMA_APURADORA": -1,
            }
        )

        # Presidential candidate B (Nominal)
        rows.append(
            {
                "DT_GERACAO": "26/10/2026",
                "HH_GERACAO": "07:42:38",
                "ANO_ELEICAO": ano,
                "CD_TIPO_ELEICAO": 0,
                "NM_TIPO_ELEICAO": "Eleição Ordinária",
                "CD_PLEITO": 3221 if turno == 2 else 3220,
                "DT_PLEITO": "2026-10-25 00:00:00" if turno == 2 else "2026-10-04 00:00:00",
                "NR_TURNO": turno,
                "CD_ELEICAO": 6258 if turno == 2 else 6257,
                "DS_ELEICAO": "Eleição Geral Federal 2026",
                "SG_UF": uf,
                "CD_MUNICIPIO": cd_municipio,
                "NM_MUNICIPIO": nm_municipio,
                "NR_ZONA": 1,
                "NR_SECAO": secao,
                "NR_LOCAL_VOTACAO": 1001,
                "CD_CARGO_PERGUNTA": 1,
                "DS_CARGO_PERGUNTA": "Presidente",
                "NR_PARTIDO": 22,
                "SG_PARTIDO": "PL",
                "NM_PARTIDO": "PARTIDO LIBERAL",
                "DT_BU_RECEBIDO": "2026-10-25 20:00:00",
                "QT_APTOS": aptos,
                "QT_COMPARECIMENTO": comparecimento,
                "QT_ABSTENCOES": abstencoes,
                "CD_TIPO_URNA": 1,
                "DS_TIPO_URNA": "Apurada",
                "CD_TIPO_VOTAVEL": 1,
                "DS_TIPO_VOTAVEL": "Nominal",
                "NR_VOTAVEL": 22,
                "NM_VOTAVEL": "CANDIDATO B",
                "QT_VOTOS": 120,
                "NR_URNA_EFETIVADA": 1234567,
                "CD_CARGA_1_URNA_EFETIVADA": "123.456.789.000.111.222.",
                "CD_CARGA_2_URNA_EFETIVADA": "999.888",
                "CD_FLASHCARD_URNA_EFETIVADA": "ABC12345",
                "DT_CARGA_URNA_EFETIVADA": "2026-09-15 10:00:00",
                "DS_CARGO_PERGUNTA_SECAO": f"1 - {secao}",
                "DS_SECOES_AGREGADAS": "#NULO#",
                "DT_ABERTURA": "2026-10-25 08:00:00",
                "DT_ENCERRAMENTO": "2026-10-25 17:00:00",
                "QT_ELEI_BIOM_SEM_HABILITACAO": 0,
                "DT_EMISSAO_BU": "2026-10-25 17:05:00",
                "NR_JUNTA_APURADORA": -1,
                "NR_TURMA_APURADORA": -1,
            }
        )

        # Branco (Blank)
        rows.append(
            {
                "DT_GERACAO": "26/10/2026",
                "HH_GERACAO": "07:42:38",
                "ANO_ELEICAO": ano,
                "CD_TIPO_ELEICAO": 0,
                "NM_TIPO_ELEICAO": "Eleição Ordinária",
                "CD_PLEITO": 3221 if turno == 2 else 3220,
                "DT_PLEITO": "2026-10-25 00:00:00" if turno == 2 else "2026-10-04 00:00:00",
                "NR_TURNO": turno,
                "CD_ELEICAO": 6258 if turno == 2 else 6257,
                "DS_ELEICAO": "Eleição Geral Federal 2026",
                "SG_UF": uf,
                "CD_MUNICIPIO": cd_municipio,
                "NM_MUNICIPIO": nm_municipio,
                "NR_ZONA": 1,
                "NR_SECAO": secao,
                "NR_LOCAL_VOTACAO": 1001,
                "CD_CARGO_PERGUNTA": 1,
                "DS_CARGO_PERGUNTA": "Presidente",
                "NR_PARTIDO": -1,
                "SG_PARTIDO": "#NULO#",
                "NM_PARTIDO": "#NULO#",
                "DT_BU_RECEBIDO": "2026-10-25 20:00:00",
                "QT_APTOS": aptos,
                "QT_COMPARECIMENTO": comparecimento,
                "QT_ABSTENCOES": abstencoes,
                "CD_TIPO_URNA": 1,
                "DS_TIPO_URNA": "Apurada",
                "CD_TIPO_VOTAVEL": 2,
                "DS_TIPO_VOTAVEL": "Branco",
                "NR_VOTAVEL": 95,
                "NM_VOTAVEL": "Branco",
                "QT_VOTOS": 12,
                "NR_URNA_EFETIVADA": 1234567,
                "CD_CARGA_1_URNA_EFETIVADA": "123.456.789.000.111.222.",
                "CD_CARGA_2_URNA_EFETIVADA": "999.888",
                "CD_FLASHCARD_URNA_EFETIVADA": "ABC12345",
                "DT_CARGA_URNA_EFETIVADA": "2026-09-15 10:00:00",
                "DS_CARGO_PERGUNTA_SECAO": f"1 - {secao}",
                "DS_SECOES_AGREGADAS": "#NULO#",
                "DT_ABERTURA": "2026-10-25 08:00:00",
                "DT_ENCERRAMENTO": "2026-10-25 17:00:00",
                "QT_ELEI_BIOM_SEM_HABILITACAO": 0,
                "DT_EMISSAO_BU": "2026-10-25 17:05:00",
                "NR_JUNTA_APURADORA": -1,
                "NR_TURMA_APURADORA": -1,
            }
        )

        # Nulo (Null)
        rows.append(
            {
                "DT_GERACAO": "26/10/2026",
                "HH_GERACAO": "07:42:38",
                "ANO_ELEICAO": ano,
                "CD_TIPO_ELEICAO": 0,
                "NM_TIPO_ELEICAO": "Eleição Ordinária",
                "CD_PLEITO": 3221 if turno == 2 else 3220,
                "DT_PLEITO": "2026-10-25 00:00:00" if turno == 2 else "2026-10-04 00:00:00",
                "NR_TURNO": turno,
                "CD_ELEICAO": 6258 if turno == 2 else 6257,
                "DS_ELEICAO": "Eleição Geral Federal 2026",
                "SG_UF": uf,
                "CD_MUNICIPIO": cd_municipio,
                "NM_MUNICIPIO": nm_municipio,
                "NR_ZONA": 1,
                "NR_SECAO": secao,
                "NR_LOCAL_VOTACAO": 1001,
                "CD_CARGO_PERGUNTA": 1,
                "DS_CARGO_PERGUNTA": "Presidente",
                "NR_PARTIDO": -1,
                "SG_PARTIDO": "#NULO#",
                "NM_PARTIDO": "#NULO#",
                "DT_BU_RECEBIDO": "2026-10-25 20:00:00",
                "QT_APTOS": aptos,
                "QT_COMPARECIMENTO": comparecimento,
                "QT_ABSTENCOES": abstencoes,
                "CD_TIPO_URNA": 1,
                "DS_TIPO_URNA": "Apurada",
                "CD_TIPO_VOTAVEL": 3,
                "DS_TIPO_VOTAVEL": "Nulo",
                "NR_VOTAVEL": 96,
                "NM_VOTAVEL": "Nulo",
                "QT_VOTOS": 8,
                "NR_URNA_EFETIVADA": 1234567,
                "CD_CARGA_1_URNA_EFETIVADA": "123.456.789.000.111.222.",
                "CD_CARGA_2_URNA_EFETIVADA": "999.888",
                "CD_FLASHCARD_URNA_EFETIVADA": "ABC12345",
                "DT_CARGA_URNA_EFETIVADA": "2026-09-15 10:00:00",
                "DS_CARGO_PERGUNTA_SECAO": f"1 - {secao}",
                "DS_SECOES_AGREGADAS": "#NULO#",
                "DT_ABERTURA": "2026-10-25 08:00:00",
                "DT_ENCERRAMENTO": "2026-10-25 17:00:00",
                "QT_ELEI_BIOM_SEM_HABILITACAO": 0,
                "DT_EMISSAO_BU": "2026-10-25 17:05:00",
                "NR_JUNTA_APURADORA": -1,
                "NR_TURMA_APURADORA": -1,
            }
        )

    return rows


def create_synthetic_bu_csv_content(
    ano: int = 2026,
    turno: int = 2,
    uf: str = "AC",
    cd_municipio: int = 1392,
    nm_municipio: str = "RIO BRANCO",
    secoes: list[int] | None = None,
) -> str:
    """Generate in-memory CSV string with TSE format."""
    rows = generate_synthetic_bu_rows(
        ano=ano,
        turno=turno,
        uf=uf,
        cd_municipio=cd_municipio,
        nm_municipio=nm_municipio,
        secoes=secoes,
    )
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=TSE_BWEB_COLUMNS,
        delimiter=";",
        quoting=csv.QUOTE_NONNUMERIC,
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def write_synthetic_bu_file(
    target_path: Path,
    ano: int = 2026,
    turno: int = 2,
    uf: str = "AC",
    secoes: list[int] | None = None,
) -> Path:
    """Write synthetic BU CSV encoded in Latin-1 as used by TSE."""
    content = create_synthetic_bu_csv_content(ano=ano, turno=turno, uf=uf, secoes=secoes)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(content.encode("iso-8859-1"))
    return target_path
