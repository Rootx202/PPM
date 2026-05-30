"""Audit service: vulnerability scanning and security reporting."""

from __future__ import annotations

from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.models import AuditReport
from ppm.security import check_deprecated_packages, run_audit
from ppm.utils.console import get_logger

logger = get_logger(__name__)


class AuditService:
    """Runs security audits and collects vulnerability reports."""

    def __init__(self, config: PPMConfig, env_manager: EnvironmentManager) -> None:
        self.config = config
        self.env = env_manager

    def audit(
        self,
        requirements_file: Path | None = None,
    ) -> tuple[AuditReport, list[dict]]:
        """
        Run pip-audit and check for deprecated packages.

        Returns:
            (AuditReport, deprecated_list) where deprecated_list is a list of
            dicts with package/version/warning keys.
        """
        report = run_audit(
            pip_executable=self.env.pip,
            requirements_file=requirements_file,
        )

        # Also check deprecated packages
        packages = self.env.list_packages()
        deprecated = check_deprecated_packages(packages)

        return report, deprecated
