"""Duck-typed walker for the Windows UIA adapter.

This module deliberately does **not** import `uiautomation`, so it can be
imported and exercised on Linux. It takes whatever object the adapter
passes in and uses `getattr` / method calls. On Windows the adapter
passes a real UIA control; on Linux tests pass mocks.
"""

from __future__ import annotations

import sys
from typing import Any

from sgcl.core.confidence import score_control
from sgcl.core.icon_glyphs import describe_label
from sgcl.core.schema import Bounds, Control

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


def normalize_role(native: str | None) -> str:
    if not native:
        return "unknown"
    return _UIA_TO_ROLE.get(native, native)


def extract_bounds(ctrl) -> Bounds | None:
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


def infer_actions(ctrl) -> list[str]:
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


def extract_raw_ref(ctrl) -> dict[str, Any]:
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


def extract_label(ctrl) -> str | None:
    try:
        name = getattr(ctrl, "Name", None)
        if name is None:
            return None
        name = str(name).strip()
        return name if name else None
    except Exception:
        return None


def make_id_factory(prefix: str = "ctrl"):
    counter = {"n": 0}

    def next_id() -> str:
        i = counter["n"]
        counter["n"] += 1
        return f"{prefix}_{i}"

    return next_id


def _log_children_failure(my_id: str, native: str, exc: Exception) -> None:
    print(
        f"[sgcl] WARN: GetChildren() failed on {my_id} ({native}): {exc!r}",
        file=sys.stderr,
    )


def build_control(ctrl, depth_remaining: int, next_id) -> Control:
    """Depth-first preorder build. Parent gets an id before its children.

    `GetChildren()` failures are logged to stderr (with the offending
    control's id and native role) rather than swallowed — Phase 0 needed
    two runs to confirm Warp's empty tree wasn't a walker bug.
    """
    my_id = next_id()
    native = getattr(ctrl, "ControlTypeName", None) or "Unknown"

    children: list[Control] = []
    if depth_remaining > 0:
        try:
            child_list = ctrl.GetChildren()
        except Exception as exc:
            _log_children_failure(my_id, native, exc)
            child_list = []
        for child in child_list:
            children.append(build_control(child, depth_remaining - 1, next_id))

    role = normalize_role(native)
    label = extract_label(ctrl)
    actions = infer_actions(ctrl)
    raw_ref = extract_raw_ref(ctrl)
    automation_id = raw_ref.get("AutomationId") if raw_ref else None
    description = describe_label(label)

    return Control(
        id=my_id,
        role=role,
        native_role=native,
        label=label,
        description=description,
        enabled=bool(getattr(ctrl, "IsEnabled", True)),
        visible=not bool(getattr(ctrl, "IsOffscreen", False)),
        focused=bool(getattr(ctrl, "HasKeyboardFocus", False)),
        bounds=extract_bounds(ctrl),
        actions=actions,
        children=children,
        raw_ref=raw_ref,
        confidence=score_control(
            label=label,
            role=role,
            actions=actions,
            stable_id=automation_id,
        ),
    )
