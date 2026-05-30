"""Configuration management for PPM."""

from __future__ import annotations

import os
import tomllib  # type: ignore[no-redef]
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir, user_data_dir

# Default PPM home directory
PPM_HOME = Path(user_data_dir("ppm", "ppm"))
PPM_CONFIG_DIR = Path(user_config_dir("ppm", "ppm"))
PPM_CONFIG_FILE = PPM_CONFIG_DIR / "config.toml"
PPM_WHEELHOUSE_DEFAULT = PPM_HOME / "wheelhouse"
PPM_CACHE_DIR = PPM_HOME / "cache"
PPM_LOG_DIR = PPM_HOME / "logs"

DEFAULT_INDEX_URL = "https://pypi.org/simple"
DEFAULT_MIRRORS = [
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
]


@dataclass
class RepositoryConfig:
    """Repository configuration."""

    index_url: str = DEFAULT_INDEX_URL
    mirrors: list[str] = field(default_factory=lambda: list(DEFAULT_MIRRORS))
    timeout: int = 30
    max_retries: int = 3
    trusted_hosts: list[str] = field(default_factory=list)


@dataclass
class WheelhouseConfig:
    """Wheelhouse (cache) configuration."""

    path: Path = field(default_factory=lambda: PPM_WHEELHOUSE_DEFAULT)
    max_size_gb: float = 5.0
    auto_clean: bool = False
    deduplicate: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    log_file: Path | None = None
    enable_rich: bool = True


@dataclass
class PPMConfig:
    """Root configuration object."""

    repository: RepositoryConfig = field(default_factory=RepositoryConfig)
    wheelhouse: WheelhouseConfig = field(default_factory=WheelhouseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    offline_mode: bool = False
    venv_name: str = ".venv"

    @classmethod
    def load(cls) -> PPMConfig:
        """Load configuration from disk, falling back to defaults."""
        config = cls()

        # Apply environment variable overrides first
        config._apply_env_overrides()

        # Load from file if it exists
        if PPM_CONFIG_FILE.exists():
            try:
                with open(PPM_CONFIG_FILE, "rb") as f:
                    data = tomllib.load(f)
                config._from_dict(data)
            except Exception:
                pass  # Use defaults on parse error

        return config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if url := os.getenv("PPM_INDEX_URL"):
            self.repository.index_url = url

        if mirrors := os.getenv("PPM_FALLBACK_MIRRORS"):
            self.repository.mirrors = [m.strip() for m in mirrors.split(",")]

        if wheelhouse := os.getenv("PPM_WHEELHOUSE_DIR"):
            self.wheelhouse.path = Path(wheelhouse)

        if level := os.getenv("PPM_LOG_LEVEL"):
            self.logging.level = level.upper()

        if timeout := os.getenv("PPM_TIMEOUT"):
            try:
                self.repository.timeout = int(timeout)
            except ValueError:
                pass

        if retries := os.getenv("PPM_MAX_RETRIES"):
            try:
                self.repository.max_retries = int(retries)
            except ValueError:
                pass

        if offline := os.getenv("PPM_OFFLINE"):
            self.offline_mode = offline.lower() in ("true", "1", "yes")

    def _from_dict(self, data: dict[str, Any]) -> None:
        """Populate from TOML-parsed dictionary."""
        if repo := data.get("repository"):
            self.repository.index_url = repo.get("index_url", self.repository.index_url)
            self.repository.mirrors = repo.get("mirrors", self.repository.mirrors)
            self.repository.timeout = repo.get("timeout", self.repository.timeout)
            self.repository.max_retries = repo.get("max_retries", self.repository.max_retries)
            self.repository.trusted_hosts = repo.get("trusted_hosts", self.repository.trusted_hosts)

        if wh := data.get("wheelhouse"):
            path_str = wh.get("path")
            if path_str:
                self.wheelhouse.path = Path(path_str)
            self.wheelhouse.max_size_gb = wh.get("max_size_gb", self.wheelhouse.max_size_gb)
            self.wheelhouse.auto_clean = wh.get("auto_clean", self.wheelhouse.auto_clean)
            self.wheelhouse.deduplicate = wh.get("deduplicate", self.wheelhouse.deduplicate)

        if log := data.get("logging"):
            self.logging.level = log.get("level", self.logging.level)
            log_file = log.get("log_file")
            if log_file:
                self.logging.log_file = Path(log_file)

        self.offline_mode = data.get("offline_mode", self.offline_mode)
        self.venv_name = data.get("venv_name", self.venv_name)

    def save(self) -> None:
        """Persist configuration to disk."""
        PPM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "offline_mode": self.offline_mode,
            "venv_name": self.venv_name,
            "repository": {
                "index_url": self.repository.index_url,
                "mirrors": self.repository.mirrors,
                "timeout": self.repository.timeout,
                "max_retries": self.repository.max_retries,
                "trusted_hosts": self.repository.trusted_hosts,
            },
            "wheelhouse": {
                "path": str(self.wheelhouse.path),
                "max_size_gb": self.wheelhouse.max_size_gb,
                "auto_clean": self.wheelhouse.auto_clean,
                "deduplicate": self.wheelhouse.deduplicate,
            },
            "logging": {
                "level": self.logging.level,
            },
        }
        with open(PPM_CONFIG_FILE, "wb") as f:
            tomli_w.dump(data, f)

    def to_display_dict(self) -> dict[str, Any]:
        """Return a display-friendly nested dictionary."""
        return {
            "General": {
                "offline_mode": self.offline_mode,
                "venv_name": self.venv_name,
            },
            "Repository": {
                "index_url": self.repository.index_url,
                "mirrors": self.repository.mirrors,
                "timeout": f"{self.repository.timeout}s",
                "max_retries": self.repository.max_retries,
            },
            "Wheelhouse": {
                "path": str(self.wheelhouse.path),
                "max_size_gb": f"{self.wheelhouse.max_size_gb} GB",
                "auto_clean": self.wheelhouse.auto_clean,
                "deduplicate": self.wheelhouse.deduplicate,
            },
            "Logging": {
                "level": self.logging.level,
                "config_file": str(PPM_CONFIG_FILE),
            },
        }
