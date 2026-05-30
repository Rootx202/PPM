"""Sync service: requirements.txt synchronization."""

from __future__ import annotations

import json
from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.installers import PackageInstaller
from ppm.models import SyncResult
from ppm.parsers import generate_lock_metadata, parse_requirements
from ppm.repositories import RepositoryManager
from ppm.utils.console import get_logger
from ppm.wheelhouse import WheelhouseManager

logger = get_logger(__name__)

LOCK_FILE_NAME = "ppm.lock.json"


class SyncService:
    """Synchronizes the virtual environment with requirements.txt."""

    def __init__(
        self,
        config: PPMConfig,
        env_manager: EnvironmentManager,
        wheelhouse: WheelhouseManager,
        repo_manager: RepositoryManager,
    ) -> None:
        self.config = config
        self.env = env_manager
        self.installer = PackageInstaller(
            env_manager=env_manager,
            wheelhouse=wheelhouse,
            repo_manager=repo_manager,
            config=config,
        )
        self.repo = repo_manager

    def sync(
        self,
        requirements_file: Path,
        offline: bool = False,
        generate_lock: bool = True,
    ) -> SyncResult:
        """
        Read requirements.txt, install missing packages, and optionally
        generate a lock file.

        Returns a SyncResult with lists of installed/satisfied/failed packages.
        """
        if not requirements_file.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_file}")

        requirements = parse_requirements(requirements_file)
        result = SyncResult(total=len(requirements))

        for req in requirements:
            pkg_display = str(req) if req.name else req.url or "?"

            # Check if already installed at correct version
            if req.name:
                installed_version = self.env.is_package_installed(req.name)
                if installed_version and self._version_satisfied(
                    installed_version, req.version_spec
                ):
                    result.already_satisfied.append(pkg_display)
                    continue

            # Install
            if req.url:
                ok, output = self.env.run_pip(["install", req.url])
                if ok:
                    result.installed.append(pkg_display)
                else:
                    result.failed.append(pkg_display)
            elif req.name:
                install_result = self.installer.install(req.name, req.version_spec, offline=offline)
                if install_result.success:
                    result.installed.append(pkg_display)
                else:
                    result.failed.append(pkg_display)
                    logger.warning(f"Failed to install {pkg_display}: {install_result.error}")

        # Generate lock file
        if generate_lock and not result.failed:
            self._write_lock(requirements_file.parent, requirements)

        return result

    def _version_satisfied(self, installed: str, spec: str) -> bool:
        """Check if installed version satisfies the spec."""
        if not spec:
            return True
        try:
            from packaging.specifiers import SpecifierSet
            from packaging.version import Version

            return Version(installed) in SpecifierSet(spec)
        except Exception:
            return True  # Assume satisfied on parse error

    def _write_lock(self, project_dir: Path, requirements: list) -> None:
        """Write ppm.lock.json to the project directory."""
        try:
            lock_data = generate_lock_metadata(requirements, self.env.pip)
            lock_path = project_dir / LOCK_FILE_NAME
            with open(lock_path, "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2)
            logger.info(f"Lock file written: {lock_path}")
        except Exception as e:
            logger.warning(f"Failed to write lock file: {e}")
