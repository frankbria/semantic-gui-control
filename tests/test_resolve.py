"""Tests for the shared read-resolution helper.

This algorithm used to exist twice -- once in the Windows adapter and once,
independently, in `FakeAdapter`. Every CLI test ran against the copy, so the
resolution policy the suite certified was the double's. Changing the real
adapter's multi-match rule would have left all tests green.

These tests exercise the single definition both now delegate to.
"""

from __future__ import annotations

import pytest

from sgcl.core.matcher import Query
from sgcl.core.resolve import find_in_tree, require_exactly_one, resolve_one
from sgcl.core.schema import Control


def _ctrl(id_, label=None, role="button", children=None) -> Control:
    return Control(
        id=id_,
        role=role,
        native_role="ButtonControl",
        label=label,
        enabled=True,
        visible=True,
        focused=False,
        bounds=None,
        actions=["focus"],
        confidence=0.75,
        children=children or [],
    )


def _tree() -> Control:
    return _ctrl(
        "root",
        label="Win",
        role="window",
        children=[
            _ctrl("a", label="Save"),
            _ctrl("b", label="Cancel", children=[_ctrl("b1", label="Deep")]),
            _ctrl("c", label="Save"),  # duplicate label -> ambiguity
        ],
    )


# ---- find_in_tree ----


def test_find_in_tree_locates_root():
    tree = _tree()
    assert find_in_tree(tree, "root") is tree


def test_find_in_tree_locates_nested_descendant():
    assert find_in_tree(_tree(), "b1").label == "Deep"


def test_find_in_tree_returns_none_when_absent():
    assert find_in_tree(_tree(), "nope") is None


# ---- the exactly-one-of precondition ----


def test_require_exactly_one_rejects_neither():
    with pytest.raises(ValueError, match="exactly one"):
        require_exactly_one(None, None)


def test_require_exactly_one_rejects_both():
    with pytest.raises(ValueError, match="exactly one"):
        require_exactly_one(Query(label="Save"), "a")


def test_require_exactly_one_accepts_either_alone():
    require_exactly_one(Query(label="Save"), None)
    require_exactly_one(None, "a")


# ---- resolve_one ----


def test_resolve_by_target_id():
    assert resolve_one(_tree(), query=None, target_id="b1").label == "Deep"


def test_resolve_by_query():
    control = resolve_one(_tree(), query=Query(label="Cancel"), target_id=None)
    assert control.id == "b"


def test_unknown_target_id_raises_lookup_error():
    with pytest.raises(LookupError, match="no control with id"):
        resolve_one(_tree(), query=None, target_id="nope")


def test_no_match_raises_lookup_error():
    with pytest.raises(LookupError, match="no control matched"):
        resolve_one(_tree(), query=Query(label="Nonexistent"), target_id=None)


def test_ambiguous_match_raises_rather_than_guessing():
    """Two controls labelled "Save" must not silently collapse to one.

    "Ambiguity is explicit" is a project principle -- resolution refuses
    rather than picking the first hit.
    """
    with pytest.raises(LookupError, match="2 controls matched"):
        resolve_one(_tree(), query=Query(label="Save"), target_id=None)


def test_resolve_one_enforces_the_precondition_too():
    """Callers guard early to avoid expensive work, but the helper is safe alone."""
    with pytest.raises(ValueError, match="exactly one"):
        resolve_one(_tree(), query=None, target_id=None)
    with pytest.raises(ValueError, match="exactly one"):
        resolve_one(_tree(), query=Query(label="Save"), target_id="a")
