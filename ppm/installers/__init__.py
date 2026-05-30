"""Package installer with wheelhouse-first strategy and fallback mirrors."""

from __future__ import annotations

import time
from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.models import InstallResult
from ppm.repositories import RepositoryManager
from ppm.utils.console import get_logger
from ppm.utils.security import validate_package_name
from ppm.wheelhouse import WheelhouseManager

logger = get_logger(__name__)


class PackageInstaller:
    """
    Installs packages using a prioritized strategy:
    1. Check wheelhouse cache (offline-first)
    2. Install from PyPI with fallback mirrors
    3. Retry with exponential back-off

    Supports:
    - Single package installs
    - Version-constrained installs
    - Offline installs (wheelhouse only)
    - Batch installs with progress reporting
    """

    def __init__(
        self,
        env_manager: EnvironmentManager,
        wheelhouse: WheelhouseManager,
        repo_manager: RepositoryManager,
        config: PPMConfig,
    ) -> None:
        self.env = env_manager
        self.wheelhouse = wheelhouse
        self.repo = repo_manager
        self.config = config

    def install(
        self,
        package: str,
        version_spec: str = "",
        offline: bool = False,
        upgrade: bool = False,
    ) -> InstallResult:
        """
        Install a single package.

        Args:
            package: Package name (e.g. "fastapi").
            version_spec: Optional version constraint (e.g. ">=0.100.0").
            offline: If True, only use wheelhouse cache.
            upgrade: If True, upgrade the package to the newest available version.
        """
        if not validate_package_name(package):
            return InstallResult(
                package=package,
                version="",
                success=False,
                error=f"Invalid package name: {package!r}",
            )

        start = time.monotonic()
        package_spec = f"{package}{version_spec}" if version_spec else package

        # ── 1. Try wheelhouse ─────────────────────────────────────────────────
        cached_wheel = self.wheelhouse.find_wheel(package)
        if cached_wheel and not upgrade:
            logger.debug(f"Found cached wheel for {package}: {cached_wheel.filename}")
            args = [
                "install",
                "--no-index",
                "--find-links",
                str(self.wheelhouse.path),
                package_spec,
            ]
            ok, output = self.env.run_pip(args)
            if ok:
                elapsed = time.monotonic() - start
                return InstallResult(
                    package=package,
                    version=cached_wheel.version,
                    success=True,
                    from_cache=True,
                    elapsed_seconds=elapsed,
                )
            logger.debug(f"Wheelhouse install failed for {package}, trying online")

        if offline or self.config.offline_mode:
            elapsed = time.monotonic() - start
            return InstallResult(
                package=package,
                version="",
                success=False,
                error="Package not in wheelhouse and offline mode is enabled",
                elapsed_seconds=elapsed,
            )

        # ── 2. Install from PyPI with fallbacks ────────────────────────────────
        return self._install_online(package_spec, package, start, upgrade)

    def _install_online(
        self,
        package_spec: str,
        package_name: str,
        start: float,
        upgrade: bool = False,
    ) -> InstallResult:
        """Install from PyPI using index args and retry logic."""
        index_args = self.repo.build_pip_index_args()

        for attempt in range(self.config.repository.max_retries):
            args = [
                "install",
                package_spec,
                "--prefer-binary",
                "--disable-pip-version-check",
            ]
            if upgrade:
                args.append("--upgrade")
            args.extend(index_args)

            ok, output = self.env.run_pip(args, timeout=300)
            elapsed = time.monotonic() - start

            if ok:
                # Try to find installed version
                version = self._get_installed_version(package_name)
                return InstallResult(
                    package=package_name,
                    version=version,
                    success=True,
                    from_cache=False,
                    elapsed_seconds=elapsed,
                )

            if attempt < self.config.repository.max_retries - 1:
                wait = 2**attempt
                logger.warning(
                    f"Install attempt {attempt + 1} failed for {package_name}. "
                    f"Retrying in {wait}s..."
                )
                logger.debug(f"Pip error output: {output}")
                time.sleep(wait)

        elapsed = time.monotonic() - start
        return InstallResult(
            package=package_name,
            version="",
            success=False,
            error=(
                f"Failed after {self.config.repository.max_retries} attempts. "
                f"Last error: {output.strip()}"
            ),
            elapsed_seconds=elapsed,
        )

    def uninstall(self, package: str) -> InstallResult:
        """Uninstall a package from the virtual environment."""
        if not validate_package_name(package):
            return InstallResult(
                package=package,
                version="",
                success=False,
                error=f"Invalid package name: {package!r}",
            )

        version = self._get_installed_version(package) or "?"
        ok, output = self.env.run_pip(["uninstall", "-y", package])
        return InstallResult(
            package=package,
            version=version,
            success=ok,
            error=None if ok else output,
        )

    def install_requirements(
        self,
        requirements_file: Path,
        offline: bool = False,
    ) -> list[InstallResult]:
        """
        Install all packages from a requirements file.
        Returns one InstallResult per package.
        """
        from ppm.parsers import parse_requirements

        requirements = parse_requirements(requirements_file)
        results: list[InstallResult] = []

        for req in requirements:
            if req.url:
                # Direct URL install
                ok, output = self.env.run_pip(["install", req.url])
                results.append(
                    InstallResult(
                        package=req.url,
                        version="?",
                        success=ok,
                        error=None if ok else output,
                    )
                )
            else:
                result = self.install(
                    req.name,
                    req.version_spec,
                    offline=offline,
                )
                results.append(result)

        return results

    def _get_installed_version(self, package: str) -> str:
        """Get installed version of a package, empty string if not found."""
        version = self.env.is_package_installed(package)
        return version or ""
