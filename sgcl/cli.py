"""SGCL CLI entry point.

Phase 0 commands: `windows`, `active`, `inspect`. JSON to stdout.
See docs/phase-0-observe-spike.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from typing import Any

from sgcl.core.adapter_base import Adapter

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
    # `--pretty` is accepted both before and after the subcommand.
    # The shared 'common' parser uses SUPPRESS so subparsers don't clobber
    # the value set on the main parser.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Pretty-print JSON output (default: compact).",
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
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "windows",
        parents=[common],
        help="List open top-level windows.",
    )
    sub.add_parser(
        "active",
        parents=[common],
        help="Show the foreground/active window.",
    )

    insp = sub.add_parser(
        "inspect",
        parents=[common],
        help="Inspect a window's control tree.",
    )
    target = insp.add_mutually_exclusive_group(required=True)
    target.add_argument("--active", action="store_true", help="Inspect the active window.")
    target.add_argument("--window", metavar="ID", help="Window id from `sgcl windows`.")
    insp.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Max tree depth to walk (default: 3).",
    )

    return parser


def _emit(result: Any, pretty: bool) -> None:
    indent = 2 if pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


def main(
    argv: list[str] | None = None,
    adapter_factory: AdapterFactory = _default_adapter_factory,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    adapter = adapter_factory()

    if args.cmd == "windows":
        result: Any = [w.to_dict() for w in adapter.list_windows()]
    elif args.cmd == "active":
        active = adapter.active_window()
        result = active.to_dict() if active is not None else None
    elif args.cmd == "inspect":
        if args.depth < 0:
            parser.error("--depth must be non-negative")
        if args.active:
            tree = adapter.inspect_active(args.depth)
        else:
            tree = adapter.inspect_window(args.window, args.depth)
        result = tree.to_dict()
    else:  # pragma: no cover - argparse enforces required subcommand
        parser.error(f"unknown command: {args.cmd}")
        return 2

    _emit(result, args.pretty)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
