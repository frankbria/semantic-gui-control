from __future__ import annotations

import pytest

from sgcl.adapters.windows_uia._walker import normalize_role
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


def test_unmapped_type_scores_as_unclassified():
    """An unmapped UIA type reaches the scorer as "unknown", so no bonus.

    This previously asserted the opposite: a passed-through native string
    like "FooControl" earned the +0.25 "role is specific" bonus. That is
    backwards -- the signal means "the adapter could classify this control",
    and an unmapped type is exactly the case where it could not. The walker
    now normalizes those to "unknown" before scoring, so the scorer needs no
    special case; this test pins that the two agree.
    """
    assert normalize_role("FooControl") == "unknown"
    s = score_control(label=None, role=normalize_role("FooControl"), actions=[], stable_id=None)
    assert s == 0.0


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
