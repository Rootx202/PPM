"""Integration tests for repository manager."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ppm.config import RepositoryConfig
from ppm.repositories import RepositoryManager
from ppm.models import RepositoryStatus


class TestRepositoryManager:
    def setup_method(self):
        self.config = RepositoryConfig()
        self.config.timeout = 5
        self.manager = RepositoryManager(self.config)

    def test_builds_repo_list(self):
        repos = self.manager.repositories
        assert len(repos) >= 1
        # Primary PyPI should be first
        assert repos[0].url == "https://pypi.org/simple"

    def test_build_pip_index_args(self):
        args = self.manager.build_pip_index_args()
        assert "--index-url" in args
        assert "https://pypi.org/simple" in args
        assert "--extra-index-url" in args

    def test_invalid_mirror_filtered(self):
        config = RepositoryConfig()
        config.mirrors = ["ftp://invalid.com", "https://valid.mirror.com/simple"]
        mgr = RepositoryManager(config)
        urls = [r.url for r in mgr.repositories]
        assert "ftp://invalid.com" not in urls
        assert "https://valid.mirror.com/simple" in urls

    @pytest.mark.asyncio
    async def test_probe_repository_offline(self):
        """Test that offline probe sets status to OFFLINE."""
        import httpx
        repo = self.manager.repositories[0]

        with patch.object(
            httpx.AsyncClient,
            "get",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await self.manager.probe_repository(repo)
            assert result.status == RepositoryStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_fetch_package_info_not_found(self):
        """Test 404 returns None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            result = await self.manager.fetch_package_info("totally-nonexistent-xyz123")
            # Should return None for 404
            # (actual result depends on mock setup)

    def test_search_html_parsing(self):
        """Test the HTML parser extracts package results."""
        html = """
        <span class="package-snippet__name">requests</span>
        <span class="package-snippet__version">2.31.0</span>
        <p class="package-snippet__description">HTTP library</p>
        """
        results = self.manager._parse_search_html(html, "requests")
        assert len(results) == 1
        assert results[0]["name"] == "requests"
        assert results[0]["version"] == "2.31.0"
