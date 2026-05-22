"""Dependency injection container for PPM services."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from ppm.config import PPMConfig
from ppm.environments import EnvironmentManager
from ppm.repositories import RepositoryManager
from ppm.services.audit_service import AuditService
from ppm.services.doctor_service import DoctorService
from ppm.services.env_service import EnvironmentService
from ppm.services.install_service import InstallService
from ppm.services.repair_service import RepairService
from ppm.services.search_service import SearchService
from ppm.services.sync_service import SyncService
from ppm.services.wheelhouse_service import WheelhouseService
from ppm.wheelhouse import WheelhouseManager


class ServiceContainer:
    """
    Dependency injection container.
    Lazily instantiates and wires all services together.
    """

    def __init__(self, project_dir: Path, config: PPMConfig) -> None:
        self.project_dir = project_dir
        self.config = config

    @cached_property
    def env_manager(self) -> EnvironmentManager:
        return EnvironmentManager(self.project_dir, self.config.venv_name)

    @cached_property
    def wheelhouse(self) -> WheelhouseManager:
        return WheelhouseManager(self.config.wheelhouse)

    @cached_property
    def repo_manager(self) -> RepositoryManager:
        return RepositoryManager(self.config.repository)

    @cached_property
    def environment_service(self) -> EnvironmentService:
        return EnvironmentService(self.config, self.project_dir)

    @cached_property
    def install_service(self) -> InstallService:
        return InstallService(
            config=self.config,
            env_manager=self.env_manager,
            wheelhouse=self.wheelhouse,
            repo_manager=self.repo_manager,
        )

    @cached_property
    def sync_service(self) -> SyncService:
        return SyncService(
            config=self.config,
            env_manager=self.env_manager,
            wheelhouse=self.wheelhouse,
            repo_manager=self.repo_manager,
        )

    @cached_property
    def audit_service(self) -> AuditService:
        return AuditService(self.config, self.env_manager)

    @cached_property
    def repair_service(self) -> RepairService:
        return RepairService(self.config, self.env_manager)

    @cached_property
    def search_service(self) -> SearchService:
        return SearchService(self.config, self.repo_manager)

    @cached_property
    def doctor_service(self) -> DoctorService:
        return DoctorService(self.config, self.env_manager)

    @cached_property
    def wheelhouse_service(self) -> WheelhouseService:
        return WheelhouseService(
            config=self.config,
            wheelhouse=self.wheelhouse,
            env_manager=self.env_manager,
            repo_manager=self.repo_manager,
        )
