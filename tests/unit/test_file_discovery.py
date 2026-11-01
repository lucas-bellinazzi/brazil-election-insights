"""Unit tests for Bronze file discovery."""

from pathlib import Path

from tests.fixtures.synthetic_bu import write_synthetic_bu_file

from election_research.ingestion.file_discovery import (
    discover_bronze_files,
    parse_bronze_filename,
)


def test_parse_bronze_filename(tmp_path: Path):
    f = tmp_path / "bweb_1t_AC_051020261403.csv"
    f.touch()

    info = parse_bronze_filename(f, year=2026)
    assert info is not None
    assert info.election_round == "1t"
    assert info.uf == "AC"
    assert info.file_timestamp == "051020261403"
    assert info.year == 2026


def test_parse_invalid_filename(tmp_path: Path):
    f = tmp_path / "some_random_file.csv"
    f.touch()
    assert parse_bronze_filename(f, year=2026) is None


def test_discover_bronze_files(tmp_path: Path):
    # Setup mock bronze directory structure
    tse_dir = tmp_path / "bronze" / "tse" / "2026"
    round1 = tse_dir / "1t"
    round2 = tse_dir / "2t"

    write_synthetic_bu_file(round1 / "bweb_1t_AC_051020261403.csv", uf="AC", turno=1)
    write_synthetic_bu_file(round1 / "bweb_1t_SP_051020261403.csv", uf="SP", turno=1)
    write_synthetic_bu_file(round2 / "bweb_2t_AC_261020260742.csv", uf="AC", turno=2)

    all_files = discover_bronze_files(tmp_path / "bronze", year=2026)
    assert len(all_files) == 3

    r1_files = discover_bronze_files(tmp_path / "bronze", year=2026, election_round="1t")
    assert len(r1_files) == 2

    sp_files = discover_bronze_files(tmp_path / "bronze", year=2026, uf="SP")
    assert len(sp_files) == 1
    assert sp_files[0].uf == "SP"
