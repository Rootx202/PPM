"""Check PyPI for new versions of PPM."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import httpx

from ppm.__init__ import __version__


def check_for_updates() -> Optional[str]:
    """
    Check if a newer version of rootx-ppm is available on PyPI.
    Uses a 24-hour cache to avoid slowing down the CLI.
    Returns the new version string if available, else None.
    """
    cache_file = Path.home() / ".config" / "ppm" / "update_check.json"
    now = time.time()
    
    # 1. Check cache (24 hour TTL)
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if now - data.get("last_check", 0) < 86400:
                latest = data.get("latest_version")
                if latest and _is_newer(latest, __version__):
                    return latest
                return None
        except Exception:
            pass

    # 2. Check PyPI (with very short timeout so we don't block the user)
    try:
        resp = httpx.get("https://pypi.org/pypi/rootx-ppm/json", timeout=1.0)
        if resp.status_code == 200:
            latest = resp.json()["info"]["version"]
            
            # Save to cache
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({
                "last_check": now,
                "latest_version": latest
            }))
            
            if _is_newer(latest, __version__):
                return latest
    except Exception:
        pass
        
    return None


def _is_newer(latest: str, current: str) -> bool:
    """Compare two PEP 440 versions."""
    try:
        from packaging.version import parse
        return parse(latest) > parse(current)
    except Exception:
        return False
