from __future__ import annotations

import pytest

from sgcl.core.confidence import score_control


def test_full_signal_scores_one():
    s = score_control(
        label="Save",
        role="button",
        actions=["focus", "invoke"],
        stable_id="btnSave",
    )
    assert s == 1.0


def test_no_signal_scores_zero():
    s = score_control(label=None, role="unknown", actions=[], stable_id=None)
    assert s == 0.0


def test_empty_label_does_not_score():
    s = score_control(label="   ", role="button", actions=["focus"], stable_id=None)
    # role + actions = 0.5; whitespace label does not count.
    assert s == 0.5


def test_custom_role_does_not_score_for_role_signal():
    s = score_control(label="X", role="custom", actions=["focus"], stable_id="id")
    # label + actions + stable_id = 0.75; "custom" role does not score.
    assert s == 0.75


def test_unknown_role_does_not_score_for_role_signal():
    s = score_control(label="X", role="UNKNOWN", actions=[], stable_id=None)
    assert s == 0.25  # only label


def test_native_passthrough_role_still_scores():
    # If the adapter falls through to the native role string (e.g.,
    # "FooControl" for an unmapped UIA type), that still counts as "we
    # know what kind of thing it is" — it just hasn't been normalized.
    s = score_control(label=None, role="FooControl", actions=[], stable_id=None)
    assert s == 0.25


def test_each_signal_contributes_quarter():
    base = score_control(label=None, role="unknown", actions=[], stable_id=None)
    assert base == 0.0
    assert score_control(label="X", role="unknown", actions=[], stable_id=None) == 0.25
    assert score_control(label=None, role="button", actions=[], stable_id=None) == 0.25
    assert score_control(label=None, role="unknown", actions=["focus"], stable_id=None) == 0.25
    assert score_control(label=None, role="unknown", actions=[], stable_id="id") == 0.25


@pytest.mark.parametrize(
    "label,role,actions,stable_id,expected",
    [
        # Realistic: a Notepad "Bold (Ctrl+B)" button with full instrumentation.
        ("Bold (Ctrl+B)", "button", ["focus", "invoke"], "ToggleButtonBold", 1.0),
        # Realistic: a structural unlabeled pane in a WinUI tree.
        (None, "pane", ["focus"], None, 0.5),
        # Realistic: status-bar text like "Line 520, Column 21".
        ("Line 520, Column 21", "static_text", ["read"], "ContentTextBlock", 1.0),
        # Edge: unlabeled custom control.
        (None, "custom", [], None, 0.0),
    ],
)
def test_realistic_scores(label, role, actions, stable_id, expected):
    assert score_control(
        label=label,
        role=role,
        actions=actions,
        stable_id=stable_id,
    ) == pytest.approx(expected)
