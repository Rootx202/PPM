"""PPM CLI Application - main Typer app with all commands."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ppm.config import PPMConfig
from ppm.core import ServiceContainer
from ppm.models import VulnerabilitySeverity
from ppm.utils.console import (
    PPM_THEME,
    console,
    error,
    info,
    make_install_progress,
    make_progress,
    make_table,
    muted,
    print_banner,
    result_panel,
    section,
    step,
    success,
    warning,
)

# ─── Typer App Setup ─────────────────────────────────────────────────────────

app = typer.Typer(
    name="ppm",
    help="[bold cyan]PPM[/bold cyan] - Python Package Manager\n\n"
         "Smart Python environment and package management CLI.",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Sub-app for wheelhouse commands
wheelhouse_app = typer.Typer(
    name="wheelhouse",
    help="Manage the local wheel cache (wheelhouse).",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(wheelhouse_app, name="wheelhouse")

# Sub-app for cache commands
cache_app = typer.Typer(
    name="cache",
    help="Manage pip and PPM caches.",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(cache_app, name="cache")


# ─── Context helpers ──────────────────────────────────────────────────────────

def _get_project_dir() -> Path:
    """Return the current working directory as project root."""
    return Path.cwd()


def _get_container(project_dir: Optional[Path] = None) -> ServiceContainer:
    """Build and return the DI container."""
    cwd = project_dir or _get_project_dir()
    config = PPMConfig.load()
    return ServiceContainer(project_dir=cwd, config=config)


def _abort(msg: str) -> None:
    """Print error and exit with code 1."""
    error(msg)
    raise typer.Exit(1)


# ─── ppm init ────────────────────────────────────────────────────────────────

@app.command("init")
@app.command("i", hidden=True)
def cmd_init(
    force: Annotated[bool, typer.Option("--force", "-f", help="Recreate venv if it already exists.")] = False,
    name: Annotated[str, typer.Option("--name", "-n", help="Venv directory name.")] = ".venv",
) -> None:
    """
    🚀 Initialize a new Python virtual environment in the current directory.

    Creates [bold].venv/[/bold] and upgrades pip automatically.
    """
    print_banner()
    container = _get_container()
    container.config.venv_name = name

    section("Initializing Virtual Environment")
    step(f"OS detected: [ppm.highlight]{container.env_manager.os_type.value}[/ppm.highlight]")
    step(f"Venv path: [ppm.path]{container.env_manager.venv_path}[/ppm.path]")

    try:
        with make_progress("Creating virtual environment") as progress:
            task = progress.add_task("Creating .venv...", total=None)
            env_info = container.environment_service.init(force=force)
            progress.update(task, completed=True)

        console.print()
        success(f"Virtual environment created at [ppm.path]{env_info.path}[/ppm.path]")
        console.print()

        # Show activation instructions
        activate_panel = Text()
        activate_panel.append("To activate, run:\n\n", style="dim")
        activate_panel.append(f"  {env_info.activate_command}", style="bold bright_cyan")

        console.print(
            Panel(
                activate_panel,
                title="[bold]Activation Command[/bold]",
                border_style="cyan",
                expand=False,
            )
        )

        console.print()
        info(f"Python: [ppm.version]{env_info.python_version}[/ppm.version]")
        info(f"pip:    [ppm.version]{env_info.pip_version}[/ppm.version]")

    except FileExistsError as e:
        _abort(str(e))
    except Exception as e:
        _abort(f"Failed to create virtual environment: {e}")


# ─── ppm sync ────────────────────────────────────────────────────────────────

@app.command("sync")
@app.command("s", hidden=True)
def cmd_sync(
    requirements: Annotated[Path, typer.Option("--requirements", "-r", help="Path to requirements.txt")] = Path("requirements.txt"),
    offline: Annotated[bool, typer.Option("--offline", help="Use wheelhouse only, no network.")] = False,
    no_lock: Annotated[bool, typer.Option("--no-lock", help="Skip generating lock file.")] = False,
) -> None:
    """
    🔄 Sync virtual environment with [bold]requirements.txt[/bold].

    Installs missing packages and validates versions.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    section("Requirements Sync")
    step(f"Reading: [ppm.path]{requirements.resolve()}[/ppm.path]")

    if offline:
        info("Offline mode: using wheelhouse only")

    try:
        with make_install_progress() as progress:
            task = progress.add_task("Syncing packages...", total=None)
            result = container.sync_service.sync(
                requirements_file=requirements,
                offline=offline,
                generate_lock=not no_lock,
            )
            progress.update(task, completed=True)

        console.print()

        # Summary table
        table = make_table(
            "Sync Results",
            ("Status", "ppm.success"),
            ("Package", "ppm.package"),
        )
        for pkg in result.installed:
            table.add_row("✅ Installed", pkg)
        for pkg in result.already_satisfied:
            table.add_row("[dim]✔ Already OK[/dim]", f"[dim]{pkg}[/dim]")
        for pkg in result.failed:
            table.add_row("[ppm.error]❌ Failed[/ppm.error]", f"[ppm.error]{pkg}[/ppm.error]")

        console.print(table)
        console.print()

        if result.success:
            success(
                f"Sync complete: {len(result.installed)} installed, "
                f"{len(result.already_satisfied)} already satisfied"
            )
        else:
            warning(
                f"Sync finished with {len(result.failed)} failure(s): "
                + ", ".join(result.failed)
            )
            raise typer.Exit(1)

    except FileNotFoundError as e:
        _abort(str(e))
    except Exception as e:
        _abort(f"Sync failed: {e}")


