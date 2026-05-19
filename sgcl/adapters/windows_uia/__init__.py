"""Windows UI Automation adapter (Phase 0).

Implements the Adapter contract against Yinkaisheng's `uiautomation` library.
Phase 0 is read-only: window enumeration, active window lookup, hierarchical
inspection. No clicking, typing, or vision.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from sgcl.core.adapter_base import Adapter
from sgcl.core.schema import Bounds, Control, WindowInfo

if sys.platform != "win32":
    raise ImportError(
        "sgcl.adapters.windows_uia requires Windows. " "Current platform: " + sys.platform
    )

import uiautomation as auto  # noqa: E402  (platform-gated import)

_UIA_TO_ROLE: dict[str, str] = {
    "WindowControl": "window",
    "PaneControl": "pane",
    "DialogControl": "dialog",
    "ButtonControl": "button",
    "HyperlinkControl": "link",
    "MenuControl": "menu",
    "MenuBarControl": "menu_bar",
    "MenuItemControl": "menu_item",
    "ToolBarControl": "toolbar",
    "TabControl": "tab",
    "TabItemControl": "tab_item",
    "EditControl": "text_field",
    "DocumentControl": "document",
    "TextControl": "static_text",
    "ImageControl": "image",
    "CheckBoxControl": "checkbox",
    "RadioButtonControl": "radio",
    "ComboBoxControl": "combo",
    "ListControl": "list",
    "ListItemControl": "list_item",
    "TreeControl": "tree",
    "TreeItemControl": "tree_item",
    "TableControl": "table",
    "DataItemControl": "row",
    "DataGridControl": "table",
    "HeaderControl": "header",
    "HeaderItemControl": "header_item",
    "GroupControl": "group",
    "ScrollBarControl": "scroll_bar",
    "StatusBarControl": "status_bar",
    "TitleBarControl": "title_bar",
    "ToolTipControl": "tooltip",
    "SliderControl": "slider",
    "SpinnerControl": "spinner",
    "ProgressBarControl": "progress_bar",
    "CalendarControl": "calendar",
    "SeparatorControl": "separator",
    "ThumbControl": "thumb",
    "SemanticZoomControl": "semantic_zoom",
    "AppBarControl": "app_bar",
    "SplitButtonControl": "split_button",
    "CustomControl": "custom",
}


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


def _normalize_role(native: str | None) -> str:
    if not native:
        return "unknown"
    return _UIA_TO_ROLE.get(native, native)


def _bounds(ctrl) -> Bounds | None:
    try:
        rect = ctrl.BoundingRectangle
        if rect is None:
            return None
        w_attr = getattr(rect, "width", None)
        h_attr = getattr(rect, "height", None)
        width = w_attr() if callable(w_attr) else (rect.right - rect.left)
        height = h_attr() if callable(h_attr) else (rect.bottom - rect.top)
        # Degenerate (0,0,0,0) rectangles are common for offscreen controls;
        # emit them as-is so downstream can decide how to interpret.
        return Bounds(
            x=int(rect.left),
            y=int(rect.top),
            width=int(width),
            height=int(height),
        )
    except Exception:
        return None


def _infer_actions(ctrl) -> list[str]:
    actions: list[str] = []

    def add(a: str) -> None:
        if a not in actions:
            actions.append(a)

    try:
        if getattr(ctrl, "IsKeyboardFocusable", False):
            add("focus")
    except Exception:
        pass

    try:
        if ctrl.GetInvokePattern() is not None:
            add("focus")
            add("invoke")
    except Exception:
        pass

    try:
        vp = ctrl.GetValuePattern()
        if vp is not None:
            add("read")
            try:
                if not vp.IsReadOnly:
                    add("type")
            except Exception:
                add("type")
    except Exception:
        pass

    try:
        if ctrl.GetTogglePattern() is not None:
            add("invoke")
    except Exception:
        pass

    try:
        if ctrl.GetSelectionItemPattern() is not None:
            add("select")
    except Exception:
        pass

    try:
        if ctrl.GetScrollPattern() is not None:
            add("scroll")
    except Exception:
        pass

    try:
        if ctrl.GetTextPattern() is not None:
            add("read")
    except Exception:
        pass

    return actions


def _raw_ref(ctrl) -> dict[str, Any]:
    """Debug payload — adapter-specific. Not for agent reasoning."""
    raw: dict[str, Any] = {}
    for attr in ("ControlTypeName", "ClassName", "AutomationId", "LocalizedControlType"):
        try:
            v = getattr(ctrl, attr, None)
            if v:
                raw[attr] = v
        except Exception:
            pass
    try:
        hwnd = getattr(ctrl, "NativeWindowHandle", 0)
        if hwnd:
            raw["NativeWindowHandle"] = int(hwnd)
    except Exception:
        pass
    return raw


def _label(ctrl) -> str | None:
    try:
        name = getattr(ctrl, "Name", None)
        if name is None:
            return None
        name = str(name).strip()
        return name if name else None
    except Exception:
        return None


def _make_id_factory(prefix: str = "ctrl"):
    counter = {"n": 0}

    def next_id() -> str:
        i = counter["n"]
        counter["n"] += 1
        return f"{prefix}_{i}"

    return next_id


def _build_control(ctrl, depth_remaining: int, next_id) -> Control:
    """Depth-first preorder build. Parent gets an id before its children."""
    my_id = next_id()
    native = getattr(ctrl, "ControlTypeName", None) or "Unknown"

    children: list[Control] = []
    if depth_remaining > 0:
        try:
            for child in ctrl.GetChildren():
                children.append(_build_control(child, depth_remaining - 1, next_id))
        except Exception:
            pass

    return Control(
        id=my_id,
        role=_normalize_role(native),
        native_role=native,
        label=_label(ctrl),
        enabled=bool(getattr(ctrl, "IsEnabled", True)),
        visible=not bool(getattr(ctrl, "IsOffscreen", False)),
        focused=bool(getattr(ctrl, "HasKeyboardFocus", False)),
        bounds=_bounds(ctrl),
        actions=_infer_actions(ctrl),
        children=children,
        raw_ref=_raw_ref(ctrl),
    )


class WindowsUIAAdapter(Adapter):
    """Phase 0 read-only adapter against Windows UI Automation."""

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
        title = _label(ctrl) or ""
        return WindowInfo(
            id=f"hwnd_{hwnd}" if hwnd else f"pid_{pid}",
            title=title,
            process_name=_process_name(pid),
            pid=pid,
            bounds=_bounds(ctrl),
            visible=not bool(getattr(ctrl, "IsOffscreen", False)),
            is_active=(hwnd != 0 and hwnd == foreground_hwnd),
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

    def _inspect_ctrl(self, ctrl, depth: int) -> Control:
        next_id = _make_id_factory("ctrl")
        return _build_control(ctrl, depth, next_id)

    def inspect_window(self, window_id: str, depth: int) -> Control:
        ctrl = self._resolve_window(window_id)
        return self._inspect_ctrl(ctrl, depth)

    def inspect_active(self, depth: int) -> Control:
        ctrl = auto.GetForegroundControl()
        if ctrl is None:
            raise RuntimeError("No foreground window available.")
        return self._inspect_ctrl(ctrl, depth)

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
            "Phase 0 only supports ids of the form 'hwnd_<int>' from `sgcl windows`."
        )


__all__ = ["WindowsUIAAdapter"]
