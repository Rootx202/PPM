# PPM — Python Package Manager

<div align="center">

```
  ██████╗ ██████╗ ███╗   ███╗
  ██╔══██╗██╔══██╗████╗ ████║
  ██████╔╝██████╔╝██╔████╔██║
  ██╔═══╝ ██╔═══╝ ██║╚██╔╝██║
  ██║     ██║     ██║ ╚═╝ ██║
  ╚═╝     ╚═╝     ╚═╝     ╚═╝
```

**Smart Python environment and package management CLI**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-black)](https://github.com/astral-sh/ruff)

</div>

---

## 🎯 What is PPM?

PPM is a **professional Python environment and package management CLI** that wraps `pip` and `venv` with smart automation:

| Feature | Description |
|---|---|
| 🚀 **venv automation** | One-command environment init with OS detection |
| 🔄 **requirements sync** | Parse, validate, install, and lock dependencies |
| 🏗️ **wheelhouse cache** | Local `.whl` cache for offline and fast installs |
| 📡 **fallback mirrors** | Auto-retry with PyPI mirrors on network failure |
| 🔐 **security audit** | CVE scanning via `pip-audit` |
| 🔧 **repair system** | Detect and fix broken environments |
| 🔍 **package search** | Search PyPI with version and description display |
| 🩺 **doctor checks** | Full diagnostics on your setup |

---

## ⚡ Quick Start

### Installation

The recommended way to install Python CLI tools globally is using `pipx` (which avoids `externally-managed-environment` errors on modern Linux):

```bash
# Install globally via pipx (Recommended)
pipx install rootx-ppm

# Or using pip in an isolated virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install rootx-ppm
```

If you are developing or want to install from source:

```bash
git clone https://github.com/Rootx202/PPM.git
cd PPM
pip install -e ".[dev]"
```

Or use the install script:

```bash
bash scripts/install.sh
```

### First Run

```bash
# Initialize a virtual environment in your project
ppm init

# Sync requirements.txt
ppm sync

# Install a package
ppm install fastapi

# Run a security audit
ppm audit

# Check environment health
ppm doctor
```

---

## 📦 All Commands & Shortcuts

You can use either the full command or its shortcut (alias).

| Command | Shortcut | Description |
|---------|----------|-------------|
| `init` | `i` | Initialize a new Python virtual environment. |
| `sync` | `s` | Sync environment with requirements.txt. |
| `install` | `in` | Install a package into the virtual environment. |
| `update` | `up` | Update a package or all packages to latest versions. |
| `upgrade` | `ug` | Upgrade the PPM tool itself to the latest version. |
| `remove` | `rm` | Remove a package from the virtual environment. |
| `search` | `se` | Search PyPI for packages matching a query. |
| `audit` | `au` | Scan for vulnerabilities and deprecated packages. |
| `repair` | `rp` | Repair a broken virtual environment. |
| `doctor` | `doc` | Run full diagnostic checks on your environment. |
| `config` | `cfg` | View or modify PPM configuration. |
| `wheelhouse build` | `b` | Download wheels into the local cache. |
| `wheelhouse list` | `ls` | List all cached wheels. |
| `wheelhouse stats` | `st` | Show wheelhouse cache statistics. |
| `cache clean` | `cl` | Clean the PPM wheelhouse cache. |

---

## 🛠️ Detailed Command Guide

### `ppm init` (Alias: `i`) — Initialize Environment

```bash
ppm init                    # Create .venv in current directory
ppm init --force            # Recreate existing venv
ppm init --name my-env      # Custom venv name
```

Detects your OS and shows the correct activation command:

```
Linux/macOS:   source .venv/bin/activate
Windows:       .venv\Scripts\activate
```

---

### `ppm sync` (Alias: `s`) — Sync Requirements

```bash
ppm sync                           # Sync with requirements.txt
ppm sync -r requirements/prod.txt  # Use a specific file
ppm sync --offline                 # Use wheelhouse only
ppm sync --no-lock                 # Skip lock file generation
```

Generates `ppm.lock.json` with pinned versions after a successful sync.

---

### `ppm install` (Alias: `in`) — Install Package

```bash
ppm install fastapi               # Latest version
ppm install "fastapi>=0.100.0"    # With version constraint
ppm install fastapi --version ">=0.100"
ppm install fastapi --offline     # From wheelhouse only
```

Install strategy (in order):
1. Check local wheelhouse cache
2. Install from PyPI with configured mirrors
3. Retry with exponential back-off

---

### `ppm update` (Alias: `up`) — Update Package(s)

```bash
ppm update                        # Update ALL packages in requirements.txt
ppm update fastapi                # Update a specific package to latest
ppm update -r requirements/dev.txt # Update from a specific file
```

This bypasses the local wheelhouse cache (unless already latest) and forcefully upgrades the requested packages.

---

### `ppm remove` (Alias: `rm`) — Remove Package

```bash
ppm remove requests       # With confirmation prompt
ppm remove requests -y    # Skip confirmation
```

---

### `ppm search` (Alias: `se`) — Search PyPI

```bash
ppm search fastapi         # Search for packages
ppm search "http client"   # Multi-word query
ppm search flask -n 5      # Limit to 5 results
```

Output:

```
┌─────────────────────────────────────────────────────┐
│                Search Results: 'fastapi'             │
├─────────────┬──────────┬──────────────────────────  │
│ Package     │ Version  │ Description                 │
├─────────────┼──────────┼──────────────────────────  │
│ fastapi     │ 0.110.0  │ FastAPI framework           │
│ fastapi-cli │ 0.0.3    │ FastAPI CLI tool            │
└─────────────┴──────────┴──────────────────────────  │
```

---

### `ppm audit` (Alias: `au`) — Security Audit

```bash
ppm audit                         # Audit installed packages
ppm audit -r requirements.txt     # Audit a requirements file
ppm audit --fail                  # Exit 1 if vulnerabilities found
```

Output example:

```
⚠️  Found vulnerabilities:

┌─────────┬─────────┬───────────┬──────────┬────────────┐
│ Package │ Version │ ID        │ Severity │ Fix        │
├─────────┼─────────┼───────────┼──────────┼────────────┤
│ urllib3 │ 1.26.5  │ GHSA-xxx  │ HIGH     │ >= 2.0     │
└─────────┴─────────┴───────────┴──────────┴────────────┘
```

---

### `ppm repair` (Alias: `rp`) — Repair Environment

```bash
ppm repair                          # Auto-repair
ppm repair -r requirements.txt -y   # Repair and reinstall
```

Repair steps:
1. Upgrade `pip`, `setuptools`, `wheel`
2. Run `pip check` to detect conflicts
3. Force-reinstall conflicting packages
4. Reinstall from requirements.txt (if provided)
5. Purge pip cache

---

### `ppm doctor` — Health Checks

```bash
ppm doctor
```

Checks:
- Python version >= 3.12
- pip available in PATH
- Virtual environment exists
- pip-audit installed
- Wheelhouse directory accessible
- Config file present
- Internet connectivity to pypi.org

---

### `ppm wheelhouse` — Wheel Cache Management

```bash
ppm wheelhouse build                         # Download wheels from requirements.txt
ppm wheelhouse build -r requirements/prod.txt
ppm wheelhouse list                          # List cached wheels
ppm wheelhouse stats                         # Cache statistics
```

---

### `ppm cache` — Cache Cleaning

```bash
ppm cache clean                # Remove old wheel versions, keep latest
ppm cache clean --all          # Remove ALL wheels
ppm cache clean -y             # Skip confirmation
```

---

### `ppm config` — Configuration

```bash
ppm config                              # Show current configuration
ppm config --set repository.timeout=60
ppm config --set offline_mode=true
```

---

## ⚙️ Configuration

PPM stores its configuration at:

| OS | Path |
|---|---|
| Linux | `~/.config/ppm/config.toml` |
| macOS | `~/Library/Application Support/ppm/config.toml` |
| Windows | `%APPDATA%\ppm\ppm\config.toml` |

### Example `config.toml`

```toml
offline_mode = false
venv_name = ".venv"

[repository]
index_url = "https://pypi.org/simple"
mirrors = [
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
]
timeout = 30
max_retries = 3
trusted_hosts = []

[wheelhouse]
path = "~/.local/share/ppm/wheelhouse"
max_size_gb = 5.0
auto_clean = false
deduplicate = true

[logging]
level = "INFO"
```

### Environment Variables

All settings can be overridden via environment variables:

| Variable | Description | Default |
|---|---|---|
| `PPM_INDEX_URL` | Primary PyPI index URL | `https://pypi.org/simple` |
| `PPM_FALLBACK_MIRRORS` | Comma-separated mirror URLs | Tsinghua, Aliyun |
| `PPM_WHEELHOUSE_DIR` | Wheelhouse directory path | `~/.local/share/ppm/wheelhouse` |
| `PPM_LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `PPM_TIMEOUT` | HTTP request timeout (seconds) | `30` |
| `PPM_MAX_RETRIES` | Maximum retry attempts | `3` |
| `PPM_OFFLINE` | Enable offline mode (true/false) | `false` |

---

## 🏗️ Architecture

PPM follows **Clean Architecture** with clear separation of concerns:

```
ppm/
├── cli/           ← Typer CLI layer (user interface)
├── core/          ← Dependency injection container
├── services/      ← Business logic layer
│   ├── env_service.py
│   ├── install_service.py
│   ├── sync_service.py
│   ├── audit_service.py
│   ├── repair_service.py
│   ├── search_service.py
│   ├── doctor_service.py
│   └── wheelhouse_service.py
├── repositories/  ← PyPI access with fallback mirrors
├── environments/  ← venv creation and management
├── wheelhouse/    ← Local .whl cache management
├── installers/    ← Package installation logic
├── parsers/       ← requirements.txt parsing
├── security/      ← pip-audit vulnerability scanning
├── config/        ← TOML config management
├── models/        ← Domain models (dataclasses)
└── utils/         ← Console, logging, security utilities
```

### Design Principles

- **Clean Architecture**: CLI → Services → Core → Infrastructure
- **Dependency Injection**: `ServiceContainer` wires all components
- **Single Responsibility**: Each module has one clear purpose
- **No Shell Injection**: All subprocesses use `shell=False`
- **Async Where Useful**: HTTP calls use `httpx` with `asyncio`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ppm --cov-report=html

# Run only unit tests (fast)
pytest tests/unit/ -v

# Run CLI tests
pytest tests/cli/ -v

# Skip slow integration tests
pytest -m "not slow"
```

---

## 🔐 Security

PPM takes security seriously:

- **Package name validation**: Rejects invalid/malicious names
- **URL validation**: Only `http://` and `https://` allowed
- **No shell injection**: All subprocess calls use `shell=False`
- **Path traversal prevention**: Safe path checks for wheelhouse
- **Vulnerability scanning**: Integrated `pip-audit` CVE scanning

---

## 🛠️ Troubleshooting

### `ppm: command not found`

```bash
pip install -e .
# Or ensure your Python scripts directory is in PATH
```

### `No virtual environment found`

```bash
ppm init
```

### pip-audit not found

```bash
pip install pip-audit
# or inside your venv:
ppm install pip-audit
```

### Offline install fails

Make sure you've built the wheelhouse first:

```bash
ppm wheelhouse build
ppm install mypackage --offline
```

### Slow installations

Use a faster mirror:

```bash
ppm config --set repository.index_url=https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 📋 Requirements

| Dependency | Version | Purpose |
|---|---|---|
| `typer[all]` | ≥ 0.12 | CLI framework |
| `rich` | ≥ 13.7 | Terminal formatting |
| `httpx[http2]` | ≥ 0.27 | Async HTTP client |
| `pip-api` | ≥ 0.0.30 | pip introspection |
| `packaging` | ≥ 24.0 | Version parsing |
| `pip-audit` | ≥ 2.7 | CVE scanning |
| `requirements-parser` | ≥ 0.11 | requirements.txt parsing |
| `tomli-w` | ≥ 1.0 | TOML writing |
| `platformdirs` | ≥ 4.0 | Cross-platform paths |
| `aiofiles` | ≥ 23.0 | Async file I/O |

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by RootX for Python developers**

</div>
