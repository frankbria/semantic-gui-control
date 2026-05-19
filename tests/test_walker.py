"""Tests for the duck-typed Windows UIA walker.

The walker doesn't import `uiautomation`, so these tests run on any
platform. We pass in mock controls that mimic the attributes the real
UIA `Control` objects expose.
"""

from __future__ import annotations

from sgcl.adapters.windows_uia._system import is_system_surface
from sgcl.adapters.windows_uia._walker import (
    build_control,
    extract_bounds,
    extract_label,
    flatten_structural_panes,
    infer_actions,
    make_id_factory,
    normalize_role,
)
from sgcl.core.schema import Control


class _Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


class _FakeCtrl:
    """Mocks the UIA Control interface used by the walker."""

    def __init__(
        self,
        *,
        ControlTypeName="ButtonControl",
        Name="OK",
        AutomationId="btnOK",
        ClassName="Button",
        IsEnabled=True,
        IsOffscreen=False,
        HasKeyboardFocus=False,
        IsKeyboardFocusable=True,
        NativeWindowHandle=0,
        BoundingRectangle=None,
        children=None,
        children_error=None,
    ):
        self.ControlTypeName = ControlTypeName
        self.Name = Name
        self.AutomationId = AutomationId
        self.ClassName = ClassName
        self.IsEnabled = IsEnabled
        self.IsOffscreen = IsOffscreen
        self.HasKeyboardFocus = HasKeyboardFocus
        self.IsKeyboardFocusable = IsKeyboardFocusable
        self.NativeWindowHandle = NativeWindowHandle
        self.BoundingRectangle = BoundingRectangle or _Rect(0, 0, 100, 30)
        self.LocalizedControlType = "button"
        self._children = children or []
        self._children_error = children_error

    def GetChildren(self):
        if self._children_error is not None:
            raise self._children_error
        return self._children

    # Patterns. Default: only Invoke supported (button-shaped).
    def GetInvokePattern(self):
        return object()

    def GetValuePattern(self):
        return None

    def GetTogglePattern(self):
        return None

    def GetSelectionItemPattern(self):
        return None

    def GetScrollPattern(self):
        return None

    def GetTextPattern(self):
        return None


# ---- helpers ----


def test_normalize_role_known_mapping():
    assert normalize_role("ButtonControl") == "button"
    assert normalize_role("EditControl") == "text_field"


def test_normalize_role_unknown_passes_through():
    assert normalize_role("FooBarControl") == "FooBarControl"


def test_normalize_role_missing_defaults_to_unknown():
    assert normalize_role(None) == "unknown"
    assert normalize_role("") == "unknown"


def test_extract_bounds_uses_callable_width_height():
    ctrl = _FakeCtrl(BoundingRectangle=_Rect(10, 20, 90, 60))
    b = extract_bounds(ctrl)
    assert b.x == 10 and b.y == 20 and b.width == 80 and b.height == 40


def test_extract_label_strips_whitespace():
    assert extract_label(_FakeCtrl(Name="  Save  ")) == "Save"
    assert extract_label(_FakeCtrl(Name="")) is None
    assert extract_label(_FakeCtrl(Name=None)) is None


def test_infer_actions_button_with_focus_and_invoke():
    actions = infer_actions(_FakeCtrl())
    assert "focus" in actions
    assert "invoke" in actions


# ---- build_control ----


def test_build_control_leaf():
    next_id = make_id_factory("ctrl")
    c = build_control(_FakeCtrl(), depth_remaining=0, next_id=next_id)
    assert c.id == "ctrl_0"
    assert c.role == "button"
    assert c.native_role == "ButtonControl"
    assert c.label == "OK"
    assert c.actions == ["focus", "invoke"]
    assert c.confidence == 1.0
    assert c.children == []


def test_build_control_preorder_ids_with_children():
    leaf = _FakeCtrl(Name="Child", AutomationId="child")
    root = _FakeCtrl(Name="Root", AutomationId="root", children=[leaf])
    next_id = make_id_factory("ctrl")
    c = build_control(root, depth_remaining=3, next_id=next_id)
    assert c.id == "ctrl_0"
    assert c.children[0].id == "ctrl_1"


