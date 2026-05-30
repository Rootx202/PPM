"""Wheelhouse service: manages cached wheel files."""

from __future__ import annotations

from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.models import WheelhouseStats
from ppm.repositories import RepositoryManager
from ppm.utils.console import get_logger
from ppm.wheelhouse import WheelhouseManager

logger = get_logger(__name__)


class WheelhouseService:
    """Provides wheelhouse build, list, clean, and stats operations."""

    def __init__(
        self,
        config: PPMConfig,
        wheelhouse: WheelhouseManager,
        env_manager: EnvironmentManager,
        repo_manager: RepositoryManager,
    ) -> None:
        self.config = config
        self.wheelhouse = wheelhouse
        self.env = env_manager
        self.repo = repo_manager

    def build(self, requirements_file: Path) -> tuple[int, list[str]]:
        """
        Download wheels for all packages in requirements.txt into the wheelhouse.
        Returns (count of wheels, error messages).
        """
        if not requirements_file.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_file}")

        index_args = self.repo.build_pip_index_args()
        return self.wheelhouse.build_from_requirements(
            requirements_file=requirements_file,
            python_executable=self.env.python,
            index_args=index_args,
        )

    def get_stats(self) -> WheelhouseStats:
        """Return wheelhouse statistics."""
        return self.wheelhouse.get_stats()

    def clean(self, keep_latest: bool = True) -> int:
        """Clean old wheels from the wheelhouse. Returns removed count."""
        return self.wheelhouse.clean(keep_latest=keep_latest)

    def list_wheels(self) -> list:
        """Return all wheel entries in the wheelhouse."""
        return self.wheelhouse.list_wheels()
