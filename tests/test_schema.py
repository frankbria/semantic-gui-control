from __future__ import annotations

import json

from sgcl.core.schema import Bounds, Control, WindowInfo


def test_bounds_to_dict():
    b = Bounds(10, 20, 80, 30)
    assert b.to_dict() == {"x": 10, "y": 20, "width": 80, "height": 30}


def test_window_info_to_dict_with_bounds():
    w = WindowInfo(
        id="hwnd_1",
        title="Notepad",
        process_name="notepad.exe",
        pid=42,
        bounds=Bounds(0, 0, 100, 100),
        visible=True,
        is_active=True,
    )
    d = w.to_dict()
    assert d["title"] == "Notepad"
    assert d["bounds"] == {"x": 0, "y": 0, "width": 100, "height": 100}
    assert d["is_active"] is True


def test_window_info_to_dict_without_bounds():
    w = WindowInfo(
        id="pid_99",
        title="Headless",
        process_name=None,
        pid=99,
        bounds=None,
        visible=False,
        is_active=False,
    )
    d = w.to_dict()
    assert d["bounds"] is None
    assert d["process_name"] is None


def test_control_to_dict_serializes_nested_children():
    leaf = Control(
        id="ctrl_2",
        role="button",
        native_role="ButtonControl",
        label="Save",
        enabled=True,
        visible=True,
        focused=False,
        bounds=Bounds(10, 20, 80, 30),
        actions=["focus", "invoke"],
    )
    root = Control(
        id="ctrl_0",
        role="window",
        native_role="WindowControl",
        label="Notepad",
        enabled=True,
        visible=True,
        focused=True,
        bounds=Bounds(0, 0, 800, 600),
        actions=["focus"],
        children=[leaf],
        raw_ref={"AutomationId": "MainWindow"},
    )
    d = root.to_dict()
    assert d["id"] == "ctrl_0"
    assert d["children"][0]["label"] == "Save"
    assert d["raw_ref"] == {"AutomationId": "MainWindow"}
    # Round-trips through JSON cleanly.
    text = json.dumps(d)
    again = json.loads(text)
    assert again["children"][0]["actions"] == ["focus", "invoke"]


def test_control_actions_list_is_independent_copy():
    actions = ["focus", "invoke"]
    c = Control(
        id="ctrl_0",
        role="button",
        native_role="ButtonControl",
        label="OK",
        enabled=True,
        visible=True,
        focused=False,
        bounds=None,
        actions=actions,
    )
    d = c.to_dict()
    d["actions"].append("mutated")
    assert c.actions == ["focus", "invoke"]
