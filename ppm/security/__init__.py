"""Security audit module: vulnerability scanning via pip-audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ppm.models import AuditReport, Vulnerability, VulnerabilitySeverity
from ppm.utils.console import get_logger
from ppm.utils.security import run_safe

logger = get_logger(__name__)

# Severity mapping from pip-audit output
_SEVERITY_MAP: dict[str, VulnerabilitySeverity] = {
    "critical": VulnerabilitySeverity.CRITICAL,
    "high": VulnerabilitySeverity.HIGH,
    "medium": VulnerabilitySeverity.MEDIUM,
    "low": VulnerabilitySeverity.LOW,
}


def run_audit(
    pip_executable: Path,
    requirements_file: Path | None = None,
) -> AuditReport:
    """
    Execute pip-audit against the current environment or a requirements file.

    Args:
        pip_executable: Path to pip inside the virtual environment.
        requirements_file: Optional path to requirements.txt (audits file instead of env).

    Returns:
        AuditReport with all found vulnerabilities.
    """
    # Determine pip-audit executable path (co-located with pip)
    pip_audit = _find_pip_audit(pip_executable)
    if not pip_audit:
        return AuditReport(error="pip-audit not found. Install it with: pip install pip-audit")

    cmd = [str(pip_audit), "--format", "json", "--progress-spinner", "off"]

    if requirements_file and requirements_file.exists():
        cmd += ["-r", str(requirements_file)]

    try:
        result = run_safe(
            cmd,
            capture=True,
            timeout=120,
        )
        output = result.stdout or result.stderr
        return _parse_pip_audit_output(output)
    except subprocess.TimeoutExpired:
        return AuditReport(error="Audit timed out after 120 seconds")
    except FileNotFoundError:
        return AuditReport(error="pip-audit executable not found")
    except Exception as e:
        return AuditReport(error=f"Audit failed: {e}")


def _find_pip_audit(pip_executable: Path) -> Path | None:
    """Locate pip-audit in the same venv bin directory as pip."""
    import shutil

    bin_dir = pip_executable.parent
    candidates = [
        bin_dir / "pip-audit",
        bin_dir / "pip-audit.exe",
        Path(shutil.which("pip-audit") or ""),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _parse_pip_audit_output(output: str) -> AuditReport:
    """Parse JSON output from pip-audit into an AuditReport."""
    vulnerabilities: list[Vulnerability] = []
    scanned_packages = 0

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        # Possibly an error message
        if output.strip():
            return AuditReport(error=output.strip()[:500])
        return AuditReport(error="Empty response from pip-audit")

    # pip-audit JSON format: {"dependencies": [...], "fixes": [...]}
    dependencies = data.get("dependencies", [])
    scanned_packages = len(dependencies)

    for dep in dependencies:
        name = dep.get("name", "unknown")
        installed_version = dep.get("version", "unknown")
        vulns = dep.get("vulns", [])

        for vuln in vulns:
            vuln_id = vuln.get("id", "UNKNOWN")
            description = vuln.get("description", "No description available")
            fix_versions = vuln.get("fix_versions", [])
            aliases = vuln.get("aliases", [])

            # Attempt severity extraction from aliases (OSV/GHSA)
            severity = _infer_severity(vuln_id, aliases)

            vulnerabilities.append(
                Vulnerability(
                    package_name=name,
                    installed_version=installed_version,
                    vulnerability_id=vuln_id,
                    severity=severity,
                    description=description,
                    fix_versions=fix_versions,
                    aliases=aliases,
                )
            )

    return AuditReport(
        vulnerabilities=vulnerabilities,
        scanned_packages=scanned_packages,
        vulnerable_packages=len({v.package_name for v in vulnerabilities}),
    )


def _infer_severity(vuln_id: str, aliases: list[str]) -> VulnerabilitySeverity:
    """
    Infer severity from vulnerability ID prefix.
    GHSA IDs don't embed severity; fall back to UNKNOWN.
    CVE-based IDs: use heuristic.
    """
    for alias in [vuln_id] + aliases:
        alias_lower = alias.lower()
        for severity_str, severity_enum in _SEVERITY_MAP.items():
            if severity_str in alias_lower:
                return severity_enum
    return VulnerabilitySeverity.UNKNOWN


def check_deprecated_packages(packages: list[dict]) -> list[dict]:
    """
    Check for known deprecated or unmaintained packages.
    Returns list of dicts with package name and reason.
    """
    # Well-known deprecated packages
    deprecated_packages: dict[str, str] = {
        "distribute": "Replaced by setuptools",
        "nose": "Use pytest instead",
        "mock": "Included in unittest.mock since Python 3.3",
        "futures": "Built-in in Python 3 as concurrent.futures",
        "urllib3": "Ensure version >= 2.0 for security fixes",
        "requests": "Ensure version >= 2.31.0 for security fixes",
        "pycrypto": "Unmaintained; use pycryptodome",
        "pyOpenSSL": "Ensure version >= 23.2.0",
        "cryptography": "Ensure version >= 41.0 for recent fixes",
        "pillow": "Ensure version >= 10.0 for security fixes",
        "django": "Ensure you are on a supported LTS version",
    }

    results = []
    for pkg in packages:
        name = pkg.get("name", "").lower()
        if name in deprecated_packages:
            results.append(
                {
                    "package": pkg["name"],
                    "version": pkg.get("version", "?"),
                    "warning": deprecated_packages[name],
                }
            )
    return results
