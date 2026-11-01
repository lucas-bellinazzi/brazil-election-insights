"""Unit tests for Bronze manifests."""

from pathlib import Path

from election_research.ingestion.manifest import BronzeManifest, ManifestFileEntry


def test_manifest_lifecycle(tmp_path: Path):
    manifest = BronzeManifest(year=2026, election_round="1t")
    entry = ManifestFileEntry(
        file_name="bweb_1t_AC_051020261403.csv",
        relative_path="data/bronze/tse/2026/1t/bweb_1t_AC_051020261403.csv",
        year=2026,
        election_round="1t",
        uf="AC",
        size_bytes=1024,
        sha512="abcdef123456",
        integrity_status="no_reference",
    )
    manifest.add_entry(entry)

    assert manifest.total_files == 1
    assert manifest.total_bytes == 1024

    manifest_file = tmp_path / "manifest.json"
    manifest.save(manifest_file)
    assert manifest_file.is_file()

    loaded = BronzeManifest.load(manifest_file)
    assert loaded.year == 2026
    assert loaded.election_round == "1t"
    assert len(loaded.files) == 1
    assert loaded.files[0].sha512 == "abcdef123456"
