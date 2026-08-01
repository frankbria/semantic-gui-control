"""Linux-runnable tests for the Windows adapter's platform-neutral helpers.

`_adapter.py` is the one module binding the system to a real platform, and
it had zero automated coverage -- its error branches for stale and malformed
window handles, the most common real failure the CLI surfaces, were verified
only by hand on Windows.

The package was already split so duck-typed logic could be tested off-Windows
(`_walker.py`, `_readers.py`, `_system.py`). The same treatment was never
applied to what stayed behind. `_windows.py` is that: window-id parsing and
`WindowInfo` construction, neither of which needs `uiautomation`.

What genuinely cannot be tested here stays in the gated module and is named
as Windows-only in the PR: `_enable_dpi_awareness`, `list_windows`,
`active_window`, and the `auto.*` calls inside `_resolve_window` and
`inspect_window`.
"""

from __future__ import annotations

import pytest

from sgcl.adapters.windows_uia import _windows
from sgcl.adapters.windows_uia._windows import (
    build_window_info,
    parse_window_id,
    process_name,
)
from sgcl.core.schema import WindowInfo


class _Rect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class _FakeWindow:
    """Mirrors the UIA control attributes `build_window_info` reads."""

    def __init__(
        self,
        *,
        NativeWindowHandle=4242,
        ProcessId=99,
        Name="Untitled - Notepad",
        IsOffscreen=False,
        BoundingRectangle=None,
    ):
        self.NativeWindowHandle = NativeWindowHandle
        self.ProcessId = ProcessId
        self.Name = Name
        self.IsOffscreen = IsOffscreen
        self.BoundingRectangle = BoundingRectangle or _Rect(0, 0, 800, 600)


# ---- parse_window_id ----


def test_parses_a_well_formed_handle():
    assert parse_window_id("hwnd_4242") == 4242


def test_parses_zero_handle():
    assert parse_window_id("hwnd_0") == 0


def test_malformed_handle_raises_value_error():
    """`hwnd_` prefix present but the remainder is not an integer."""
    with pytest.raises(ValueError, match="Invalid window id"):
        parse_window_id("hwnd_abc")


def test_unsupported_id_form_names_the_supported_one():
    """The error has to teach, not just reject -- this is agent-facing."""
    with pytest.raises(ValueError, match="hwnd_<int>") as exc:
        parse_window_id("pid_123")
    assert "pid_123" in str(exc.value)


def test_bare_string_is_rejected_as_unsupported():
    with pytest.raises(ValueError, match="Unsupported window id"):
        parse_window_id("Calculator")


def test_empty_id_is_rejected():
    with pytest.raises(ValueError, match="Unsupported window id"):
        parse_window_id("")


def test_the_two_rejections_are_distinguishable():
    """Malformed-handle and wrong-scheme are different mistakes.

    Both raise ValueError, but an agent reading the message should be able
    to tell "you mistyped the number" from "you used the wrong id scheme".
    """
    with pytest.raises(ValueError) as malformed:
        parse_window_id("hwnd_xyz")
    with pytest.raises(ValueError) as wrong_scheme:
        parse_window_id("xyz")
    assert str(malformed.value) != str(wrong_scheme.value)


# ---- build_window_info ----


def test_builds_window_info_from_a_control():
    info = build_window_info(_FakeWindow(), foreground_hwnd=0)
    assert isinstance(info, WindowInfo)
    assert info.id == "hwnd_4242"
    assert info.title == "Untitled - Notepad"
    assert info.pid == 99
    assert info.visible is True
    assert info.bounds.width == 800 and info.bounds.height == 600


def test_id_falls_back_to_pid_when_there_is_no_window_handle():
    """Some UIA controls report handle 0; they still need an addressable id."""
    info = build_window_info(_FakeWindow(NativeWindowHandle=0, ProcessId=77), foreground_hwnd=0)
    assert info.id == "pid_77"


def test_is_active_only_when_the_handle_matches_the_foreground():
    ctrl = _FakeWindow(NativeWindowHandle=4242)
    assert build_window_info(ctrl, foreground_hwnd=4242).is_active is True
    assert build_window_info(ctrl, foreground_hwnd=1111).is_active is False


def test_handle_zero_is_never_active_even_if_foreground_is_zero():
    """0 == 0 must not read as "this window is focused"."""
    info = build_window_info(_FakeWindow(NativeWindowHandle=0), foreground_hwnd=0)
    assert info.is_active is False


def test_offscreen_window_is_not_visible():
    info = build_window_info(_FakeWindow(IsOffscreen=True), foreground_hwnd=0)
    assert info.visible is False


def test_missing_title_becomes_empty_string_not_none():
    info = build_window_info(_FakeWindow(Name=None), foreground_hwnd=0)
    assert info.title == ""


def test_system_surface_wiring_passes_title_and_process_name(monkeypatch):
    """Shell surfaces are tagged so `sgcl windows` can hide them by default.

    `is_system_surface` needs the owning process to be `explorer.exe`, and
    `process_name` can only ever return None off-Windows -- so the lookup is
    patched. What this asserts is the *wiring*: that `build_window_info`
    feeds both the title and the resolved process name into the heuristic.
    The heuristic's own rules are covered in `tests/test_walker.py`.
    """
    monkeypatch.setattr(_windows, "process_name", lambda pid: "explorer.exe")

    assert build_window_info(_FakeWindow(Name="Taskbar"), foreground_hwnd=0).is_system_surface
    assert build_window_info(_FakeWindow(Name=""), foreground_hwnd=0).is_system_surface
    # A real Explorer folder window is not a shell surface.
    assert not build_window_info(_FakeWindow(Name="Documents"), foreground_hwnd=0).is_system_surface


def test_not_a_system_surface_when_the_process_is_unknown():
    """Off-Windows `process_name` is always None, so nothing is tagged."""
    info = build_window_info(_FakeWindow(Name="Taskbar"), foreground_hwnd=0)
    assert info.is_system_surface is False


# ---- process_name ----


def test_process_name_of_pid_zero_is_none():
    assert process_name(0) is None


def test_process_name_degrades_to_none_off_windows():
    """No Win32 here, so the lookup fails and must return None, not raise.

    This is the behaviour that lets `build_window_info` be tested on Linux
    at all -- the function swallows the failure by design.
    """
    assert process_name(99999) is None
