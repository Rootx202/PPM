"""Doctor service: environment health checks."""

from __future__ import annotations

import shutil
import sys

from ppm.config import PPM_CONFIG_FILE, PPMConfig
from ppm.environments import EnvironmentManager
from ppm.models import DoctorCheck, DoctorReport
from ppm.utils.console import get_logger

logger = get_logger(__name__)


class DoctorService:
    """Runs diagnostic checks on the PPM environment and configuration."""

    def __init__(self, config: PPMConfig, env_manager: EnvironmentManager) -> None:
        self.config = config
        self.env = env_manager

    def run(self) -> DoctorReport:
        """Execute all health checks and return the report."""
        report = DoctorReport()

        report.checks.append(self._check_python_version())
        report.checks.append(self._check_pip_available())
        report.checks.append(self._check_venv_exists())
        report.checks.append(self._check_pip_audit_installed())
        report.checks.append(self._check_wheelhouse_dir())
        report.checks.append(self._check_config_file())
        report.checks.append(self._check_internet_connectivity())

        return report

    def _check_python_version(self) -> DoctorCheck:
        version = sys.version_info
        passed = version >= (3, 12)
        return DoctorCheck(
            name="Python version >= 3.12",
            passed=passed,
            message=f"Python {version.major}.{version.minor}.{version.micro}",
            suggestion="Upgrade to Python 3.12+" if not passed else None,
        )

    def _check_pip_available(self) -> DoctorCheck:
        pip_path = shutil.which("pip") or shutil.which("pip3")
        return DoctorCheck(
            name="pip available",
            passed=pip_path is not None,
            message=pip_path or "pip not found in PATH",
            suggestion="Install pip: https://pip.pypa.io" if not pip_path else None,
        )

    def _check_venv_exists(self) -> DoctorCheck:
        exists = self.env.exists()
        return DoctorCheck(
            name="Virtual environment exists",
            passed=exists,
            message=str(self.env.venv_path) if exists else "No .venv found",
            suggestion="Run 'ppm init' to create one" if not exists else None,
        )

    def _check_pip_audit_installed(self) -> DoctorCheck:
        pip_audit = shutil.which("pip-audit")
        if not pip_audit and self.env.exists():
            # Check inside venv
            venv_bin = self.env.pip.parent
            candidate = venv_bin / "pip-audit"
            if candidate.exists():
                pip_audit = str(candidate)
        return DoctorCheck(
            name="pip-audit available",
            passed=pip_audit is not None,
            message=pip_audit or "pip-audit not found",
            suggestion="Run: pip install pip-audit" if not pip_audit else None,
        )

    def _check_wheelhouse_dir(self) -> DoctorCheck:
        wh_path = self.config.wheelhouse.path
        exists = wh_path.exists()
        accessible = exists and wh_path.is_dir()
        return DoctorCheck(
            name="Wheelhouse directory accessible",
            passed=accessible,
            message=str(wh_path) if accessible else f"Not found: {wh_path}",
            suggestion="Run 'ppm wheelhouse build' to populate it" if not accessible else None,
        )

    def _check_config_file(self) -> DoctorCheck:
        exists = PPM_CONFIG_FILE.exists()
        return DoctorCheck(
            name="PPM config file",
            passed=True,  # Not required to work
            message=str(PPM_CONFIG_FILE) if exists else "Using defaults (no config file)",
        )

    def _check_internet_connectivity(self) -> DoctorCheck:
        import socket

        try:
            socket.create_connection(("pypi.org", 443), timeout=5)
            return DoctorCheck(
                name="Internet connectivity (pypi.org)",
                passed=True,
                message="Connected to pypi.org:443",
            )
        except OSError:
            return DoctorCheck(
                name="Internet connectivity (pypi.org)",
                passed=False,
                message="Cannot reach pypi.org",
                suggestion="Check network connection or use --offline flag",
            )
