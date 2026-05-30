"""Unit tests for environment manager."""

from unittest.mock import patch

import pytest

from ppm.environments import EnvironmentManager, detect_os
from ppm.models import OSType


class TestDetectOS:
    def test_linux_detection(self):
        with patch("platform.system", return_value="Linux"):
            assert detect_os() == OSType.LINUX

    def test_windows_detection(self):
        with patch("platform.system", return_value="Windows"):
            assert detect_os() == OSType.WINDOWS

    def test_macos_detection(self):
        with patch("platform.system", return_value="Darwin"):
            assert detect_os() == OSType.MACOS

    def test_unknown_detection(self):
        with patch("platform.system", return_value="SomeUnknownOS"):
            assert detect_os() == OSType.UNKNOWN


class TestEnvironmentManager:
    def test_venv_path(self, tmp_path):
        mgr = EnvironmentManager(tmp_path, ".venv")
        assert mgr.venv_path == tmp_path / ".venv"

    def test_does_not_exist_initially(self, tmp_path):
        mgr = EnvironmentManager(tmp_path, ".venv")
        assert not mgr.exists()

    def test_python_path_linux(self, tmp_path):
        with patch("platform.system", return_value="Linux"):
            mgr = EnvironmentManager(tmp_path, ".venv")
            expected = tmp_path / ".venv" / "bin" / "python"
            assert mgr.python == expected

    def test_python_path_windows(self, tmp_path):
        with patch("platform.system", return_value="Windows"):
            mgr = EnvironmentManager(tmp_path, ".venv")
            expected = tmp_path / ".venv" / "Scripts" / "python.exe"
            assert mgr.python == expected

    def test_activation_command_linux(self, tmp_path):
        with patch("platform.system", return_value="Linux"):
            mgr = EnvironmentManager(tmp_path, ".venv")
            cmd = mgr.activation_command()
            assert "source" in cmd
            assert "/bin/activate" in cmd

    def test_activation_command_windows(self, tmp_path):
        with patch("platform.system", return_value="Windows"):
            mgr = EnvironmentManager(tmp_path, ".venv")
            cmd = mgr.activation_command()
            assert "Scripts" in cmd
            assert "activate" in cmd

    def test_remove_nonexistent(self, tmp_path):
        mgr = EnvironmentManager(tmp_path, ".venv")
        # Should not raise
        mgr.remove()


class TestEnvironmentIntegration:
    """Integration tests that actually create a venv (slower)."""

    @pytest.mark.slow
    def test_create_and_inspect(self, tmp_path):
        mgr = EnvironmentManager(tmp_path, ".venv")
        assert not mgr.exists()
        info = mgr.create(upgrade_pip=False)
        assert mgr.exists()
        assert info.python_version
        mgr.remove()
        assert not mgr.exists()
