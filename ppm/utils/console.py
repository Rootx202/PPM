"""Rich-based console and logging utilities for PPM."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.theme import Theme

# ─── PPM Theme ────────────────────────────────────────────────────────────────

PPM_THEME = Theme(
    {
        "ppm.brand": "bold bright_cyan",
        "ppm.success": "bold bright_green",
        "ppm.warning": "bold yellow",
        "ppm.error": "bold bright_red",
        "ppm.info": "bold cyan",
        "ppm.muted": "dim white",
        "ppm.highlight": "bold magenta",
        "ppm.version": "bold bright_yellow",
        "ppm.path": "underline bright_blue",
        "ppm.package": "bold white",
        "ppm.vuln.critical": "bold bright_red on dark_red",
        "ppm.vuln.high": "bold bright_red",
        "ppm.vuln.medium": "bold yellow",
        "ppm.vuln.low": "yellow",
        "ppm.vuln.unknown": "dim white",
    }
)

# Global console instance
console = Console(theme=PPM_THEME)
err_console = Console(theme=PPM_THEME, stderr=True)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a structured logger with Rich handler."""
    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
                show_path=False,
            )
        ],
    )
    return logging.getLogger(name)


# ─── Banner ───────────────────────────────────────────────────────────────────

PPM_BANNER = """[ppm.brand]
  ██████╗ ██████╗ ███╗   ███╗
  ██╔══██╗██╔══██╗████╗ ████║
  ██████╔╝██████╔╝██╔████╔██║
  ██╔═══╝ ██╔═══╝ ██║╚██╔╝██║
  ██║     ██║     ██║ ╚═╝ ██║
  ╚═╝     ╚═╝     ╚═╝     ╚═╝[/ppm.brand]
[ppm.muted]  Python Package Manager v1.0.0[/ppm.muted]"""


def print_banner() -> None:
    """Print the PPM ASCII banner and check for updates."""
    from ppm.update_checker import check_for_updates

    console.print(PPM_BANNER)

    # Check for updates in the background cache
    new_version = check_for_updates()
    if new_version:
        console.print(
            f"[bold bright_yellow]🚀 A new version of PPM ({new_version}) "
            "is available![/bold bright_yellow]"
        )
        console.print(
            "[dim]Update using: [bold]pipx upgrade rootx-ppm[/bold] "
            "(or pip install --upgrade rootx-ppm)[/dim]"
        )

    console.print()


# ─── Status helpers ───────────────────────────────────────────────────────────


def success(msg: str) -> None:
    console.print(f"[ppm.success]✅ {msg}[/ppm.success]")


def warning(msg: str) -> None:
    console.print(f"[ppm.warning]⚠️  {msg}[/ppm.warning]")


def error(msg: str) -> None:
    console.print(f"[ppm.error]❌ {msg}[/ppm.error]")


def info(msg: str) -> None:
    console.print(f"[ppm.info]ℹ️  {msg}[/ppm.info]")


def muted(msg: str) -> None:
    console.print(f"[ppm.muted]{msg}[/ppm.muted]")


def step(msg: str) -> None:
    console.print(f"[ppm.brand]→[/ppm.brand] {msg}")


def section(title: str) -> None:
    """Print a visually distinct section header."""
    console.print()
    console.rule(f"[ppm.brand]{title}[/ppm.brand]")


def result_panel(content: str, title: str = "Result", style: str = "cyan") -> None:
    console.print(Panel(content, title=f"[bold]{title}[/bold]", border_style=style, expand=False))


# ─── Progress bars ────────────────────────────────────────────────────────────


def make_progress(description: str = "Processing") -> Progress:
    """Create a standard spinner + bar progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def make_download_progress() -> Progress:
    """Create a download-focused progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def make_install_progress() -> Progress:
    """Create a multi-step install progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# ─── Table helpers ────────────────────────────────────────────────────────────


def make_table(title: str, *columns: tuple[str, str | None]) -> Table:
    """Create a styled Rich table."""
    table = Table(
        title=f"[ppm.brand]{title}[/ppm.brand]",
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        show_lines=False,
        expand=False,
    )
    for col_name, col_style in columns:
        table.add_column(col_name, style=col_style or "white")
    return table
