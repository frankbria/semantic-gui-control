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
                process_name="notepad.exe",
                pid=1234,
                bounds=Bounds(0, 0, 800, 600),
                visible=True,
                is_active=True,
            ),
            WindowInfo(
                id="hwnd_222",
                title="Calculator",
                process_name="calculator.exe",
                pid=5678,
                bounds=Bounds(100, 100, 400, 500),
                visible=True,
                is_active=False,
            ),
        ]
        self.active_returns: WindowInfo | None = self._windows[0]

    def list_windows(self) -> list[WindowInfo]:
        return list(self._windows)

    def active_window(self) -> WindowInfo | None:
        return self.active_returns

    def inspect_window(self, window_id: str, depth: int) -> Control:
        if not any(w.id == window_id for w in self._windows):
            raise LookupError(f"unknown window {window_id!r}")
        return self._build_tree(window_id, depth)

    def inspect_active(self, depth: int) -> Control:
        if self.active_returns is None:
            raise RuntimeError("no active window")
        return self._build_tree(self.active_returns.id, depth)

    def _build_tree(self, window_id: str, depth: int) -> Control:
        root = Control(
            id="ctrl_0",
            role="window",
            native_role="WindowControl",
            label="Untitled - Notepad",
            enabled=True,
            visible=True,
            focused=True,
            bounds=Bounds(0, 0, 800, 600),
            actions=["focus"],
            children=[],
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
                    focused=True,
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
