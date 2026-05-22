"""Repository management: primary index + fallback mirrors with retry logic."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from ppm.config import RepositoryConfig
from ppm.models import Repository, RepositoryStatus
from ppm.utils.console import get_logger
from ppm.utils.security import validate_url

logger = get_logger(__name__)

PYPI_JSON_API = "https://pypi.org/pypi/{package}/json"
PYPI_SEARCH_URL = "https://pypi.org/search/?q={query}&format=json"


class RepositoryManager:
    """
    Manages PyPI index repositories with priority-based fallback and retry logic.
    Supports async health checks and parallel mirror probing.
    """

    def __init__(self, config: RepositoryConfig) -> None:
        self.config = config
        self._repositories: list[Repository] = self._build_repo_list()

    def _build_repo_list(self) -> list[Repository]:
        """Build ordered repository list from config."""
        repos = [
            Repository(
                name="PyPI (primary)",
                url=self.config.index_url,
                priority=0,
                trusted=True,
            )
        ]
        for i, mirror_url in enumerate(self.config.mirrors, start=1):
            if validate_url(mirror_url):
                repos.append(
                    Repository(
                        name=f"Mirror {i}",
                        url=mirror_url,
                        priority=i,
                    )
                )
        return sorted(repos, key=lambda r: r.priority)

    @property
    def repositories(self) -> list[Repository]:
        return self._repositories

    async def probe_repository(self, repo: Repository) -> Repository:
        """Ping a repository and measure response time."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(repo.url, follow_redirects=True)
                elapsed = (time.monotonic() - start) * 1000
                repo.response_time_ms = elapsed
                if resp.status_code < 500:
                    repo.status = (
                        RepositoryStatus.SLOW
                        if elapsed > 5000
                        else RepositoryStatus.ONLINE
                    )
                else:
                    repo.status = RepositoryStatus.OFFLINE
        except Exception as exc:
            logger.debug(f"Probe failed for {repo.url}: {exc}")
            repo.status = RepositoryStatus.OFFLINE
            repo.response_time_ms = 0.0
        return repo

    async def probe_all(self) -> list[Repository]:
        """Probe all repositories concurrently."""
        tasks = [self.probe_repository(repo) for repo in self._repositories]
        self._repositories = await asyncio.gather(*tasks)
        return self._repositories

    def get_online_repositories(self) -> list[Repository]:
        """Return only repositories with ONLINE/SLOW status."""
        return [
            r for r in self._repositories
            if r.status in (RepositoryStatus.ONLINE, RepositoryStatus.SLOW)
        ]

    async def fetch_package_info(self, package_name: str) -> Optional[dict]:
        """
        Fetch package metadata from PyPI JSON API.
        Returns parsed JSON dict or None on failure.
        """
        url = PYPI_JSON_API.format(package=package_name)
        for attempt in range(self.config.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.config.timeout,
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code == 404:
                        return None  # Package not found
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {package_name}, attempt {attempt + 1}")
                await asyncio.sleep(1.0 * (attempt + 1))  # exponential back-off
            except Exception as e:
                logger.warning(f"Error fetching {package_name}: {e}")
                await asyncio.sleep(0.5)
        return None

    async def search_packages(self, query: str) -> list[dict]:
        """
        Search PyPI for packages matching the query.
        Returns a list of result dicts with name/version/description.
        """
        # Use the PyPI search endpoint (XML-RPC or simple API workaround)
        # We use the JSON API for individual results as PyPI search API is deprecated
        search_url = f"https://pypi.org/search/?q={query}"
        results: list[dict] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout,
                follow_redirects=True,
                headers={"Accept": "text/html"},
            ) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    results = self._parse_search_html(resp.text, query)
        except Exception as e:
            logger.warning(f"Search failed: {e}")

        return results

    def _parse_search_html(self, html: str, query: str) -> list[dict]:
        """Extract package names from PyPI search result HTML."""
        import re

        results: list[dict] = []
        # Extract package snippets from search HTML
        # Pattern: <span class="package-snippet__name">NAME</span>
        name_pat = re.compile(
            r'class="package-snippet__name"[^>]*>\s*([^<]+)\s*</span>'
        )
        ver_pat = re.compile(
            r'class="package-snippet__version"[^>]*>\s*([^<]+)\s*</span>'
        )
        desc_pat = re.compile(
            r'class="package-snippet__description"[^>]*>\s*([^<]*)\s*</p>'
        )

        names = name_pat.findall(html)
        versions = ver_pat.findall(html)
        descs = desc_pat.findall(html)

        for i, name in enumerate(names[:20]):  # Cap at 20 results
            results.append(
                {
                    "name": name.strip(),
                    "version": versions[i].strip() if i < len(versions) else "?",
                    "description": descs[i].strip() if i < len(descs) else "",
                }
            )
        return results

    def build_pip_index_args(self) -> list[str]:
        """
        Build pip --index-url and --extra-index-url args from config.
        Includes trusted-host flags where needed.
        """
        args = ["--index-url", self.config.index_url]
        for mirror in self.config.mirrors:
            args += ["--extra-index-url", mirror]
        for host in self.config.trusted_hosts:
            args += ["--trusted-host", host]
        return args
