"""Requirements file parser with full PEP 508 support."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ppm.models import Requirement
from ppm.utils.console import get_logger

logger = get_logger(__name__)


def parse_requirements(file_path: Path) -> list[Requirement]:
    """
    Parse a requirements.txt file and return a list of Requirement objects.
    Handles:
    - Version specifiers
    - Extras
    - Environment markers
    - Comments and blank lines
    - -r / --requirement includes
    - Direct URL installs
    - Editable installs (-e)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Requirements file not found: {file_path}")

    requirements: list[Requirement] = []
    seen_files: set[Path] = {file_path.resolve()}

    _parse_file(file_path, requirements, seen_files)
    return requirements


def _parse_file(
    file_path: Path,
    requirements: list[Requirement],
    seen_files: set[Path],
) -> None:
    """Recursively parse a requirements file, resolving -r includes."""
    try:
        import requirements as req_parser  # requirements-parser library
    except ImportError:
        # Fallback: manual parse
        _parse_file_manual(file_path, requirements, seen_files)
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            for req in req_parser.parse(f):
                if req.name:
                    requirements.append(
                        Requirement(
                            name=req.name,
                            version_spec="".join(
                                f"{s[0]}{s[1]}" for s in (req.specs or [])
                            ),
                            extras=list(req.extras or []),
                            marker=str(req.marker) if req.marker else "",
                            url=req.uri or "",
                            editable=req.editable,
                            raw_line=req.line or "",
                        )
                    )
    except Exception as e:
        logger.warning(f"requirements-parser failed, using fallback: {e}")
        _parse_file_manual(file_path, requirements, seen_files)


def _parse_file_manual(
    file_path: Path,
    requirements: list[Requirement],
    seen_files: set[Path],
) -> None:
    """Manual fallback parser for requirements.txt."""
    import re

    specifier_re = re.compile(r"([a-zA-Z0-9_.-]+)(\[.*?\])?(.*)")

    with open(file_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle -r / --requirement includes
            if line.startswith(("-r ", "--requirement ")):
                include_path = Path(line.split(None, 1)[1].strip())
                if not include_path.is_absolute():
                    include_path = file_path.parent / include_path
                include_path = include_path.resolve()
                if include_path not in seen_files:
                    seen_files.add(include_path)
                    _parse_file_manual(include_path, requirements, seen_files)
                continue

            # Handle -e / --editable
            editable = False
            if line.startswith(("-e ", "--editable ")):
                editable = True
                line = line.split(None, 1)[1].strip()

            # Strip inline comments
            if " #" in line:
                line = line[: line.index(" #")].strip()

            # Direct URL installs
            if "://" in line or line.startswith("git+"):
                requirements.append(
                    Requirement(url=line, editable=editable, raw_line=raw_line.rstrip())
                )
                continue

            # Strip environment markers
            marker = ""
            if ";" in line:
                line, marker = line.split(";", 1)
                line = line.strip()
                marker = marker.strip()

            # Extract extras
            extras: list[str] = []
            extras_match = re.search(r"\[([^\]]+)\]", line)
            if extras_match:
                extras = [e.strip() for e in extras_match.group(1).split(",")]
                line = line[: extras_match.start()] + line[extras_match.end() :]

            # Extract name and version spec
            m = specifier_re.match(line)
            if not m:
                logger.debug(f"Could not parse requirement: {raw_line.rstrip()!r}")
                continue

            name = m.group(1).strip()
            version_spec = m.group(3).strip() if m.group(3) else ""

            requirements.append(
                Requirement(
                    name=name,
                    version_spec=version_spec,
                    extras=extras,
                    marker=marker,
                    editable=editable,
                    raw_line=raw_line.rstrip(),
                )
            )


def write_requirements(requirements: list[Requirement], file_path: Path) -> None:
    """Write requirements back to a file in canonical format."""
    lines = []
    for req in requirements:
        if req.url:
            prefix = "-e " if req.editable else ""
            lines.append(f"{prefix}{req.url}")
        else:
            extras = f"[{','.join(req.extras)}]" if req.extras else ""
            marker = f"; {req.marker}" if req.marker else ""
            lines.append(f"{req.name}{extras}{req.version_spec}{marker}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def generate_lock_metadata(requirements: list[Requirement], pip_executable: Path) -> dict:
    """
    Generate a lock metadata dict recording resolved versions.
    Runs pip freeze inside the active venv to capture exact pinned versions.
    """
    from ppm.utils.security import run_safe

    pinned: dict[str, str] = {}
    try:
        result = run_safe([str(pip_executable), "freeze"], capture=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if "==" in line:
                    name, version = line.split("==", 1)
                    pinned[name.strip().lower()] = version.strip()
    except Exception as e:
        logger.warning(f"pip freeze failed: {e}")

    return {
        "generated_at": _iso_now(),
        "requirements": [str(r) for r in requirements],
        "pinned": pinned,
    }


def _iso_now() -> str:
    """Return current UTC time in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
