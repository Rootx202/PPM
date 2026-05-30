"""Unit tests for validation utilities."""

import pytest

from ppm.utils.security import (
    safe_path,
    safe_subprocess_args,
    sanitize_package_name,
    validate_package_name,
    validate_pypi_url,
    validate_url,
)


class TestPackageNameValidation:
    def test_valid_names(self):
        valid = ["requests", "Flask", "Django", "my-package", "my_pkg", "pkg123", "A"]
        for name in valid:
            assert validate_package_name(name), f"Expected valid: {name}"

    def test_invalid_names(self):
        invalid = ["", "pkg with space", "pkg/slash", "a" * 201, "-starts-with-dash"]
        for name in invalid:
            assert not validate_package_name(name), f"Expected invalid: {name}"

    def test_sanitize(self):
        assert sanitize_package_name("My-Package") == "my-package"
        assert sanitize_package_name("my_package") == "my-package"
        assert sanitize_package_name("my.pkg") == "my-pkg"
        assert sanitize_package_name("my--pkg") == "my-pkg"


class TestUrlValidation:
    def test_valid_urls(self):
        valid = [
            "https://pypi.org/simple",
            "http://mirrors.aliyun.com/pypi/simple",
            "https://pypi.tuna.tsinghua.edu.cn/simple",
        ]
        for url in valid:
            assert validate_url(url), f"Expected valid URL: {url}"

    def test_invalid_urls(self):
        invalid = [
            "",
            "ftp://bad.com",
            "not-a-url",
            "file:///etc/passwd",
            "javascript:alert(1)",
        ]
        for url in invalid:
            assert not validate_url(url), f"Expected invalid URL: {url}"

    def test_pypi_url_check(self):
        assert validate_pypi_url("https://pypi.org/simple")
        assert not validate_pypi_url("ftp://evil.com")


class TestPathSafety:
    def test_safe_path_within_base(self, tmp_path):
        base = tmp_path / "wheelhouse"
        base.mkdir()
        child = base / "mypackage-1.0.whl"
        assert safe_path(child, base)

    def test_safe_path_traversal_blocked(self, tmp_path):
        base = tmp_path / "wheelhouse"
        base.mkdir()
        traversal = base / ".." / "etc" / "passwd"
        assert not safe_path(traversal, base)


class TestSubprocessSafety:
    def test_safe_args_pass(self):
        args = ["pip", "install", "requests"]
        assert safe_subprocess_args(args) == args

    def test_dangerous_chars_blocked(self):
        with pytest.raises(ValueError):
            safe_subprocess_args(["pip", "install", "requests; rm -rf /"])

    def test_pipe_blocked(self):
        with pytest.raises(ValueError):
            safe_subprocess_args(["pip", "install", "pkg | cat /etc/passwd"])
