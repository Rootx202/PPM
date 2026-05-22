"""Data models for PPM."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class OSType(str, Enum):
    """Operating system types."""
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


class PackageStatus(str, Enum):
    """Package installation status."""
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    OUTDATED = "outdated"
    BROKEN = "broken"
    CACHED = "cached"


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RepositoryStatus(str, Enum):
    """Repository reachability status."""
    ONLINE = "online"
    OFFLINE = "offline"
    SLOW = "slow"
    UNKNOWN = "unknown"


@dataclass
class PackageInfo:
    """Represents a Python package."""
    name: str
    version: str
    description: str = ""
    homepage: str = ""
    author: str = ""
    license: str = ""
    requires: list[str] = field(default_factory=list)
    status: PackageStatus = PackageStatus.NOT_INSTALLED

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


@dataclass
class Requirement:
    """A parsed package requirement."""
    name: str
    version_spec: str = ""   # e.g. ">=1.0,<2.0"
    extras: list[str] = field(default_factory=list)
    marker: str = ""         # PEP 508 marker
    url: str = ""            # Direct URL installs
    editable: bool = False
    raw_line: str = ""

    def __str__(self) -> str:
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{self.name}{extras_str}{self.version_spec}"


@dataclass
class Vulnerability:
    """A security vulnerability finding."""
    package_name: str
    installed_version: str
    vulnerability_id: str
    severity: VulnerabilitySeverity
    description: str
    fix_versions: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    url: str = ""


@dataclass
class AuditReport:
    """Security audit results."""
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    scanned_packages: int = 0
    vulnerable_packages: int = 0
    error: Optional[str] = None

    @property
    def is_clean(self) -> bool:
        return len(self.vulnerabilities) == 0


@dataclass
class WheelEntry:
    """A cached wheel file entry."""
    package_name: str
    version: str
    python_tag: str
    abi_tag: str
    platform_tag: str
    file_path: Path
    file_size: int = 0
    sha256: str = ""

    @property
    def filename(self) -> str:
        return self.file_path.name


@dataclass
class WheelhouseStats:
    """Wheelhouse cache statistics."""
    total_wheels: int = 0
    total_size_bytes: int = 0
    unique_packages: int = 0
    packages: list[str] = field(default_factory=list)

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)


@dataclass
class Repository:
    """A PyPI-compatible package repository."""
    name: str
    url: str
    priority: int = 0
    status: RepositoryStatus = RepositoryStatus.UNKNOWN
    response_time_ms: float = 0.0
    trusted: bool = False


@dataclass
class InstallResult:
    """Result of a package installation operation."""
    package: str
    version: str
    success: bool
    from_cache: bool = False
    error: Optional[str] = None
    elapsed_seconds: float = 0.0


@dataclass
class SyncResult:
    """Result of requirements.txt sync operation."""
    installed: list[str] = field(default_factory=list)
    already_satisfied: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    total: int = 0

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


@dataclass
class EnvironmentInfo:
    """Virtual environment metadata."""
    path: Path
    python_version: str
    python_executable: Path
    pip_version: str
    os_type: OSType
    is_active: bool = False
    packages_count: int = 0

    @property
    def activate_command(self) -> str:
        if self.os_type == OSType.WINDOWS:
            return rf"{self.path}\Scripts\activate"
        return f"source {self.path}/bin/activate"


@dataclass
class DoctorCheck:
    """A single doctor health check result."""
    name: str
    passed: bool
    message: str
    suggestion: Optional[str] = None


@dataclass
class DoctorReport:
    """Full doctor diagnostic report."""
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[DoctorCheck]:
        return [c for c in self.checks if not c.passed]
