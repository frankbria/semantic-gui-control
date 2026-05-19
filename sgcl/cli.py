"""SGCL CLI entry point.

Phase 0 commands: `windows`, `active`, `inspect`. JSON to stdout.
See docs/phase-0-observe-spike.md.

Targeting note: `--active` is unreliable from a CLI context, because the
terminal that runs `sgcl` typically holds foreground focus itself. Prefer
`--process`, `--title`, or `--window` for predictable behavior.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from collections.abc import Callable
from typing import Any

from sgcl.core.adapter_base import Adapter
from sgcl.core.schema import WindowInfo

AdapterFactory = Callable[[], Adapter]


def _default_adapter_factory() -> Adapter:
    if sys.platform == "win32":
        from sgcl.adapters.windows_uia import WindowsUIAAdapter

        return WindowsUIAAdapter()
    raise SystemExit(
        f"sgcl: Phase 0 only supports Windows. Current platform: {sys.platform}. "
        "Run from a native Windows shell (PowerShell), not WSL."
    )


def _build_parser() -> argparse.ArgumentParser:
    # `--pretty` and `--output` are accepted both before and after the
    # subcommand. The shared 'common' parser uses SUPPRESS so subparsers
    # don't clobber the value set on the main parser.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Pretty-print JSON output (default: compact).",
    )
    common.add_argument(
        "--output",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help=(
            "Write JSON to PATH (UTF-8) instead of stdout. Bypasses shell "
            "pipe encoding so non-ASCII characters survive on Windows."
        ),
    )

    parser = argparse.ArgumentParser(
        prog="sgcl",
        description="Semantic GUI Control Layer (Phase 0: observe).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (default: compact).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help=(
            "Write JSON to PATH (UTF-8) instead of stdout. Bypasses shell "
            "pipe encoding so non-ASCII characters survive on Windows."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    windows_p = sub.add_parser(
        "windows",
        parents=[common],
        help="List open top-level windows.",
    )
    windows_p.add_argument(
        "--include-system",
        action="store_true",
        help="Include shell/system windows (Taskbar, Program Manager). Default: hide them.",
    )
    sub.add_parser(
        "active",
        parents=[common],
        help="Show the foreground/active window (often the terminal itself; see note).",
    )

    insp = sub.add_parser(
        "inspect",
        parents=[common],
        help="Inspect a window's control tree.",
    )
    insp.add_argument(
        "--include-system",
        action="store_true",
        help=(
            "When matching by --process/--title/--pid, also consider shell/system "
            "windows. Has no effect for --window or --active (those are explicit)."
        ),
    )
    target = insp.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--active",
        action="store_true",
        help=(
            "Inspect the foreground window. NOTE: from a CLI the foreground is "
            "almost always the terminal you're running in; prefer --process/--title/--window."
        ),
    )
    target.add_argument(
        "--window",
        metavar="ID",
        help="Window id from `sgcl windows` (e.g., hwnd_6623598).",
    )
    target.add_argument(
        "--process",
        metavar="NAME",
        help=(
            "Match a window by its process name (case-insensitive; .exe optional). "
            "Errors if multiple windows match."
        ),
    )
    target.add_argument(
        "--title",
        metavar="TEXT",
        help=(
            "Match a window whose title contains TEXT (case-insensitive). "
            "Errors if multiple windows match."
        ),
    )
    target.add_argument(
        "--pid",
        metavar="PID",
        type=int,
        help="Match a window by process id. Errors if multiple windows match.",
    )
    insp.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Max tree depth to walk (default: 3).",
    )
    insp.add_argument(
        "--delay",
        metavar="SEC",
        type=float,
        default=0.0,
        help="Sleep this many seconds before inspecting (use to switch focus first).",
    )

    return parser


def _ensure_utf8_stdout() -> None:
    """Force stdout to UTF-8 so non-ASCII codepoints don't crash on Windows.

    UI Automation labels routinely include icon-font glyphs in the Unicode
    Private Use Area (e.g., Segoe Fluent Icons). Python on Windows defaults
    stdout to cp1252, which can't encode them. UTF-8 with `replace` on
    encode errors keeps us safe even if a future surrogate slips through.
    """
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError, OSError):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _emit(result: Any, pretty: bool, output_path: str | None = None) -> None:
    indent = 2 if pretty else None
    text = json.dumps(result, indent=indent, default=str, ensure_ascii=False)
    if output_path:
        # Writing directly from Python with an explicit UTF-8 file handle
        # avoids the host shell's pipe encoding (PowerShell on Windows
        # decodes our UTF-8 stdout bytes as cp437 by default, which
        # corrupts non-ASCII synonyms and labels). No BOM.
        with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.write("\n")
    else:
        print(text)


def _process_matches(actual: str | None, query: str) -> bool:
    if not actual:
        return False
    a = actual.lower().removesuffix(".exe")
    q = query.lower().removesuffix(".exe")
    return a == q


def _title_matches(actual: str | None, query: str) -> bool:
    if not actual:
        return False
    return query.lower() in actual.lower()


def _filter_windows(
    windows: list[WindowInfo],
    *,
    process: str | None,
    title: str | None,
    pid: int | None,
) -> list[WindowInfo]:
    matches: list[WindowInfo] = []
    for w in windows:
        if pid is not None:
            if w.pid == pid:
                matches.append(w)
            continue
        if process is not None:
            if _process_matches(w.process_name, process):
                matches.append(w)
            continue
        if title is not None and _title_matches(w.title, title):
            matches.append(w)
    return matches


def _resolve_window_id(
    adapter: Adapter,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> str:
    if args.active:
        active = adapter.active_window()
        if active is None:
            parser.error("no foreground window available")
        return active.id
    if args.window:
        return args.window
    candidates = adapter.list_windows()
    if not args.include_system:
        candidates = [w for w in candidates if not w.is_system_surface]
    matches = _filter_windows(
        candidates,
        process=args.process,
        title=args.title,
        pid=args.pid,
    )
    if not matches:
        parser.error("no window matched the given criteria")
    if len(matches) > 1:
        descs = "; ".join(f"{w.id} title={w.title!r}" for w in matches)
        parser.error(
            f"{len(matches)} windows matched: {descs}. "
            "Disambiguate with --window <id> from `sgcl windows`."
        )
    return matches[0].id


def main(
    argv: list[str] | None = None,
    adapter_factory: AdapterFactory = _default_adapter_factory,
) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)

    adapter = adapter_factory()

    if args.cmd == "windows":
        windows = adapter.list_windows()
        if not args.include_system:
            windows = [w for w in windows if not w.is_system_surface]
        result: Any = [w.to_dict() for w in windows]
    elif args.cmd == "active":
        active = adapter.active_window()
        result = active.to_dict() if active is not None else None
    elif args.cmd == "inspect":
        if args.depth < 0:
            parser.error("--depth must be non-negative")
        if args.delay < 0:
            parser.error("--delay must be non-negative")
        window_id = _resolve_window_id(adapter, args, parser)
        if args.delay > 0:
            print(
                f"sgcl: waiting {args.delay}s before inspecting...",
                file=sys.stderr,
            )
            time.sleep(args.delay)
        tree = adapter.inspect_window(window_id, args.depth)
        result = tree.to_dict()
    else:  # pragma: no cover - argparse enforces required subcommand
        parser.error(f"unknown command: {args.cmd}")
        return 2

    _emit(result, args.pretty, getattr(args, "output", None))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
