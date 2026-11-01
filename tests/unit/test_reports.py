"""Unit tests for automated analytical report generator."""

from pathlib import Path

from scripts.generate_report import generate_analytical_report


def test_generate_analytical_report(tmp_path: Path):
    output_dir = tmp_path / "reports"
    report_file = generate_analytical_report(year=2026, election_round="2t", output_dir=output_dir)

    assert report_file.is_file()
    content = report_file.read_text(encoding="utf-8")
    assert "Relatório Analítico Oficial" in content
    assert "Eleitorado Apto Total" in content
    assert "Desvios Paramétricos" in content
