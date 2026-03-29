"""Two-column layout: results on the left, session info + cheatsheet on the right."""

from __future__ import annotations

import os
from typing import List, Tuple, Union

from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from media_backup.session import REQUIRED_PATHS

NARROW_THRESHOLD = 100


def _build_right_panel(paths: List[Tuple[str, object]]) -> str:
    """Build the right-panel markup string."""
    lines: List[str] = []

    lines.append("[bold underline]SESSION PATHS[/]")
    if not paths:
        lines.append("  [dim](none set)[/]")
    else:
        for name, p in paths:
            marker = ""
            if name in REQUIRED_PATHS:
                marker = " [bold green][✓][/]"
            path_str = str(p)
            if len(path_str) > 30:
                path_str = path_str[:27] + "…"
            lines.append(f"  [bold]{name:<8}[/] {path_str}{marker}")

    for req in REQUIRED_PATHS:
        if not any(n == req for n, _ in paths):
            lines.append(f"  [bold]{req:<8}[/] [dim]not set[/]          [bold red][✗][/]")

    lines.append("")
    lines.append("[bold underline]COMMANDS[/]")
    cmds = [
        ("sync-check", "SSD vs HDD — path structure diff"),
        ("coverage-check <src> <tgt>", "Every file from src found in tgt?"),
        ("safe-to-clear <dir>", "Safe to delete this laptop dir?"),
        ("duplicates <dir>", "Same file in multiple subdirs?"),
        ("timeline-gaps <dir> [--min-gap N]", "Date gaps across entire drive"),
        ("set/unset/paths/help/quit", ""),
    ]
    for cmd, desc in cmds:
        lines.append(f"  [bold cyan]{cmd}[/]")
        if desc:
            lines.append(f"    [dim]{desc}[/]")

    lines.append("")
    lines.append("[bold underline]PATH EXAMPLES (Windows)[/]")
    lines.append("  Laptop:  C:\\Users\\You\\Pictures\\2024")
    lines.append("  Drive:   D:\\Backup\\Photos")
    lines.append("  Phone*:  C:\\Users\\You\\Downloads\\dump")
    lines.append("  [dim]* copy phone files to laptop first[/]")

    return "\n".join(lines)


def render_split(
    result_renderables: Union[List, str],
    paths: List[Tuple[str, object]],
    console: Console,
) -> None:
    """Print the two-column layout (or single-column on narrow terminals)."""
    term_width = os.get_terminal_size(fallback=(80, 24)).columns

    right_content = _build_right_panel(paths)
    right_panel = Panel(right_content, title="Reference", border_style="blue")

    if isinstance(result_renderables, str):
        result_renderables = [result_renderables]

    left_group = Group(*result_renderables)
    left_panel = Panel(left_group, title="Results", border_style="green")

    if term_width < NARROW_THRESHOLD:
        console.print(left_panel)
        console.print(right_panel)
        return

    layout = Layout()
    layout.split_row(
        Layout(left_panel, name="left", ratio=3),
        Layout(right_panel, name="right", ratio=2),
    )
    console.print(layout)


def render_welcome(console: Console) -> None:
    """Print the banner shown at REPL startup."""
    from media_backup import __version__
    console.print()
    console.print(f"  [bold]Media Backup Tool[/]  v{__version__}")
    console.print("  Type [bold cyan]help[/] for commands, [bold cyan]quit[/] to exit.")
    console.print()
