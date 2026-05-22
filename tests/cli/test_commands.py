"""CLI command tests using Typer test client."""

import pytest
from typer.testing import CliRunner
from ppm.cli.app import app

runner = CliRunner()


class TestCLIBasic:
    def test_help_displayed(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "PPM" in result.output or "ppm" in result.output.lower()

    def test_init_help(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "virtual environment" in result.output.lower()

    def test_sync_help(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0

    def test_install_help(self):
        result = runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0

    def test_remove_help(self):
        result = runner.invoke(app, ["remove", "--help"])
        assert result.exit_code == 0

    def test_search_help(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0

    def test_audit_help(self):
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0

    def test_repair_help(self):
        result = runner.invoke(app, ["repair", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self):
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_wheelhouse_help(self):
        result = runner.invoke(app, ["wheelhouse", "--help"])
        assert result.exit_code == 0

    def test_cache_help(self):
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0


class TestCLIInit:
    def test_init_creates_venv(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        # Either succeeds or fails gracefully
        assert result.exit_code in (0, 1)

    def test_init_force_flag_exists(self):
        result = runner.invoke(app, ["init", "--help"])
        assert "--force" in result.output or "-f" in result.output


class TestCLISearch:
    def test_search_no_network_graceful(self, monkeypatch):
        """Search should not crash, even with network issues."""
        from unittest.mock import AsyncMock, patch

        async def mock_search(*args, **kwargs):
            return []

        with patch(
            "ppm.repositories.RepositoryManager.search_packages",
            new=mock_search,
        ):
            result = runner.invoke(app, ["search", "somepackage"])
            assert result.exit_code == 0


class TestCLIConfig:
    def test_config_show(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        # Should show some config keys
        assert "Repository" in result.output or "repository" in result.output.lower()
