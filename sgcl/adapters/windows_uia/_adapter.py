"""Windows-only glue for the UIA adapter.

Imports `uiautomation` and Win32 ctypes. The walker and system-surface
heuristic live in their own modules (`_walker.py`, `_system.py`) so the
duck-typed logic can be tested on Linux.
"""

from __future__ import annotations

import os
import sys

if sys.platform != "win32":
    raise ImportError(
        "sgcl.adapters.windows_uia._adapter requires Windows. " "Current platform: " + sys.platform
    )

import uiautomation as auto  # noqa: E402  (platform-gated import)

from sgcl.adapters.windows_uia._readers import read_value  # noqa: E402
from sgcl.adapters.windows_uia._system import is_system_surface  # noqa: E402
from sgcl.adapters.windows_uia._walker import (  # noqa: E402
    build_control,
    extract_bounds,
    extract_label,
    flatten_structural_panes,
    make_id_factory,
)
from sgcl.core.adapter_base import Adapter, ReadResolution  # noqa: E402
from sgcl.core.matcher import Query, match_query  # noqa: E402
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


def _process_name(pid: int) -> str | None:
    """Look up process executable name by PID via Win32. Returns basename or None."""
    if not pid:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
            if not ok:
                return None
            return os.path.basename(buf.value)
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return None


def _find_in_tree(root: Control, target_id: str) -> Control | None:
    if root.id == target_id:
        return root
    for child in root.children:
        found = _find_in_tree(child, target_id)
        if found is not None:
            return found
    return None


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
        hwnd = int(getattr(ctrl, "NativeWindowHandle", 0) or 0)
        pid = int(getattr(ctrl, "ProcessId", 0) or 0)
        title = extract_label(ctrl) or ""
        process_name = _process_name(pid)
        return WindowInfo(
            id=f"hwnd_{hwnd}" if hwnd else f"pid_{pid}",
            title=title,
            process_name=process_name,
            pid=pid,
            bounds=extract_bounds(ctrl),
            visible=not bool(getattr(ctrl, "IsOffscreen", False)),
            is_active=(hwnd != 0 and hwnd == foreground_hwnd),
            is_system_surface=is_system_surface(title, process_name),
        )

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
        if (query is None) == (target_id is None):
            raise ValueError("read() requires exactly one of query / target_id")

        root_uia = self._resolve_window(window_id)
        next_id = make_id_factory("ctrl")
        id_to_uia: dict = {}
        tree = build_control(root_uia, depth, next_id, id_to_uia)
        tree = flatten_structural_panes(tree)

        if target_id is not None:
            control = _find_in_tree(tree, target_id)
            if control is None:
                raise LookupError(f"no control with id {target_id!r}")
        else:
            assert query is not None
            matches = match_query(tree, query)
            if not matches:
                raise LookupError("no control matched the query")
            if len(matches) > 1:
                raise LookupError(f"{len(matches)} controls matched the query")
            control = matches[0].control

        uia_ctrl = id_to_uia.get(control.id)
        if uia_ctrl is None:
            # Should not happen — every normalized control id originates
            # from a build_control visit which populates id_to_uia.
            from sgcl.core.read_result import ReadResult

            return ReadResolution(
                result=ReadResult(supported=False, source="none", value=None),
                control=control,
            )
        result = read_value(uia_ctrl, max_length=max_length)
        return ReadResolution(result=result, control=control)

    def _resolve_window(self, window_id: str):
        if window_id.startswith("hwnd_"):
            try:
                hwnd = int(window_id.removeprefix("hwnd_"))
            except ValueError:
                raise ValueError(f"Invalid window id: {window_id!r}") from None
            ctrl = auto.ControlFromHandle(hwnd)
            if ctrl is None:
                raise LookupError(f"Window {window_id!r} not found (handle no longer valid?).")
            return ctrl
        raise ValueError(
            f"Unsupported window id: {window_id!r}. "
            "Only ids of the form 'hwnd_<int>' from `sgcl windows` are supported."
        )
