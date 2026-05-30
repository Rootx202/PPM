"""Security and validation utilities."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

# ─── Package name validation ─────────────────────────────────────────────────

# Per PEP 508 / PyPI naming conventions
_PACKAGE_NAME_RE = re.compile(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE)
_VERSION_SPEC_RE = re.compile(r"^[a-zA-Z0-9_.!<>=,\[\]*+-]+$")
_SAFE_EXTRA_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_package_name(name: str) -> bool:
    """Validate a PyPI package name. Returns True if valid."""
    if not name or len(name) > 200:
        return False
    return bool(_PACKAGE_NAME_RE.match(name))


def validate_version_spec(spec: str) -> bool:
    """Validate a version specifier string."""
    if not spec:
        return True  # empty is valid (no constraint)
    return bool(_VERSION_SPEC_RE.match(spec))


def sanitize_package_name(name: str) -> str:
    """Normalize package name per PEP 508 (replace [-_.] with -)."""
    return re.sub(r"[-_.]+", "-", name).lower()


# ─── URL validation ───────────────────────────────────────────────────────────

_ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url: str) -> bool:
    """Validate that a URL is safe and well-formed."""
    try:
        parsed = urlparse(url)
        is_valid = parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)
        if is_valid and parsed.scheme == "http":
            from ppm.utils.console import warning
            warning(f"Insecure HTTP URL detected: {url}. HTTPS is recommended for security.")
        return is_valid
    except Exception:
        return False


def validate_pypi_url(url: str) -> bool:
    """Check that a URL looks like a PyPI-compatible index."""
    if not validate_url(url):
        return False
    # Ensure it ends with /simple or /simple/
    return "/simple" in url or url.endswith("/")


# ─── Path safety ──────────────────────────────────────────────────────────────

def safe_path(path: Path, base: Path) -> bool:
    """Ensure path is within the base directory (prevent path traversal)."""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def ensure_safe_dir(path: Path) -> Path:
    """Create directory safely, ensuring it doesn't already exist as a file."""
    if path.exists() and not path.is_dir():
        raise ValueError(f"Path exists but is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─── Subprocess safety ────────────────────────────────────────────────────────

def safe_subprocess_args(args: list[str]) -> list[str]:
    """
    Validate subprocess arguments to prevent injection.
    Each arg must be a non-empty string without shell-special characters.
    """
    dangerous_chars = set("|;&$`<>\n\r\t")
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(f"Subprocess arg must be str, got: {type(arg)}")
        if any(c in arg for c in dangerous_chars):
            raise ValueError(f"Potentially dangerous character in arg: {arg!r}")
    return args


def run_safe(
    args: list[str],
    cwd: Path | None = None,
    capture: bool = True,
    timeout: int = 120,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess safely without shell=True.
    Raises RuntimeError on non-zero exit.
    """
    validated = safe_subprocess_args(args)
    result = subprocess.run(
        validated,
        cwd=cwd,
        capture_output=capture,
        text=True,
        timeout=timeout,
        env=env,
        shell=False,  # Never use shell=True
    )
    return result
