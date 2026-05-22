"""Search service: query PyPI for packages."""

from __future__ import annotations

import asyncio

from ppm.config import PPMConfig
from ppm.repositories import RepositoryManager
from ppm.utils.console import get_logger

logger = get_logger(__name__)


class SearchService:
    """Search PyPI for packages matching a query."""

    def __init__(self, config: PPMConfig, repo_manager: RepositoryManager) -> None:
        self.config = config
        self.repo = repo_manager

    def search(self, query: str) -> list[dict]:
        """
        Search PyPI for packages.
        Returns list of dicts: {name, version, description}.
        """
        return asyncio.run(self.repo.search_packages(query))

    def get_package_info(self, package_name: str) -> dict | None:
        """Fetch detailed package info from PyPI JSON API."""
        return asyncio.run(self.repo.fetch_package_info(package_name))
