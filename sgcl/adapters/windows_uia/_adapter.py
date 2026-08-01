"""Windows-only glue for the UIA adapter.

This module holds **only** what genuinely needs the platform: the
`uiautomation` import, DPI awareness, and the `auto.*` calls that enumerate
and resolve windows. Everything duck-typed lives in a sibling that does not
import `uiautomation`, so it can be tested on Linux:

- `_walker.py` — tree building, role mapping, action inference
- `_readers.py` — pattern-based value extraction
- `_system.py` — shell/system-surface heuristic
- `_windows.py` — window-id parsing, `WindowInfo` construction, process names

The resolution policy shared with every other adapter is in
`sgcl/core/resolve.py`.

What remains here is reachable only from a real Windows session, and is
therefore omitted from coverage measurement (see `pyproject.toml`). Keep it
that way: if something here can be written without touching `auto.*`, it
belongs in a sibling where a test can reach it.
"""

from __future__ import annotations

import sys

if sys.platform != "win32":
    raise ImportError(
        "sgcl.adapters.windows_uia._adapter requires Windows. " "Current platform: " + sys.platform
    )

import uiautomation as auto  # noqa: E402  (platform-gated import)

from sgcl.adapters.windows_uia._readers import read_value  # noqa: E402
from sgcl.adapters.windows_uia._walker import (  # noqa: E402
    build_control,
    flatten_structural_panes,
    make_id_factory,
)
from sgcl.adapters.windows_uia._windows import build_window_info, parse_window_id  # noqa: E402
from sgcl.core.adapter_base import Adapter, ReadResolution  # noqa: E402
from sgcl.core.matcher import Query  # noqa: E402
from sgcl.core.resolve import require_exactly_one, resolve_one  # noqa: E402
from sgcl.core.schema import Control, WindowInfo  # noqa: E402


def _enable_dpi_awareness() -> None:
    """Mark the process as per-monitor DPI aware so bounds aren't auto-scaled.

    Best-effort: silently no-ops on Windows versions that don't support it or
    when DPI awareness has already been set.
    """
    import contextlib

    with contextlib.suppress(Exception):
        import ctypes

        # PER_MONITOR_AWARE_V2 = -4 (Win10 1703+)
        ctx = ctypes.c_void_p(-4)
        with contextlib.suppress(AttributeError, OSError):
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctx)
            return
        # Fallback: PROCESS_PER_MONITOR_DPI_AWARE = 2 (Win8.1+)
        with contextlib.suppress(AttributeError, OSError):
            ctypes.windll.shcore.SetProcessDpiAwareness(2)


class WindowsUIAAdapter(Adapter):
    """Read-only adapter against Windows UI Automation."""

    def __init__(self) -> None:
        _enable_dpi_awareness()

    @property
    def name(self) -> str:
        return "windows_uia"

    @property
    def platform(self) -> str:
        return "windows"

    # ---- windows ----

    def _foreground_hwnd(self) -> int:
        try:
            return int(auto.GetForegroundWindow())
        except Exception:
            return 0

    def _window_info(self, ctrl, foreground_hwnd: int) -> WindowInfo:
        return build_window_info(ctrl, foreground_hwnd)

    def list_windows(self) -> list[WindowInfo]:
        foreground = self._foreground_hwnd()
        desktop = auto.GetRootControl()
        windows: list[WindowInfo] = []
        for child in desktop.GetChildren():
            try:
                if not child.IsTopLevel():
                    continue
            except Exception:
                pass
            try:
                windows.append(self._window_info(child, foreground))
            except Exception:
                continue
        return windows

    def active_window(self) -> WindowInfo | None:
        try:
            ctrl = auto.GetForegroundControl()
        except Exception:
            return None
        if ctrl is None:
            return None
        return self._window_info(ctrl, self._foreground_hwnd())

    # ---- inspect ----

    def inspect_window(self, window_id: str, depth: int) -> Control:
        ctrl = self._resolve_window(window_id)
        next_id = make_id_factory("ctrl")
        tree = build_control(ctrl, depth, next_id)
        return flatten_structural_panes(tree)

    def read(
        self,
        window_id: str,
        *,
        query: Query | None = None,
        target_id: str | None = None,
        depth: int = 8,
        max_length: int = 4096,
    ) -> ReadResolution:
        require_exactly_one(query, target_id)

        root_uia = self._resolve_window(window_id)
        next_id = make_id_factory("ctrl")
        id_to_uia: dict = {}
        tree = build_control(root_uia, depth, next_id, id_to_uia)
        tree = flatten_structural_panes(tree)

        control = resolve_one(tree, query=query, target_id=target_id)

        # Every control in the flattened tree came from a build_control
        # visit, and build_control records each visited node in id_to_uia --
        # flattening drops nodes from the tree but never from the map. So
        # this lookup cannot miss; there is no fallback branch to take.
        result = read_value(id_to_uia[control.id], max_length=max_length)
        return ReadResolution(result=result, control=control)

    def _resolve_window(self, window_id: str):
        hwnd = parse_window_id(window_id)
        ctrl = auto.ControlFromHandle(hwnd)
        if ctrl is None:
            raise LookupError(f"Window {window_id!r} not found (handle no longer valid?).")
        return ctrl
