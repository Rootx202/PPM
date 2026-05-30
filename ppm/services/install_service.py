"""Install service: package installation and removal."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.installers import PackageInstaller
from ppm.models import InstallResult
from ppm.repositories import RepositoryManager
from ppm.utils.console import get_logger
from ppm.wheelhouse import WheelhouseManager

logger = get_logger(__name__)


class InstallService:
    """Orchestrates package installation using injected components."""

    def __init__(
        self,
        config: PPMConfig,
        env_manager: EnvironmentManager,
        wheelhouse: WheelhouseManager,
        repo_manager: RepositoryManager,
    ) -> None:
        self.config = config
        self.installer = PackageInstaller(
            env_manager=env_manager,
            wheelhouse=wheelhouse,
            repo_manager=repo_manager,
            config=config,
        )

    def install(
        self,
        package: str,
        version_spec: str = "",
        offline: bool = False,
        upgrade: bool = False,
    ) -> InstallResult:
        """Install a package."""
        return self.installer.install(package, version_spec, offline=offline, upgrade=upgrade)

    def uninstall(self, package: str) -> InstallResult:
        """Uninstall a package."""
        return self.installer.uninstall(package)

    def install_from_requirements(
        self,
        requirements_file: Path,
        offline: bool = False,
    ) -> list[InstallResult]:
        """Install all packages from a requirements file."""
        return self.installer.install_requirements(requirements_file, offline=offline)