# ─── ppm install ─────────────────────────────────────────────────────────────

@app.command("install")
@app.command("in", hidden=True)
def cmd_install(
    package: Annotated[str, typer.Argument(help="Package name to install (e.g. fastapi>=0.100)")],
    offline: Annotated[bool, typer.Option("--offline", help="Use wheelhouse only.")] = False,
    version: Annotated[Optional[str], typer.Option("--version", "-v", help="Version specifier, e.g. '>=1.0'")] = None,
) -> None:
    """
    📦 Install a package into the virtual environment.

    Uses wheelhouse cache first, then falls back to PyPI with mirror support.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    section(f"Installing: {package}")

    # Allow version in package name OR via --version flag
    pkg_name = package
    version_spec = version or ""

    # Parse if user provides "fastapi>=0.100" style
    import re
    m = re.match(r"^([a-zA-Z0-9_.-]+)(.*)", package)
    if m:
        pkg_name = m.group(1)
        if not version_spec:
            version_spec = m.group(2).strip()

    try:
        with make_progress(f"Installing {pkg_name}") as progress:
            task = progress.add_task(f"Installing [bold]{pkg_name}[/bold]...", total=None)
            result = container.install_service.install(
                pkg_name, version_spec=version_spec, offline=offline
            )
            progress.update(task, completed=True)

        console.print()

        if result.success:
            cache_note = " [dim](from wheelhouse)[/dim]" if result.from_cache else ""
            success(
                f"Installed [ppm.package]{result.package}[/ppm.package] "
                f"[ppm.version]{result.version}[/ppm.version]{cache_note} "
                f"in {result.elapsed_seconds:.2f}s"
            )
        else:
            _abort(f"Install failed: {result.error}")

    except Exception as e:
        _abort(f"Install error: {e}")


# ─── ppm remove ──────────────────────────────────────────────────────────────

@app.command("remove")
@app.command("rm", hidden=True)
def cmd_remove(
    package: Annotated[str, typer.Argument(help="Package name to remove.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """
    🗑️  Remove a package from the virtual environment.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    if not yes:
        confirmed = typer.confirm(f"Remove '{package}'?")
        if not confirmed:
            info("Aborted.")
            return

    with make_progress(f"Removing {package}") as progress:
        task = progress.add_task(f"Removing [bold]{package}[/bold]...", total=None)
        result = container.install_service.uninstall(package)
        progress.update(task, completed=True)

    console.print()
    if result.success:
        success(f"Removed [ppm.package]{result.package}[/ppm.package]")
    else:
        _abort(f"Remove failed: {result.error}")


