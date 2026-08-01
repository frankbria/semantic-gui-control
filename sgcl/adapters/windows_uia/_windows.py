"""Window-level helpers for the Windows UIA adapter.

Like `_walker.py`, `_readers.py` and `_system.py`, this module deliberately
does **not** import `uiautomation`, so it can be imported and exercised on
Linux. `_adapter.py` keeps only the parts that genuinely need the platform:
the `auto.*` calls, DPI awareness, and window enumeration.

The split matters most for the error branches below. A stale or mistyped
window handle is the most common real failure an agent hits, and until these
moved out of the gated module the only way to check them was to run Windows
by hand.
"""

from __future__ import annotations

import os

from sgcl.adapters.windows_uia._system import is_system_surface
from sgcl.adapters.windows_uia._walker import extract_bounds, extract_label
from sgcl.core.schema import WindowInfo

_HWND_PREFIX = "hwnd_"


def parse_window_id(window_id: str) -> int:
    """Extract the Win32 handle from an `hwnd_<int>` id.

    Two distinct rejections, deliberately worded differently: a mistyped
    handle is a different mistake from using the wrong id scheme, and the
    message is what an agent reads to correct itself.

    Raises:
        ValueError: the id is not of the form `hwnd_<int>`.
    """
    if window_id.startswith(_HWND_PREFIX):
        try:
            return int(window_id.removeprefix(_HWND_PREFIX))
        except ValueError:
            raise ValueError(f"Invalid window id: {window_id!r}") from None
    raise ValueError(
        f"Unsupported window id: {window_id!r}. "
        "Only ids of the form 'hwnd_<int>' from `sgcl windows` are supported."
    )


def process_name(pid: int) -> str | None:
    """Look up a process's executable basename by PID via Win32.

    Returns None rather than raising when the lookup is unavailable or
    fails -- including off-Windows, where there is no `ctypes.windll` at
    all. `process_name` is best-effort metadata; a window is still usable
    without it.
    """
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


def build_window_info(ctrl, foreground_hwnd: int) -> WindowInfo:
    """Normalize a UIA window control into a `WindowInfo`.

    Duck-typed: takes whatever object exposes the attributes below, so a
    real UIA control on Windows and a mock on Linux are both fine.

    Falls back to `pid_<n>` when the control reports no window handle --
    some UIA controls do, and they still need an addressable id. Note that
    handle 0 is never `is_active`, so a foreground handle of 0 does not make
    every handle-less window look focused.
    """
    hwnd = int(getattr(ctrl, "NativeWindowHandle", 0) or 0)
    pid = int(getattr(ctrl, "ProcessId", 0) or 0)
    title = extract_label(ctrl) or ""
    name = process_name(pid)
    return WindowInfo(
        id=f"{_HWND_PREFIX}{hwnd}" if hwnd else f"pid_{pid}",
        title=title,
        process_name=name,
        pid=pid,
        bounds=extract_bounds(ctrl),
        visible=not bool(getattr(ctrl, "IsOffscreen", False)),
        is_active=(hwnd != 0 and hwnd == foreground_hwnd),
        is_system_surface=is_system_surface(title, name),
    )
