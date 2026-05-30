
import pytest
from ppm.security import run_audit
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_run_audit_uses_run_safe():
    """Verify that run_audit calls run_safe and not subprocess.run directly."""
    pip_path = Path("/tmp/venv/bin/pip")

    with patch("ppm.security._find_pip_audit") as mock_find:
        mock_find.return_value = Path("/tmp/venv/bin/pip-audit")

        with patch("ppm.security.run_safe") as mock_run_safe:
            mock_result = MagicMock()
            mock_result.stdout = '{"dependencies": []}'
            mock_result.stderr = ""
            mock_run_safe.return_value = mock_result

            run_audit(pip_path)

            # Check if run_safe was called
            assert mock_run_safe.called
            args, kwargs = mock_run_safe.call_args
            assert "/tmp/venv/bin/pip-audit" in args[0]
            assert kwargs["capture"] is True

def test_validate_url_warns_on_http():
    """Verify that validate_url issues a warning for HTTP URLs."""
    from ppm.utils.security import validate_url

    with patch("ppm.utils.console.warning") as mock_warning:
        # Test HTTP
        assert validate_url("http://example.com/simple") is True
        assert mock_warning.called
        assert "Insecure HTTP URL detected" in mock_warning.call_args[0][0]

        # Test HTTPS (no warning)
        mock_warning.reset_mock()
        assert validate_url("https://example.com/simple") is True
        assert not mock_warning.called