def test_build_control_depth_zero_drops_children():
    leaf = _FakeCtrl(Name="Child")
    root = _FakeCtrl(Name="Root", children=[leaf])
    c = build_control(root, depth_remaining=0, next_id=make_id_factory())
    assert c.children == []


def test_build_control_logs_get_children_failure(capsys):
    """Phase 0 finding: silent GetChildren failures hide bugs. Should log."""

    class _Boom(_FakeCtrl):
        pass

    boom = _Boom(
        ControlTypeName="PaneControl",
        Name="bad",
        children_error=RuntimeError("UIA timeout"),
    )
    c = build_control(boom, depth_remaining=2, next_id=make_id_factory())
    # Walker continued and produced a Control for the parent itself.
    assert c.role == "pane"
    assert c.children == []
    err = capsys.readouterr().err
    assert "GetChildren() failed" in err
    assert "ctrl_0" in err
    assert "PaneControl" in err
    assert "UIA timeout" in err


def test_build_control_populates_description_for_icon_only_label():
    icon = chr(0xE700)  # GlobalNavButton
    ctrl = _FakeCtrl(Name=icon, AutomationId="btnHamburger")
    c = build_control(ctrl, depth_remaining=0, next_id=make_id_factory())
    assert c.label == icon  # raw glyph preserved
    assert c.description == "icon: GlobalNavButton"


def test_build_control_no_description_for_plain_text_label():
    c = build_control(_FakeCtrl(Name="Save"), depth_remaining=0, next_id=make_id_factory())
    assert c.description is None


def test_build_control_populates_synonyms_for_known_word_label():
    c = build_control(_FakeCtrl(Name="Zero"), depth_remaining=0, next_id=make_id_factory())
    assert c.synonyms == ["0"]


def test_build_control_no_synonyms_for_arbitrary_label():
    c = build_control(_FakeCtrl(Name="Save"), depth_remaining=0, next_id=make_id_factory())
    assert c.synonyms == []


def test_build_control_confidence_reflects_signal_availability():
    # No label, no AutomationId, generic pane role with focus action only.
    weak = _FakeCtrl(
        ControlTypeName="PaneControl",
        Name=None,
        AutomationId=None,
        IsKeyboardFocusable=True,
    )

    # Override Invoke to return None (panes don't typically invoke).
    class _NoPatternsPane(_FakeCtrl):
        def GetInvokePattern(self):
            return None

    weak = _NoPatternsPane(
        ControlTypeName="PaneControl",
        Name=None,
        AutomationId=None,
        IsKeyboardFocusable=True,
    )
    c = build_control(weak, depth_remaining=0, next_id=make_id_factory())
    # role=pane (specific, +0.25) + actions=[focus] (+0.25) = 0.5
    assert c.confidence == 0.5


# ---- system surface ----


def test_is_system_surface_taskbar():
    assert is_system_surface("Taskbar", "explorer.exe") is True


def test_is_system_surface_program_manager():
    assert is_system_surface("Program Manager", "explorer.exe") is True


def test_is_system_surface_empty_title_explorer_is_secondary_taskbar():
    assert is_system_surface("", "explorer.exe") is True


def test_is_system_surface_explorer_folder_window_is_not_system():
    # A real File Explorer window has a folder name as title.
    assert is_system_surface("Documents", "explorer.exe") is False


def test_is_system_surface_non_explorer_process_is_not_system():
    assert is_system_surface("Taskbar", "Notepad.exe") is False
    assert is_system_surface("Calculator", "ApplicationFrameHost.exe") is False


def test_is_system_surface_no_process_name_is_not_system():
    assert is_system_surface("Taskbar", None) is False


def test_is_system_surface_case_handling():
    # Process matching is case-insensitive.
    assert is_system_surface("Taskbar", "Explorer.EXE") is True


