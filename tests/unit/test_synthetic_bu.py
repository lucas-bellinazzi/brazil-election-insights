"""Unit tests for synthetic Boletim de Urna generator."""

import csv
from pathlib import Path

from tests.fixtures.synthetic_bu import (
    TSE_BWEB_COLUMNS,
    generate_synthetic_bu_rows,
    write_synthetic_bu_file,
)


def test_tse_column_count():
    assert len(TSE_BWEB_COLUMNS) == 45


def test_generate_synthetic_bu_rows():
    rows = generate_synthetic_bu_rows(ano=2026, turno=2, uf="AC", secoes=[10, 20])
    # 2 sections * 4 entries each (Cand A, Cand B, Branco, Nulo) = 8 rows
    assert len(rows) == 8
    for row in rows:
        assert set(row.keys()) == set(TSE_BWEB_COLUMNS)
        assert row["ANO_ELEICAO"] == 2026
        assert row["NR_TURNO"] == 2
        assert row["SG_UF"] == "AC"
        assert row["DS_CARGO_PERGUNTA"] == "Presidente"


def test_write_and_read_synthetic_bu_file(tmp_path: Path):
    target = tmp_path / "synthetic_test.csv"
    write_synthetic_bu_file(target, ano=2026, turno=2, uf="SP", secoes=[1])

    assert target.is_file()
    # Read back with latin-1 as expected for TSE files
    with open(target, encoding="iso-8859-1") as f:
        reader = csv.DictReader(f, delimiter=";")
        assert reader.fieldnames == TSE_BWEB_COLUMNS
        read_rows = list(reader)
        assert len(read_rows) == 4
        # Verify candidate and vote counts
        assert read_rows[0]["NM_VOTAVEL"] == "CANDIDATO A"
        assert int(read_rows[0]["QT_VOTOS"]) == 180
