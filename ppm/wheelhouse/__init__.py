"""Wheelhouse cache management: store, retrieve, and manage .whl files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from ppm.config import WheelhouseConfig
from ppm.models import WheelEntry, WheelhouseStats
from ppm.utils.console import get_logger
from ppm.utils.security import ensure_safe_dir, safe_path

logger = get_logger(__name__)

# Wheel filename pattern: {name}-{version}(-{build})?-{python}-{abi}-{platform}.whl
_WHEEL_FILENAME_RE = re.compile(
    r"^(?P<name>[^-]+)-(?P<version>[^-]+)(-(?P<build>[^-]+))?-"
    r"(?P<python>[^-]+)-(?P<abi>[^-]+)-(?P<platform>[^-]+)\.whl$"
)


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class WheelhouseManager:
    """
    Manages a local directory of cached .whl files.

    Provides:
    - Storage and deduplication of wheel files
    - Offline-install support via --find-links
    - Cache statistics and cleanup
    """

    def __init__(self, config: WheelhouseConfig) -> None:
        self.config = config
        self.path = config.path
        ensure_safe_dir(self.path)

    # ─── Core operations ──────────────────────────────────────────────────────

    def list_wheels(self) -> list[WheelEntry]:
        """List all wheel files currently in the wheelhouse."""
        entries: list[WheelEntry] = []
        for whl_file in self.path.glob("*.whl"):
            entry = self._parse_wheel_file(whl_file)
            if entry:
                entries.append(entry)
        return sorted(entries, key=lambda e: (e.package_name, e.version))

    def get_stats(self) -> WheelhouseStats:
        """Compute statistics for the wheelhouse."""
        wheels = self.list_wheels()
        unique_packages = {e.package_name for e in wheels}
        total_size = sum(e.file_size for e in wheels)
        return WheelhouseStats(
            total_wheels=len(wheels),
            total_size_bytes=total_size,
            unique_packages=len(unique_packages),
            packages=sorted(unique_packages),
        )

    def find_wheel(self, package_name: str, version: Optional[str] = None) -> Optional[WheelEntry]:
        """
        Search for a cached wheel matching the given package name and optional version.
        Normalizes package name for comparison.
        """
        normalized = _normalize_name(package_name)
        for wheel in self.list_wheels():
            if _normalize_name(wheel.package_name) == normalized:
                if version is None or wheel.version == version:
                    return wheel
        return None

    def add_wheel(self, source_path: Path) -> Optional[WheelEntry]:
        """
        Copy a wheel file into the wheelhouse.
        Returns the wheel entry if successful, None on failure.
        """
        if not source_path.exists() or not source_path.suffix == ".whl":
            logger.warning(f"Not a valid .whl file: {source_path}")
            return None

        dest = self.path / source_path.name

        # Deduplication: skip if already present with same hash
        if self.config.deduplicate and dest.exists():
            if _sha256(dest) == _sha256(source_path):
                logger.debug(f"Wheel already cached (identical): {source_path.name}")
                return self._parse_wheel_file(dest)

        import shutil
        shutil.copy2(source_path, dest)
        logger.info(f"Cached wheel: {dest.name}")
        return self._parse_wheel_file(dest)

    def remove_wheel(self, package_name: str, version: Optional[str] = None) -> int:
        """
        Remove wheel(s) matching package_name (and optionally version).
        Returns number of files removed.
        """
        count = 0
        normalized = _normalize_name(package_name)
        for wheel in self.list_wheels():
            if _normalize_name(wheel.package_name) != normalized:
                continue
            if version and wheel.version != version:
                continue
            if safe_path(wheel.file_path, self.path):
                wheel.file_path.unlink()
                count += 1
                logger.info(f"Removed cached wheel: {wheel.filename}")
        return count

    def clean(self, keep_latest: bool = True) -> int:
        """
        Clean the wheelhouse.
        If keep_latest=True, removes all but the latest version per package.
        Returns number of files removed.
        """
        wheels = self.list_wheels()
        removed = 0

        if keep_latest:
            from packaging.version import Version

            # Group by package name
            grouped: dict[str, list[WheelEntry]] = {}
            for w in wheels:
                normalized = _normalize_name(w.package_name)
                grouped.setdefault(normalized, []).append(w)

            for pkg_wheels in grouped.values():
                try:
                    sorted_wheels = sorted(
                        pkg_wheels, key=lambda w: Version(w.version), reverse=True
                    )
                except Exception:
                    sorted_wheels = pkg_wheels

                # Keep only the latest
                for old_wheel in sorted_wheels[1:]:
                    if safe_path(old_wheel.file_path, self.path):
                        old_wheel.file_path.unlink()
                        removed += 1
        else:
            # Remove all wheels
            for w in wheels:
                if safe_path(w.file_path, self.path):
                    w.file_path.unlink()
                    removed += 1

        return removed

    def build_from_requirements(
        self,
        requirements_file: Path,
        python_executable: Path,
        index_args: list[str],
    ) -> tuple[int, list[str]]:
        """
        Download wheels from PyPI for all packages in requirements_file
        and store them in the wheelhouse.
        Returns (count, errors).
        """
        from ppm.utils.security import run_safe

        errors: list[str] = []
        try:
            result = run_safe(
                [
                    str(python_executable),
                    "-m",
                    "pip",
                    "download",
                    "-r",
                    str(requirements_file),
                    "-d",
                    str(self.path),
                    "--prefer-binary",
                ]
                + index_args,
                timeout=600,
            )
            if result.returncode != 0:
                errors.append(result.stderr)
                return 0, errors
        except Exception as e:
            errors.append(str(e))
            return 0, errors

        count = sum(1 for _ in self.path.glob("*.whl"))
        return count, errors

    def get_find_links_arg(self) -> list[str]:
        """Return pip --find-links argument pointing to wheelhouse."""
        return ["--find-links", str(self.path)]

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _parse_wheel_file(self, path: Path) -> Optional[WheelEntry]:
        """Parse a wheel filename into a WheelEntry."""
        m = _WHEEL_FILENAME_RE.match(path.name)
        if not m:
            return None
        return WheelEntry(
            package_name=m.group("name").replace("_", "-"),
            version=m.group("version"),
            python_tag=m.group("python"),
            abi_tag=m.group("abi"),
            platform_tag=m.group("platform"),
            file_path=path,
            file_size=path.stat().st_size,
        )


def _normalize_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()
