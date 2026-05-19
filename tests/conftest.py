"""Test fixtures.

A FakeAdapter exercises the cross-platform dispatch path on Linux. The real
Windows adapter is platform-gated and only importable on win32.
"""

from __future__ import annotations

import pytest

from sgcl.core.adapter_base import Adapter
from sgcl.core.schema import Bounds, Control, WindowInfo


class FakeAdapter(Adapter):
    name = "fake"
    platform = "fake"

    def __init__(self) -> None:
        self._windows = [
            WindowInfo(
                id="hwnd_111",
                title="Untitled - Notepad",
                process_name="Notepad.exe",
                pid=1234,
                bounds=Bounds(0, 0, 800, 600),
                visible=True,
                is_active=True,
            ),
            WindowInfo(
                id="hwnd_222",
                title="Calculator",
                process_name="Calculator.exe",
                pid=5678,
                bounds=Bounds(100, 100, 400, 500),
                visible=True,
                is_active=False,
            ),
            WindowInfo(
                id="hwnd_333",
                title="second.txt - Notepad",
                process_name="Notepad.exe",
                pid=9999,
                bounds=Bounds(50, 50, 800, 600),
                visible=True,
                is_active=False,
            ),
            WindowInfo(
                id="hwnd_444",
                title="Taskbar",
                process_name="explorer.exe",
                pid=684,
                bounds=Bounds(0, 1380, 3440, 60),
                visible=True,
                is_active=False,
                is_system_surface=True,
            ),
        ]
        self.active_returns: WindowInfo | None = self._windows[0]

    def list_windows(self) -> list[WindowInfo]:
        return list(self._windows)

    def active_window(self) -> WindowInfo | None:
        return self.active_returns

    def inspect_window(self, window_id: str, depth: int) -> Control:
        target = next((w for w in self._windows if w.id == window_id), None)
        if target is None:
            raise LookupError(f"unknown window {window_id!r}")
        # The label echoes the window id so tests can verify the right window
        # was the target.
        root = Control(
            id="ctrl_0",
            role="window",
            native_role="WindowControl",
            label=target.title,
            enabled=True,
            visible=True,
            focused=target.is_active,
            bounds=target.bounds,
            actions=["focus"],
            children=[],
            raw_ref={"window_id": target.id},
        )
        if depth > 0:
            root.children.append(
                Control(
                    id="ctrl_1",
                    role="text_field",
                    native_role="EditControl",
                    label="",
                    enabled=True,
                    visible=True,
                    focused=False,
                    bounds=Bounds(0, 30, 800, 570),
                    actions=["focus", "read", "type"],
                    children=[],
                )
            )
        return root


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def fake_adapter_factory(fake_adapter):
    def factory():
        return fake_adapter

    return factory
