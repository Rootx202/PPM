"""Environment service: creates, destroys, and inspects virtual environments."""

from __future__ import annotations

from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.models import EnvironmentInfo
from ppm.utils.console import get_logger

logger = get_logger(__name__)


class EnvironmentService:
    """Orchestrates virtual environment creation and inspection."""

    def __init__(self, config: PPMConfig, project_dir: Path) -> None:
        self.config = config
        self.project_dir = project_dir
        self.manager = EnvironmentManager(project_dir, config.venv_name)

    def init(self, force: bool = False) -> EnvironmentInfo:
        """
        Initialize a new virtual environment.

        Args:
            force: If True, delete existing venv before creating.
        """
        if self.manager.exists():
            if not force:
                raise FileExistsError(
                    f"Virtual environment already exists at {self.manager.venv_path}. "
                    "Use --force to recreate it."
                )
            logger.info("Removing existing virtual environment...")
            self.manager.remove()

        logger.info(f"Creating virtual environment at {self.manager.venv_path}")
        return self.manager.create(upgrade_pip=True)

    def get_info(self) -> EnvironmentInfo:
        """Return metadata about the current virtual environment."""
        return self.manager.get_info()

    def activation_command(self) -> str:
        return self.manager.activation_command()

    def exists(self) -> bool:
        return self.manager.exists()

    def require_env(self) -> None:
        """Raise RuntimeError if no venv exists in the project directory."""
        if not self.manager.exists():
            raise RuntimeError(
                f"No virtual environment found at {self.manager.venv_path}. "
                "Run 'ppm init' first."
            )
