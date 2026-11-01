"""Unit tests for DataRepository."""

from election_research.core.config import get_settings
from election_research.data.repository import DataRepository


def test_repository_load_silver():
    settings = get_settings()
    repo = DataRepository(settings)

    # We already ingested 2t
    elections = repo.load_elections(year=2026, election_round="2t")
    assert len(elections) > 0
    assert "election_year" in elections.columns

    candidates = repo.load_candidates(year=2026, election_round="2t", office_code=1)
    assert len(candidates) > 0
    assert "candidate_name" in candidates.columns

    # Check query on specific UF
    sections_zz = repo.load_polling_sections(year=2026, election_round="2t", uf="ZZ")
    assert len(sections_zz) > 0
    assert (sections_zz["state_abbreviation"] == "ZZ").all()
