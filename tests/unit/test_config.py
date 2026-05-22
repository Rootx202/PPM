"""Unit tests for the configuration manager."""

import os
import pytest
from pathlib import Path
from ppm.config import PPMConfig, RepositoryConfig, WheelhouseConfig


class TestPPMConfig:
    def test_default_values(self):
        config = PPMConfig()
        assert config.repository.index_url == "https://pypi.org/simple"
        assert len(config.repository.mirrors) == 2
        assert config.repository.timeout == 30
        assert config.repository.max_retries == 3
        assert config.offline_mode is False
        assert config.venv_name == ".venv"

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv("PPM_INDEX_URL", "https://custom.pypi.org/simple")
        monkeypatch.setenv("PPM_TIMEOUT", "60")
        monkeypatch.setenv("PPM_OFFLINE", "true")
        monkeypatch.setenv("PPM_MAX_RETRIES", "5")

        config = PPMConfig()
        config._apply_env_overrides()

        assert config.repository.index_url == "https://custom.pypi.org/simple"
        assert config.repository.timeout == 60
        assert config.offline_mode is True
        assert config.repository.max_retries == 5

    def test_mirrors_env_var(self, monkeypatch):
        monkeypatch.setenv(
            "PPM_FALLBACK_MIRRORS",
            "https://mirror1.com/simple,https://mirror2.com/simple",
        )
        config = PPMConfig()
        config._apply_env_overrides()
        assert "https://mirror1.com/simple" in config.repository.mirrors
        assert "https://mirror2.com/simple" in config.repository.mirrors

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Test round-trip save/load of config."""
        import ppm.config as cfg_module
        config_file = tmp_path / "config.toml"
        monkeypatch.setattr(cfg_module, "PPM_CONFIG_FILE", config_file)
        monkeypatch.setattr(cfg_module, "PPM_CONFIG_DIR", tmp_path)

        config = PPMConfig()
        config.repository.timeout = 99
        config.offline_mode = True
        config.save()

        assert config_file.exists()

    def test_to_display_dict(self):
        config = PPMConfig()
        display = config.to_display_dict()
        assert "General" in display
        assert "Repository" in display
        assert "Wheelhouse" in display
        assert "Logging" in display


class TestRepositoryConfig:
    def test_defaults(self):
        repo = RepositoryConfig()
        assert repo.index_url == "https://pypi.org/simple"
        assert repo.timeout == 30
        assert repo.max_retries == 3
        assert repo.trusted_hosts == []