# ─── ppm search ──────────────────────────────────────────────────────────────

@app.command("search")
@app.command("se", hidden=True)
def cmd_search(
    query: Annotated[str, typer.Argument(help="Package name or keyword to search for.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results to show.")] = 10,
) -> None:
    """
    🔍 Search PyPI for packages matching the query.
    """
    section(f"Searching PyPI: '{query}'")
    container = _get_container()

    with make_progress("Searching") as progress:
        task = progress.add_task(f"Searching for [bold]{query}[/bold]...", total=None)
        results = container.search_service.search(query)
        progress.update(task, completed=True)

    console.print()

    if not results:
        warning(f"No packages found for '{query}'")
        return

    table = make_table(
        f"Search Results: '{query}'",
        ("Package", "bold white"),
        ("Version", "ppm.version"),
        ("Description", "dim"),
    )

    for pkg in results[:limit]:
        desc = pkg.get("description", "")
        if len(desc) > 70:
            desc = desc[:67] + "..."
        table.add_row(pkg["name"], pkg["version"], desc)

    console.print(table)
    console.print()
    muted(f"Showing {min(len(results), limit)} of {len(results)} results. Install with: ppm install <name>")


# ─── ppm audit ───────────────────────────────────────────────────────────────

@app.command("audit")
@app.command("au", hidden=True)
def cmd_audit(
    requirements: Annotated[Optional[Path], typer.Option("--requirements", "-r", help="Audit a requirements.txt file.")] = None,
    fail_on_vuln: Annotated[bool, typer.Option("--fail", help="Exit with code 1 if vulnerabilities found.")] = False,
) -> None:
    """
    🔐 Scan for security vulnerabilities and deprecated packages.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    section("Security Audit")

    with make_progress("Scanning for vulnerabilities") as progress:
        task = progress.add_task("Running pip-audit...", total=None)
        report, deprecated = container.audit_service.audit(requirements_file=requirements)
        progress.update(task, completed=True)

    console.print()

    # ── Vulnerabilities ───────────────────────────────────────────────────────
    if report.error:
        warning(f"Audit error: {report.error}")
    elif report.is_clean:
        success(f"No vulnerabilities found in {report.scanned_packages} packages ✨")
    else:
        vuln_table = make_table(
            "Vulnerabilities Found",
            ("Package", "bold white"),
            ("Version", "ppm.version"),
            ("ID", "yellow"),
            ("Severity", "ppm.error"),
            ("Fix Available", "ppm.success"),
        )

        severity_styles = {
            VulnerabilitySeverity.CRITICAL: "[ppm.vuln.critical]CRITICAL[/ppm.vuln.critical]",
            VulnerabilitySeverity.HIGH: "[ppm.vuln.high]HIGH[/ppm.vuln.high]",
            VulnerabilitySeverity.MEDIUM: "[ppm.vuln.medium]MEDIUM[/ppm.vuln.medium]",
            VulnerabilitySeverity.LOW: "[ppm.vuln.low]LOW[/ppm.vuln.low]",
            VulnerabilitySeverity.UNKNOWN: "[ppm.vuln.unknown]UNKNOWN[/ppm.vuln.unknown]",
        }

        for vuln in report.vulnerabilities:
            fix = ", ".join(f">= {v}" for v in vuln.fix_versions) or "N/A"
            vuln_table.add_row(
                vuln.package_name,
                vuln.installed_version,
                vuln.vulnerability_id,
                severity_styles.get(vuln.severity, "?"),
                fix,
            )

        console.print(vuln_table)
        console.print()
        error(
            f"Found {report.vulnerable_packages} vulnerable package(s) "
            f"out of {report.scanned_packages} scanned"
        )

    # ── Deprecated packages ───────────────────────────────────────────────────
    if deprecated:
        console.print()
        dep_table = make_table(
            "Deprecated / At-Risk Packages",
            ("Package", "bold white"),
            ("Version", "ppm.version"),
            ("Warning", "ppm.warning"),
        )
        for item in deprecated:
            dep_table.add_row(item["package"], item["version"], item["warning"])
        console.print(dep_table)

    if fail_on_vuln and not report.is_clean:
        raise typer.Exit(1)


# ─── ppm repair ──────────────────────────────────────────────────────────────

@app.command("repair")
@app.command("rp", hidden=True)
def cmd_repair(
    requirements: Annotated[Optional[Path], typer.Option("--requirements", "-r", help="Reinstall from requirements.txt")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """
    🔧 Repair a broken virtual environment.

    Upgrades pip, detects conflicts, cleans caches, and reinstalls packages.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    if not yes:
        confirmed = typer.confirm("This will modify your environment. Continue?")
        if not confirmed:
            info("Aborted.")
            return

    section("Repairing Environment")

    with make_progress("Running repairs") as progress:
        task = progress.add_task("Repairing...", total=None)
        actions = container.repair_service.repair(requirements_file=requirements)
        progress.update(task, completed=True)

    console.print()
    for action in actions:
        console.print(f"  {action}")

    console.print()
    success("Repair complete.")


