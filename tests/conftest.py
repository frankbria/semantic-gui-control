"""Test fixtures.

A FakeAdapter exercises the cross-platform dispatch path on Linux. The real
Windows adapter is platform-gated and only importable on win32.
"""

from __future__ import annotations

import pytest

from sgcl.core.adapter_base import Adapter
from sgcl.core.schema import Bounds, Control, WindowInfo


def _ctrl(
    id_,
    *,
    role,
    label,
    children=None,
    enabled=True,
    visible=True,
    focused=False,
    confidence=1.0,
    synonyms=None,
    description=None,
    bounds=None,
    raw_ref_window_id=None,
) -> Control:
    native = {
        "window": "WindowControl",
        "button": "ButtonControl",
        "text_field": "EditControl",
        "static_text": "TextControl",
        "checkbox": "CheckBoxControl",
        "document": "DocumentControl",
        "pane": "PaneControl",
        "group": "GroupControl",
    }.get(role, role)
    actions = {
        "button": ["focus", "invoke"],
        "text_field": ["focus", "read", "type"],
        "static_text": ["read"],
        "checkbox": ["focus", "invoke"],
        "document": ["focus", "read"],
    }.get(role, ["focus"])
    raw_ref = {"window_id": raw_ref_window_id} if raw_ref_window_id else None
    return Control(
        id=id_,
        role=role,
        native_role=native,
        label=label,
        enabled=enabled,
        visible=visible,
        focused=focused,
        bounds=bounds,
        actions=actions,
        children=children or [],
        confidence=confidence,
        synonyms=list(synonyms) if synonyms else [],
        description=description,
        raw_ref=raw_ref,
    )


class FakeAdapter(Adapter):
    """Test adapter with a richer per-window tree.

    Each window has its own affordance graph that exercises real query
    paths: multiple buttons (some with synonyms), a static_text display,
    an icon-only button with a description. The structure makes synonym
    hits, role-only filters, ambiguity, and relationship selectors all
    testable end-to-end.
    """

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
        if window_id == "hwnd_222":
            tree = self._calculator_tree(window_id)
        elif window_id in {"hwnd_111", "hwnd_333"}:
            tree = self._notepad_tree(target.title, window_id)
        else:
            tree = self._minimal_tree(target.title, window_id)
        return _truncate_depth(tree, depth)

    def _calculator_tree(self, window_id: str) -> Control:
        """Miniature Calculator with keypad, display, and a settings icon."""
        zero = _ctrl("ctrl_zero", role="button", label="Zero", synonyms=["0"])
        plus = _ctrl("ctrl_plus", role="button", label="Plus", synonyms=["+"])
        equals = _ctrl("ctrl_eq", role="button", label="Equals", synonyms=["="])
        pi = _ctrl("ctrl_pi", role="button", label="Pi", synonyms=["π"])
        display = _ctrl(
            "ctrl_display",
            role="static_text",
            label="Display is 0",
            confidence=0.75,
        )
        keypad = _ctrl(
            "ctrl_keypad",
            role="group",
            label="Number pad",
            children=[zero, plus, equals, pi],
        )
        settings = _ctrl(
            "ctrl_settings",
            role="button",
            label="",
            description="icon: Settings",
            confidence=0.75,
        )
        return _ctrl(
            "ctrl_window",
            role="window",
            label="Calculator",
            children=[display, keypad, settings],
            raw_ref_window_id=window_id,
        )

    def _notepad_tree(self, title: str, window_id: str) -> Control:
        """Notepad with editor + status bar + a Save toolbar button."""
        save = _ctrl("ctrl_save", role="button", label="Save")
        toolbar = _ctrl(
            "ctrl_toolbar",
            role="group",
            label="Toolbar",
            children=[save],
        )
        cursor = _ctrl(
            "ctrl_cursor",
            role="static_text",
            label="Line 1, Column 1",
        )
        chars = _ctrl(
            "ctrl_chars",
            role="static_text",
            label="0 characters",
        )
        encoding = _ctrl("ctrl_encoding", role="static_text", label="UTF-8")
        status = _ctrl(
            "ctrl_status",
            role="group",
            label="Status bar",
            children=[cursor, chars, encoding],
        )
        editor = _ctrl(
            "ctrl_editor",
            role="document",
            label="Text editor",
            children=[],
            focused=True,
        )
        return _ctrl(
            "ctrl_window",
            role="window",
            label=title,
            children=[toolbar, editor, status],
            raw_ref_window_id=window_id,
        )

    def _minimal_tree(self, title: str, window_id: str) -> Control:
        return _ctrl(
            "ctrl_window",
            role="window",
            label=title,
            children=[],
            raw_ref_window_id=window_id,
        )


def _truncate_depth(control: Control, depth: int) -> Control:
    """Mutate-in-place truncation so FakeAdapter respects the --depth arg."""
    if depth <= 0:
        control.children = []
        return control
    for child in control.children:
        _truncate_depth(child, depth - 1)
    return control


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def fake_adapter_factory(fake_adapter):
    def factory():
        return fake_adapter

    return factory
