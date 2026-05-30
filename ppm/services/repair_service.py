"""Repair service: fix broken environments and dependency conflicts."""

from __future__ import annotations

from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.utils.console import get_logger
from ppm.utils.security import run_safe

logger = get_logger(__name__)


class RepairService:
    """Repairs broken virtual environments and dependency conflicts."""

    def __init__(self, config: PPMConfig, env_manager: EnvironmentManager) -> None:
        self.config = config
        self.env = env_manager

    def repair(self, requirements_file: Path | None = None) -> list[str]:
        """
        Attempt to repair the environment.

        Steps:
        1. Upgrade pip and setuptools
        2. Remove conflicting packages
        3. Reinstall from requirements.txt if provided
        4. Clean pip cache

        Returns list of repair actions taken.
        """
        actions: list[str] = []

        if not self.env.exists():
            raise RuntimeError("No virtual environment found. Run 'ppm init' first.")

        # ── Step 1: Upgrade pip, setuptools, wheel ─────────────────────────────
        logger.info("Upgrading pip, setuptools, wheel...")
        ok, output = self.env.run_pip(["install", "--upgrade", "pip", "setuptools", "wheel"])
        if ok:
            actions.append("✅ Upgraded pip, setuptools, wheel")
        else:
            actions.append(f"⚠️  pip upgrade failed: {output[:200]}")

        # ── Step 2: Check for conflicts ────────────────────────────────────────
        logger.info("Checking for dependency conflicts...")
        conflicts = self._find_conflicts()
        if conflicts:
            actions.append(f"⚠️  Found conflicts: {', '.join(conflicts)}")
            # Try to reinstall conflicting packages
            for pkg in conflicts:
                ok, _ = self.env.run_pip(["install", "--force-reinstall", "--no-deps", pkg])
                if ok:
                    actions.append(f"✅ Force-reinstalled: {pkg}")
                else:
                    actions.append(f"❌ Could not fix: {pkg}")
        else:
            actions.append("✅ No dependency conflicts found")

        # ── Step 3: Reinstall from requirements.txt ────────────────────────────
        if requirements_file and requirements_file.exists():
            logger.info("Reinstalling from requirements.txt...")
            ok, output = self.env.run_pip(["install", "-r", str(requirements_file), "--upgrade"])
            if ok:
                actions.append("✅ Reinstalled requirements.txt packages")
            else:
                actions.append(f"❌ Requirements reinstall failed: {output[:200]}")

        # ── Step 4: Clean pip cache ────────────────────────────────────────────
        logger.info("Cleaning pip cache...")
        ok, _ = self.env.run_pip(["cache", "purge"])
        if ok:
            actions.append("✅ Cleaned pip cache")
        else:
            actions.append("ℹ️  pip cache clean skipped (older pip version)")

        return actions

    def _find_conflicts(self) -> list[str]:
        """
        Run pip check to find dependency conflicts.
        Returns list of package names with issues.
        """
        result = run_safe(
            [str(self.env.pip), "check"],
            capture=True,
            timeout=60,
        )
        if result.returncode == 0:
            return []

        # Parse output like: "package X Y requires package Z, but Z W is installed"
        import re

        conflicts: list[str] = []
        for line in result.stdout.splitlines():
            m = re.match(r"^([a-zA-Z0-9_-]+)\s", line)
            if m:
                conflicts.append(m.group(1))

        return list(set(conflicts))

    def clean_cache(self) -> list[str]:
        """Clean pip cache and PPM wheelhouse duplicates."""
        actions: list[str] = []

        ok, _ = self.env.run_pip(["cache", "purge"])
        actions.append("✅ Cleaned pip cache" if ok else "⚠️  pip cache purge skipped")

        return actions