# ─── ppm doctor ──────────────────────────────────────────────────────────────

@app.command("doctor")
@app.command("doc", hidden=True)
def cmd_doctor() -> None:
    """
    🩺 Run a full diagnostic check on your PPM environment.
    """
    section("PPM Doctor")
    container = _get_container()

    with make_progress("Running checks") as progress:
        task = progress.add_task("Diagnosing...", total=None)
        report = container.doctor_service.run()
        progress.update(task, completed=True)

    console.print()

    table = make_table(
        "Diagnostic Report",
        ("Check", "bold white"),
        ("Status", None),
        ("Details", "dim"),
    )

    for check in report.checks:
        status = "[ppm.success]✅ Pass[/ppm.success]" if check.passed else "[ppm.error]❌ Fail[/ppm.error]"
        details = check.message
        if not check.passed and check.suggestion:
            details += f"\n  [dim]→ {check.suggestion}[/dim]"
        table.add_row(check.name, status, details)

    console.print(table)
    console.print()

    if report.all_passed:
        success("All checks passed! Your environment is healthy. ✨")
    else:
        failed_count = len(report.failed_checks)
        warning(f"{failed_count} check(s) failed. See suggestions above.")


# ─── ppm config show ─────────────────────────────────────────────────────────

@app.command("config")
@app.command("cfg", hidden=True)
def cmd_config(
    show: Annotated[bool, typer.Option("--show", help="Show current configuration.")] = True,
    set_key: Annotated[Optional[str], typer.Option("--set", help="Set a config key (key=value).")] = None,
) -> None:
    """
    ⚙️  View or modify PPM configuration.

    Config is stored at [bold]~/.config/ppm/config.toml[/bold].
    """
    from ppm.config import PPM_CONFIG_FILE

    config = PPMConfig.load()

    if set_key:
        # Parse key=value
        if "=" not in set_key:
            _abort("Use --set key=value format, e.g. --set repository.timeout=60")
        key, value = set_key.split("=", 1)
        info(f"Setting [bold]{key}[/bold] = [ppm.version]{value}[/ppm.version]")
        # Apply simple key overrides (extend as needed)
        if key == "repository.timeout":
            config.repository.timeout = int(value)
        elif key == "repository.index_url":
            config.repository.index_url = value
        elif key == "offline_mode":
            config.offline_mode = value.lower() in ("true", "1", "yes")
        else:
            warning(f"Unknown config key: {key}")
            return
        config.save()
        success("Configuration saved.")
        return

    section("PPM Configuration")
    display = config.to_display_dict()

    for section_name, values in display.items():
        table = make_table(
            section_name,
            ("Setting", "bold white"),
            ("Value", "ppm.highlight"),
        )
        for k, v in values.items():
            if isinstance(v, list):
                v_str = "\n".join(str(item) for item in v) if v else "(none)"
            else:
                v_str = str(v)
            table.add_row(k, v_str)
        console.print(table)
        console.print()

    muted(f"Config file: {PPM_CONFIG_FILE}")


# ─── ppm wheelhouse build ────────────────────────────────────────────────────