# ---- flatten_structural_panes ----


def _pane(id_, *, label=None, description=None, children=None) -> Control:
    return Control(
        id=id_,
        role="pane",
        native_role="PaneControl",
        label=label,
        description=description,
        enabled=True,
        visible=True,
        focused=False,
        bounds=None,
        actions=[],
        children=children or [],
    )


def _button(id_, label="OK") -> Control:
    return Control(
        id=id_,
        role="button",
        native_role="ButtonControl",
        label=label,
        enabled=True,
        visible=True,
        focused=False,
        bounds=None,
        actions=["focus", "invoke"],
    )


def test_flatten_collapses_single_unlabeled_pane():
    btn = _button("ctrl_2")
    pane = _pane("ctrl_1", children=[btn])
    root = _pane("ctrl_0", label="Window", children=[pane])

    result = flatten_structural_panes(root)
    assert result.id == "ctrl_0"
    assert len(result.children) == 1
    survivor = result.children[0]
    assert survivor.id == "ctrl_2"  # the button replaced the pane
    assert survivor.raw_ref == {"flattened": ["ctrl_1"]}


def test_flatten_collapses_chain_of_panes():
    btn = _button("ctrl_3")
    inner = _pane("ctrl_2", children=[btn])
    middle = _pane("ctrl_1", children=[inner])
    root = _pane("ctrl_0", label="Window", children=[middle])

    result = flatten_structural_panes(root)
    assert len(result.children) == 1
    survivor = result.children[0]
    assert survivor.id == "ctrl_3"
    # Bottom-up: innermost pane was recorded first.
    assert survivor.raw_ref == {"flattened": ["ctrl_2", "ctrl_1"]}


def test_flatten_preserves_labeled_panes():
    btn = _button("ctrl_2")
    labeled_pane = _pane("ctrl_1", label="Sidebar", children=[btn])
    root = _pane("ctrl_0", label="Window", children=[labeled_pane])

    result = flatten_structural_panes(root)
    # Labeled pane survives even though it has one child.
    assert result.children[0].id == "ctrl_1"
    assert result.children[0].label == "Sidebar"


def test_flatten_preserves_panes_with_multiple_children():
    a = _button("ctrl_2", label="A")
    b = _button("ctrl_3", label="B")
    pane = _pane("ctrl_1", children=[a, b])
    root = _pane("ctrl_0", label="Window", children=[pane])

    result = flatten_structural_panes(root)
    # Pane has 2 kids → not flattenable.
    assert result.children[0].id == "ctrl_1"
    assert len(result.children[0].children) == 2


def test_flatten_preserves_root_even_if_qualifies():
    # If the root would itself collapse, we still keep it — the caller
    # asked for THIS window and the response should reflect that.
    btn = _button("ctrl_1")
    root = _pane("ctrl_0", children=[btn])  # unlabeled pane root + 1 child

    result = flatten_structural_panes(root)
    assert result.id == "ctrl_0"
    assert len(result.children) == 1
    assert result.children[0].id == "ctrl_1"


def test_flatten_preserves_panes_with_description():
    # Icon-font hint on a pane means it carries info → don't collapse.
    btn = _button("ctrl_2")
    icon_pane = _pane("ctrl_1", description="icon: Settings", children=[btn])
    root = _pane("ctrl_0", label="Window", children=[icon_pane])

    result = flatten_structural_panes(root)
    assert result.children[0].id == "ctrl_1"


def test_flatten_does_not_collapse_non_pane_roles():
    # A "group" with one child stays — the rule targets panes only.
    btn = _button("ctrl_2")
    group = Control(
        id="ctrl_1",
        role="group",
        native_role="GroupControl",
        label=None,
        enabled=True,
        visible=True,
        focused=False,
        bounds=None,
        actions=[],
        children=[btn],
    )
    root = _pane("ctrl_0", label="Window", children=[group])

    result = flatten_structural_panes(root)
    assert result.children[0].id == "ctrl_1"
