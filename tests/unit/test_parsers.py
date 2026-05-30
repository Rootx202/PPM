"""Unit tests for the requirements parser."""

import textwrap
from pathlib import Path

import pytest

from ppm.models import Requirement
from ppm.parsers import parse_requirements, write_requirements


def _write_reqs(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "requirements.txt"
    f.write_text(textwrap.dedent(content))
    return f


class TestParseRequirements:
    def test_simple_packages(self, tmp_path):
        f = _write_reqs(
            tmp_path,
            """
            requests
            flask
            django
        """,
        )
        reqs = parse_requirements(f)
        names = [r.name for r in reqs if r.name]
        assert "requests" in names
        assert "flask" in names
        assert "django" in names

    def test_version_specifiers(self, tmp_path):
        f = _write_reqs(
            tmp_path,
            """
            requests>=2.28.0
            flask==2.3.0
            django>=4.0,<5.0
        """,
        )
        reqs = parse_requirements(f)
        named = {r.name: r for r in reqs if r.name}
        assert "requests" in named
        assert "flask" in named

    def test_skip_comments_and_blanks(self, tmp_path):
        f = _write_reqs(
            tmp_path,
            """
            # This is a comment
            requests  # inline comment

            flask
        """,
        )
        reqs = parse_requirements(f)
        names = [r.name for r in reqs if r.name]
        assert "requests" in names
        assert "flask" in names
        assert len(names) == 2

    def test_extras(self, tmp_path):
        f = _write_reqs(
            tmp_path,
            """
            httpx[http2]>=0.27
        """,
        )
        reqs = parse_requirements(f)
        assert any(r.name and r.name.lower() == "httpx" for r in reqs)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_requirements(tmp_path / "nonexistent.txt")

    def test_recursive_include(self, tmp_path):
        base = _write_reqs(tmp_path, "requests\n")
        included = tmp_path / "extra.txt"
        included.write_text("flask\n")
        base.write_text(f"requests\n-r {included}\n")
        reqs = parse_requirements(base)
        names = [r.name for r in reqs if r.name]
        assert "requests" in names
        assert "flask" in names


class TestWriteRequirements:
    def test_write_and_read_back(self, tmp_path):
        reqs = [
            Requirement(name="requests", version_spec=">=2.0"),
            Requirement(name="flask", version_spec="==2.3.0"),
        ]
        out = tmp_path / "out.txt"
        write_requirements(reqs, out)
        content = out.read_text()
        assert "requests>=2.0" in content
        assert "flask==2.3.0" in content
