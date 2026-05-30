
import pytest
from typer.testing import CliRunner
from ppm.cli.app import app
from unittest.mock import MagicMock, patch
from pathlib import Path

runner = CliRunner()

def test_update_package_calls_service_with_upgrade():
    """Verify that 'ppm update <package>' calls InstallService.install with upgrade=True."""
    with patch("ppm.cli.app._get_container") as mock_get_container:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        # Mock requirement checks
        mock_container.environment_service.require_env.return_value = None

        # Mock the install method
        mock_container.install_service.install.return_value = MagicMock(
            success=True, package="fastapi", version="0.100.0", elapsed_seconds=1.0
        )

        result = runner.invoke(app, ["update", "fastapi"])

        assert result.exit_code == 0
        mock_container.install_service.install.assert_called_with(
            "fastapi", version_spec="", offline=False, upgrade=True
        )

def test_update_all_calls_service_with_upgrade(tmp_path):
    """Verify that 'ppm update' (all) calls InstallService.install with upgrade=True for each requirement."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi\nrequests")

    with patch("ppm.cli.app._get_container") as mock_get_container:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        mock_container.environment_service.require_env.return_value = None
        mock_container.install_service.install.return_value = MagicMock(
            success=True, package="somepkg", version="1.0.0"
        )

        # We need to mock parse_requirements as well because it's imported inside the command
        with patch("ppm.parsers.parse_requirements") as mock_parse:
            from ppm.models import Requirement
            mock_parse.return_value = [
                Requirement(name="fastapi"),
                Requirement(name="requests")
            ]

            result = runner.invoke(app, ["update", "-r", str(req_file)])

            assert result.exit_code == 0
            assert mock_container.install_service.install.call_count == 2

            # Check if upgrade=True was passed in both calls
            calls = mock_container.install_service.install.call_args_list
            assert calls[0].kwargs["upgrade"] is True
            assert calls[1].kwargs["upgrade"] is True
