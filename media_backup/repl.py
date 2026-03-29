"""Interactive REPL: prompt_toolkit loop with tab-completion and command dispatch."""

from __future__ import annotations

import shlex
from typing import List, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from media_backup import comparators, reporter
from media_backup.help_panel import render_split, render_welcome
from media_backup.session import Session

console = Console()

COMMANDS = [
    "set", "unset", "paths", "help", "quit", "exit",
    "sync-check", "coverage-check", "safe-to-clear", "duplicates", "timeline-gaps",
]


class _Completer(Completer):
    """Tab-completes command names and session path names."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        word = document.get_word_before_cursor()

        if len(words) <= 1:
            for cmd in COMMANDS:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
        else:
            for name in self._session.names:
                if name.startswith(word):
                    yield Completion(name, start_position=-len(word))


def _show(result_parts, session: Session) -> None:
    """Render results via the split layout."""
    if isinstance(result_parts, str):
        result_parts = [result_parts]
    render_split(result_parts, session.list_paths(), console)


def _parse_min_gap(args: List[str]) -> Tuple[int, List[str]]:
    """Extract --min-gap N from args, return (value, remaining args)."""
    min_gap = 7
    filtered: List[str] = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == "--min-gap" and i + 1 < len(args):
            try:
                val = int(args[i + 1])
                if val > 0:
                    min_gap = val
            except ValueError:
                pass
            skip_next = True
        else:
            filtered.append(arg)
    return min_gap, filtered


def _dispatch(line: str, session: Session) -> bool:
    """Handle one command.  Returns False to signal quit."""
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = line.strip().split()

    if not parts:
        return True

    cmd = parts[0].lower()
    args = parts[1:]

    # ---- session management ----

    if cmd == "set":
        if len(args) < 2:
            _show(["[red]Usage: set <name> <path>[/]"], session)
            return True
        name = args[0]
        path = " ".join(args[1:])
        p, exists = session.set(name, path)
        parts = [f"[green]✓ {name} = {p}[/]"]
        if not exists:
            parts.append(f"[bold yellow]⚠ Warning: path does not exist: {p}[/]")
        _show(parts, session)
        return True

    if cmd == "unset":
        if not args:
            _show(["[red]Usage: unset <name>[/]"], session)
            return True
        name = args[0]
        if session.unset(name):
            _show([f"[green]✓ Removed {name}[/]"], session)
        else:
            _show([f"[yellow]{name} was not set.[/]"], session)
        return True

    if cmd == "paths":
        paths = session.list_paths()
        if not paths:
            _show(["[dim]No paths set.[/]"], session)
        else:
            lines = [f"  [bold]{n:<10}[/] {p}" for n, p in paths]
            _show(lines, session)
        return True

    if cmd == "help":
        help_lines = [
            "[bold underline]Commands[/]",
            "  [bold cyan]sync-check[/]                    SSD vs HDD — path structure diff",
            "  [bold cyan]coverage-check <src> <tgt>[/]    Every file from src found in tgt?",
            "  [bold cyan]safe-to-clear <dir>[/]           Safe to delete this laptop dir?",
            "  [bold cyan]duplicates <dir>[/]              Same file in multiple subdirs?",
            "  [bold cyan]timeline-gaps <dir>[/]           Date gaps across entire drive",
            "",
            "  [bold cyan]set <name> <path>[/]             Register a named path",
            "  [bold cyan]unset <name>[/]                  Remove a named path",
            "  [bold cyan]paths[/]                         List all current paths",
            "  [bold cyan]quit[/] / [bold cyan]exit[/]                    End session",
        ]
        _show(help_lines, session)
        return True

    if cmd in ("quit", "exit"):
        console.print("\n  [dim]Goodbye.[/]\n")
        return False

    # ---- checks ----

    if cmd == "sync-check":
        if not session.has_drives():
            missing = ", ".join(session.missing_drives())
            _show([f"[bold red]Cannot run sync-check: {missing} not set.[/]"], session)
            return True
        ssd = session.get("SSD")
        hdd = session.get("HDD")
        result = comparators.sync_check(ssd, hdd, cache=session.cache)
        _show(reporter.render_sync(result), session)
        return True

    if cmd == "coverage-check":
        if len(args) < 2:
            _show(["[red]Usage: coverage-check <source> <target>[/]"], session)
            return True
        src_label, src_path = session.resolve(args[0])
        tgt_label, tgt_path = session.resolve(args[1])
        if src_path is None:
            _show([f"[red]Path not found: {args[0]}[/]"], session)
            return True
        if tgt_path is None:
            _show([f"[red]Path not found: {args[1]}[/]"], session)
            return True
        result = comparators.coverage_check(
            src_path, tgt_path, src_label, tgt_label, cache=session.cache,
        )
        _show(reporter.render_coverage(result, src_label, tgt_label), session)
        return True

    if cmd == "safe-to-clear":
        if not session.has_drives():
            missing = ", ".join(session.missing_drives())
            _show([f"[bold red]Cannot run safe-to-clear: {missing} not set.[/]"], session)
            return True
        if not args:
            _show(["[red]Usage: safe-to-clear <name_or_path>[/]"], session)
            return True
        label, path = session.resolve(args[0])
        if path is None:
            _show([f"[red]Path not found: {args[0]}[/]"], session)
            return True
        ssd = session.get("SSD")
        hdd = session.get("HDD")
        result = comparators.safe_to_clear(
            path, ssd, hdd, label, cache=session.cache,
        )
        _show(reporter.render_safe_to_clear(result, label), session)
        return True

    if cmd == "duplicates":
        if not args:
            _show(["[red]Usage: duplicates <name_or_path>[/]"], session)
            return True
        label, path = session.resolve(args[0])
        if path is None:
            _show([f"[red]Path not found: {args[0]}[/]"], session)
            return True
        groups = comparators.find_duplicates(path, label, cache=session.cache)
        _show(reporter.render_duplicates(groups), session)
        return True

    if cmd == "timeline-gaps":
        if not args:
            _show(["[red]Usage: timeline-gaps <name_or_path> [--min-gap N][/]"], session)
            return True
        min_gap, remaining = _parse_min_gap(args)
        if not remaining:
            _show(["[red]Usage: timeline-gaps <name_or_path> [--min-gap N][/]"], session)
            return True
        label, path = session.resolve(remaining[0])
        if path is None:
            _show([f"[red]Path not found: {remaining[0]}[/]"], session)
            return True
        gaps, earliest, latest = comparators.timeline_gaps(
            path, label, min_gap, cache=session.cache,
        )
        _show(reporter.render_timeline_gaps(gaps, earliest, latest, min_gap), session)
        return True

    _show([f"[red]Unknown command: {cmd}[/]  Type [bold cyan]help[/] for commands."], session)
    return True


def run() -> None:
    """Start the interactive REPL."""
    session = Session()
    render_welcome(console)

    prompt_session: PromptSession = PromptSession(
        history=InMemoryHistory(),
        completer=_Completer(session),
    )

    while True:
        try:
            line = prompt_session.prompt("> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n  [dim]Goodbye.[/]\n")
            break

        if not line.strip():
            continue

        if not _dispatch(line, session):
            break