@wheelhouse_app.command("build")
@wheelhouse_app.command("b", hidden=True)
def cmd_wheelhouse_build(
    requirements: Annotated[Path, typer.Option("--requirements", "-r", help="Path to requirements.txt")] = Path("requirements.txt"),
) -> None:
    """
    🏗️  Download wheels for all requirements into the local wheelhouse cache.
    """
    container = _get_container()

    try:
        container.environment_service.require_env()
    except RuntimeError as e:
        _abort(str(e))

    section("Building Wheelhouse")
    step(f"Downloading wheels from requirements: [ppm.path]{requirements}[/ppm.path]")
    step(f"Wheelhouse path: [ppm.path]{container.config.wheelhouse.path}[/ppm.path]")

    try:
        with make_progress("Downloading wheels") as progress:
            task = progress.add_task("Downloading...", total=None)
            count, errors = container.wheelhouse_service.build(requirements)
            progress.update(task, completed=True)

        console.print()
        if errors:
            for err in errors:
                warning(err[:200])

        stats = container.wheelhouse_service.get_stats()
        success(
            f"Wheelhouse built: {stats.total_wheels} wheels "
            f"({stats.total_size_mb:.1f} MB) for {stats.unique_packages} packages"
        )

    except FileNotFoundError as e:
        _abort(str(e))
    except Exception as e:
        _abort(f"Wheelhouse build failed: {e}")


@wheelhouse_app.command("list")
@wheelhouse_app.command("ls", hidden=True)
def cmd_wheelhouse_list() -> None:
    """📋 List all cached wheels in the wheelhouse."""
    container = _get_container()
    stats = container.wheelhouse_service.get_stats()
    wheels = container.wheelhouse_service.list_wheels()

    if not wheels:
        info("Wheelhouse is empty. Run 'ppm wheelhouse build' to populate it.")
        return

    table = make_table(
        f"Wheelhouse ({stats.total_wheels} wheels, {stats.total_size_mb:.1f} MB)",
        ("Package", "bold white"),
        ("Version", "ppm.version"),
        ("Platform", "dim"),
        ("Size", "ppm.muted"),
    )

    for w in wheels:
        size_kb = w.file_size / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
        table.add_row(w.package_name, w.version, w.platform_tag, size_str)

    console.print(table)


@wheelhouse_app.command("stats")
@wheelhouse_app.command("st", hidden=True)
def cmd_wheelhouse_stats() -> None:
    """📊 Show wheelhouse cache statistics."""
    container = _get_container()
    stats = container.wheelhouse_service.get_stats()

    result_panel(
        f"[bold]Total wheels:[/bold] {stats.total_wheels}\n"
        f"[bold]Unique packages:[/bold] {stats.unique_packages}\n"
        f"[bold]Total size:[/bold] {stats.total_size_mb:.2f} MB\n"
        f"[bold]Location:[/bold] {container.config.wheelhouse.path}",
        title="Wheelhouse Stats",
        style="cyan",
    )


# ─── ppm cache clean ──────────────────────────────────────────────────────────

@cache_app.command("clean")
@cache_app.command("cl", hidden=True)
def cmd_cache_clean(
    keep_latest: Annotated[bool, typer.Option("--keep-latest/--all", help="Keep only latest wheel per package.")] = True,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """
    🧹 Clean the PPM wheelhouse cache.
    """
    container = _get_container()

    action = "old versions" if keep_latest else "ALL wheels"
    if not yes:
        confirmed = typer.confirm(f"Remove {action} from wheelhouse?")
        if not confirmed:
            info("Aborted.")
            return

    with make_progress("Cleaning cache") as progress:
        task = progress.add_task("Cleaning...", total=None)
        removed = container.wheelhouse_service.clean(keep_latest=keep_latest)
        repair_actions = container.repair_service.clean_cache()
        progress.update(task, completed=True)

    console.print()
    success(f"Removed {removed} wheel file(s) from wheelhouse")
    for action in repair_actions:
        console.print(f"  {action}")


# ─── Main entry point ─────────────────────────────────────────────────────────

def main() -> None:
    """PPM CLI entry point."""
    app()


if __name__ == "__main__":
    main()
