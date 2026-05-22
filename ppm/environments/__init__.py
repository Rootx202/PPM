"""Virtual environment detection, creation, and management."""

from __future__ import annotations

import platform
import shutil
import sys
import venv
from pathlib import Path
from typing import Optional

from ppm.models import EnvironmentInfo, OSType
from ppm.utils.console import get_logger
from ppm.utils.security import run_safe

logger = get_logger(__name__)


def detect_os() -> OSType:
    """Detect the current operating system."""
    system = platform.system().lower()
    if system == "linux":
        return OSType.LINUX
    if system == "windows":
        return OSType.WINDOWS
    if system == "darwin":
        return OSType.MACOS
    return OSType.UNKNOWN


def get_python_executable(venv_path: Path, os_type: OSType) -> Path:
    """Return the path to the Python executable inside a venv."""
    if os_type == OSType.WINDOWS:
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def get_pip_executable(venv_path: Path, os_type: OSType) -> Path:
    """Return the path to pip inside a venv."""
    if os_type == OSType.WINDOWS:
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


class EnvironmentManager:
    """Manages virtual environment lifecycle operations."""

    def __init__(self, project_dir: Path, venv_name: str = ".venv") -> None:
        self.project_dir = project_dir
        self.venv_name = venv_name
        self.os_type = detect_os()

    @property
    def venv_path(self) -> Path:
        return self.project_dir / self.venv_name

    @property
    def python(self) -> Path:
        return get_python_executable(self.venv_path, self.os_type)

    @property
    def pip(self) -> Path:
        return get_pip_executable(self.venv_path, self.os_type)

    def exists(self) -> bool:
        """Check if the virtual environment already exists and is valid."""
        return self.python.exists()

    def create(self, upgrade_pip: bool = True) -> EnvironmentInfo:
        """
        Create a new virtual environment at self.venv_path.
        Raises RuntimeError if creation fails.
        """
        if self.exists():
            raise FileExistsError(
                f"Virtual environment already exists at {self.venv_path}"
            )

        logger.debug(f"Creating venv at {self.venv_path}")
        builder = venv.EnvBuilder(
            system_site_packages=False,
            clear=False,
            symlinks=(self.os_type != OSType.WINDOWS),
            upgrade=False,
            with_pip=True,
        )
        builder.create(str(self.venv_path))

        if upgrade_pip:
            try:
                run_safe(
                    [str(self.python), "-m", "pip", "install", "--upgrade", "pip"],
                    capture=True,
                    timeout=60,
                )
            except Exception as e:
                logger.warning(f"pip upgrade failed (non-fatal): {e}")

        return self.get_info()

    def remove(self) -> None:
        """Delete the virtual environment directory."""
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path)
            logger.info(f"Removed venv: {self.venv_path}")

    def get_info(self) -> EnvironmentInfo:
        """Gather metadata about the current virtual environment."""
        if not self.exists():
            raise RuntimeError(f"No virtual environment found at {self.venv_path}")

        # Determine Python version
        python_version = "unknown"
        pip_version = "unknown"
        packages_count = 0

        try:
            result = run_safe([str(self.python), "--version"], capture=True)
            python_version = result.stdout.strip().replace("Python ", "")
        except Exception:
            pass

        try:
            result = run_safe([str(self.pip), "--version"], capture=True)
            pip_version = result.stdout.split()[1]
        except Exception:
            pass

        try:
            result = run_safe(
                [str(self.pip), "list", "--format=json"],
                capture=True,
            )
            import json
            packages_count = len(json.loads(result.stdout))
        except Exception:
            pass

        # Detect if this venv is active
        active_venv = Path(sys.prefix)
        is_active = self.venv_path.resolve() == active_venv.resolve()

        return EnvironmentInfo(
            path=self.venv_path,
            python_version=python_version,
            python_executable=self.python,
            pip_version=pip_version,
            os_type=self.os_type,
            is_active=is_active,
            packages_count=packages_count,
        )

    def activation_command(self) -> str:
        """Return the shell command to activate this venv."""
        if self.os_type == OSType.WINDOWS:
            return rf"{self.venv_path}\Scripts\activate"
        return f"source {self.venv_path}/bin/activate"

    def run_pip(self, args: list[str], timeout: int = 300) -> tuple[bool, str]:
        """
        Execute pip with the given args inside this venv.
        Returns (success: bool, output: str).
        """
        if not self.exists():
            return False, "Virtual environment not found"

        try:
            result = run_safe(
                [str(self.pip)] + args,
                capture=True,
                timeout=timeout,
            )
            ok = result.returncode == 0
            output = result.stdout if ok else result.stderr
            return ok, output
        except Exception as e:
            return False, str(e)

    def list_packages(self) -> list[dict]:
        """Return list of installed packages as dicts with name/version."""
        try:
            result = run_safe(
                [str(self.pip), "list", "--format=json"],
                capture=True,
            )
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        except Exception:
            pass
        return []

    def is_package_installed(self, package_name: str) -> Optional[str]:
        """Check if a package is installed; return version string or None."""
        packages = self.list_packages()
        name_lower = package_name.lower().replace("-", "_")
        for pkg in packages:
            if pkg["name"].lower().replace("-", "_") == name_lower:
                return pkg["version"]
        return None
