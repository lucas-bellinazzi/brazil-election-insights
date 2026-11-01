"""Unit tests for core configuration and settings."""

from pathlib import Path

from election_research.core.config import Settings, find_project_root, get_settings


def test_find_project_root():
    root = find_project_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "src").is_dir()


def test_settings_default_values():
    settings = get_settings()
    assert settings.project_root.is_dir()
    assert settings.app_env in ("development", "testing", "production")
    assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    assert settings.data_dir == (settings.project_root / "data").resolve()
    assert settings.bronze_dir == settings.data_dir / "bronze"
    assert settings.silver_dir == settings.data_dir / "silver"
    assert settings.gold_dir == settings.data_dir / "gold"
    assert settings.manifests_dir == settings.data_dir / "metadata" / "manifests"


def test_settings_custom_directories(tmp_path: Path):
    custom_data = tmp_path / "custom_data"
    settings = Settings(
        project_root=tmp_path,
        data_dir_name=str(custom_data),
        app_env="testing",
        log_level="DEBUG",
    )
    assert settings.data_dir == custom_data
    assert settings.bronze_dir == custom_data / "bronze"
    assert settings.silver_dir == custom_data / "silver"

    settings.ensure_directories()
    assert settings.bronze_dir.is_dir()
    assert settings.silver_dir.is_dir()
    assert settings.gold_dir.is_dir()
    assert settings.manifests_dir.is_dir()
