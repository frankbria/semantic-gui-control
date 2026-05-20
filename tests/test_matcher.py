"""Matcher tests against synthetic Control trees."""

from __future__ import annotations

import pytest

from sgcl.core.matcher import Query, match_query
from sgcl.core.schema import Control


def _ctrl(
    id_,
    role="button",
    label="OK",
    *,
    enabled=True,
    visible=True,
    focused=False,
    confidence=1.0,
    synonyms=None,
    description=None,
    children=None,
) -> Control:
    return Control(
        id=id_,
        role=role,
        native_role={"button": "ButtonControl", "text_field": "EditControl"}.get(role, role),
        label=label,
        enabled=enabled,
        visible=visible,
        focused=focused,
        bounds=None,
        actions=["focus", "invoke"] if role == "button" else ["focus"],
        children=children or [],
        confidence=confidence,
        description=description,
        synonyms=list(synonyms) if synonyms else [],
    )


def _calculator_like() -> Control:
    """A miniature affordance graph that exercises synonyms + role mix."""
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
    icon = _ctrl(
        "ctrl_icon",
        role="button",
        label="",
        description="icon: Settings",
        confidence=0.75,
    )
    return _ctrl(
        "ctrl_window",
        role="window",
        label="Calculator",
        children=[zero, plus, equals, pi, display, icon],
    )


# ---- exact label ----------------------------------------------------------


def test_exact_label_returns_one_match_at_full_score():
    root = _calculator_like()
    results = match_query(root, Query(label="Plus"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_plus"
    assert results[0].match_confidence == 1.0


def test_exact_label_is_case_insensitive():
    root = _calculator_like()
    results = match_query(root, Query(label="plus"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_plus"


def test_exact_label_strips_whitespace():
    root = _calculator_like()
    results = match_query(root, Query(label="  plus  "))
    assert len(results) == 1


def test_exact_label_no_match():
    root = _calculator_like()
    assert match_query(root, Query(label="Times")) == []


# ---- synonym path via text ------------------------------------------------


def test_synonym_via_text_selector_scores_0_9():
    # text="0" hits ctrl_zero via synonym "0" (0.9) AND ctrl_display
    # via label_contains on "Display is 0" (0.7). Both are valid matches;
    # synonym hit ranks higher.
    root = _calculator_like()
    results = match_query(root, Query(text="0"))
    assert len(results) == 2
    assert results[0].control.id == "ctrl_zero"
    assert results[0].match_confidence == 0.9
    assert results[1].control.id == "ctrl_display"
    assert results[1].match_confidence == 0.7


def test_synonym_for_special_char():
    root = _calculator_like()
    results = match_query(root, Query(text="π"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_pi"


def test_text_prefers_exact_label_over_synonym():
    # "Plus" is an exact label hit on ctrl_plus AND a synonym hit on nothing.
    root = _calculator_like()
    results = match_query(root, Query(text="Plus"))
    # Should score 1.0 (exact) not 0.9 (synonym).
    assert results[0].match_confidence == 1.0


# ---- description path -----------------------------------------------------


def test_description_match_scores_0_85():
    root = _calculator_like()
    results = match_query(root, Query(text="Settings"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_icon"
    assert results[0].match_confidence == 0.85


# ---- label_contains -------------------------------------------------------


def test_label_contains_scores_0_7():
    root = _calculator_like()
    results = match_query(root, Query(label_contains="display"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_display"
    assert results[0].match_confidence == 0.7


def test_label_contains_is_case_insensitive():
    root = _calculator_like()
    assert match_query(root, Query(label_contains="DISPLAY"))[0].control.id == "ctrl_display"


# ---- role / state filters -------------------------------------------------


def test_role_only_filter_scores_0_5():
    root = _calculator_like()
    results = match_query(root, Query(role="button"))
    assert len(results) == 5  # Zero, Plus, Equals, Pi, icon button
    assert all(r.match_confidence == 0.5 for r in results)
    assert all(r.control.role == "button" for r in results)


def test_role_filter_combined_with_label():
    root = _calculator_like()
    results = match_query(root, Query(role="button", label="Equals"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_eq"
    assert results[0].match_confidence == 1.0


def test_role_filter_blocks_wrong_role():
    root = _calculator_like()
    # Window's label is "Calculator" but role is "window", not "button".
    results = match_query(root, Query(role="button", label="Calculator"))
    assert results == []


def test_enabled_filter():
    disabled = _ctrl("ctrl_disabled", role="button", label="Cancel", enabled=False)
    root = _ctrl("root", role="window", label="W", children=[disabled])
    assert match_query(root, Query(enabled=False))[0].control.id == "ctrl_disabled"
    assert match_query(root, Query(enabled=True, label="Cancel")) == []


def test_focused_filter():
    a = _ctrl("a", role="button", label="A", focused=True)
    b = _ctrl("b", role="button", label="B", focused=False)
    root = _ctrl("root", role="window", label="W", children=[a, b])
    assert [m.control.id for m in match_query(root, Query(focused=True))] == ["a"]


def test_visible_filter():
    a = _ctrl("a", role="button", label="A", visible=True)
    b = _ctrl("b", role="button", label="B", visible=False)
    root = _ctrl("root", role="window", label="W", children=[a, b])
    assert [m.control.id for m in match_query(root, Query(visible=False))] == ["b"]


def test_tri_state_none_is_pass_through():
    a = _ctrl("a", role="button", label="A", enabled=True)
    b = _ctrl("b", role="button", label="B", enabled=False)
    root = _ctrl("root", role="window", label="W", children=[a, b])
    # No enabled/visible/focused specified; both buttons returned.
    results = match_query(root, Query(role="button"))
    ids = {m.control.id for m in results}
    assert ids == {"a", "b"}


# ---- combined ranking -----------------------------------------------------


def test_combined_rank_includes_adapter_confidence():
    high_conf = _ctrl("high", role="button", label="X", confidence=1.0)
    low_conf = _ctrl("low", role="button", label="X", confidence=0.5)
    root = _ctrl("root", role="window", label="W", children=[low_conf, high_conf])

    results = match_query(root, Query(label="X"))
    assert results[0].control.id == "high"  # higher combined_rank wins ordering
    assert results[0].combined_rank == 1.0  # 1.0 * 1.0
    assert results[1].combined_rank == 0.5  # 1.0 * 0.5


def test_results_sorted_descending_by_combined_rank():
    root = _calculator_like()
    results = match_query(root, Query(role="button"))
    ranks = [r.combined_rank for r in results]
    assert ranks == sorted(ranks, reverse=True)


# ---- ambiguity ------------------------------------------------------------


def test_multiple_matches_returned_not_collapsed():
    a = _ctrl("a", role="button", label="OK")
    b = _ctrl("b", role="button", label="OK")
    root = _ctrl("root", role="window", label="W", children=[a, b])
    results = match_query(root, Query(label="OK"))
    assert {r.control.id for r in results} == {"a", "b"}


def test_empty_match_returns_empty_list():
    root = _calculator_like()
    assert match_query(root, Query(label="nothing-here")) == []


# ---- ancestor context -----------------------------------------------------


def test_parents_descriptor_contains_ancestor_chain():
    leaf = _ctrl("leaf", role="button", label="Save")
    inner = _ctrl("inner", role="group", label="Toolbar", children=[leaf])
    root = _ctrl("root", role="window", label="MyApp", children=[inner])

    results = match_query(root, Query(label="Save"))
    assert len(results) == 1
    parents = results[0].parents
    assert [p["id"] for p in parents] == ["root", "inner"]
    assert parents[1]["label"] == "Toolbar"
    assert parents[1]["role"] == "group"


def test_root_match_has_empty_parents():
    only = _ctrl("only", role="button", label="X")
    results = match_query(only, Query(label="X"))
    assert results[0].parents == []


# ---- serialization --------------------------------------------------------


def test_match_result_to_dict_round_trips_through_json():
    import json

    root = _calculator_like()
    results = match_query(root, Query(label="Plus"))
    out = json.dumps(results[0].to_dict())
    loaded = json.loads(out)
    assert loaded["control"]["id"] == "ctrl_plus"
    assert loaded["match_confidence"] == 1.0
    assert loaded["combined_rank"] == 1.0


# ---- additive selector semantics (AND) ------------------------------------


def test_multiple_text_selectors_must_all_match():
    """label AND label_contains both specified: both must hit."""
    root = _calculator_like()
    # label='Plus' matches ctrl_plus; label_contains='lus' also matches ctrl_plus.
    results = match_query(root, Query(label="Plus", label_contains="lus"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_plus"
    # label='Plus' but label_contains='xyz' → no match.
    assert match_query(root, Query(label="Plus", label_contains="xyz")) == []


def test_text_selector_finds_via_label_substring_as_fallback():
    root = _calculator_like()
    # "isplay" isn't an exact label, synonym, or description hit on anything,
    # but IS a label_contains hit on "Display is 0".
    results = match_query(root, Query(text="isplay"))
    assert len(results) == 1
    assert results[0].control.id == "ctrl_display"
    assert results[0].match_confidence == 0.7


@pytest.mark.parametrize(
    "selector,expected_score",
    [
        ({"label": "Plus"}, 1.0),
        ({"text": "+"}, 0.9),  # synonym
        ({"text": "Settings"}, 0.85),  # description
        ({"label_contains": "lus"}, 0.7),
        ({"role": "button"}, 0.5),  # role-only
    ],
)
def test_scoring_constants(selector, expected_score):
    root = _calculator_like()
    results = match_query(root, Query(**selector))
    assert results, f"selector {selector} produced no matches"
    assert results[0].match_confidence == expected_score


# ---- F.2: relationship filters --------------------------------------------


def _dialog_tree() -> Control:
    """A small Save-As dialog:

    window#root
      dialog#dlg
        text_field#name_field  (label "File name:")
        button#save           (label "Save")
        button#cancel         (label "Cancel")
      status_bar#status
        button#help           (label "Help")  ← uncle of save/cancel
    """
    name_field = _ctrl("name_field", role="text_field", label="File name:")
    save = _ctrl("save", role="button", label="Save")
    cancel = _ctrl("cancel", role="button", label="Cancel")
    dlg = _ctrl(
        "dlg",
        role="dialog",
        label="Save As",
        children=[name_field, save, cancel],
    )
    help_btn = _ctrl("help", role="button", label="Help")
    status = _ctrl(
        "status",
        role="status_bar",
        label="Status",
        children=[help_btn],
    )
    return _ctrl(
        "root",
        role="window",
        label="MyApp",
        children=[dlg, status],
    )


def test_inside_filter_matches_descendants():
    root = _dialog_tree()
    results = match_query(root, Query(role="button", inside="dlg"))
    ids = {r.control.id for r in results}
    assert ids == {"save", "cancel"}  # help is not inside dlg


def test_inside_filter_does_not_match_self():
    root = _dialog_tree()
    # dlg itself is not a descendant of dlg.
    results = match_query(root, Query(label="Save As", inside="dlg"))
    assert results == []


def test_inside_filter_no_match_when_ancestor_id_missing():
    root = _dialog_tree()
    results = match_query(root, Query(role="button", inside="nonexistent"))
    assert results == []


def test_with_parent_role_filters_by_direct_parent():
    root = _dialog_tree()
    # Buttons directly inside a dialog: save, cancel. Not help (parent is status_bar).
    results = match_query(root, Query(role="button", with_parent_role="dialog"))
    ids = {r.control.id for r in results}
    assert ids == {"save", "cancel"}


def test_with_parent_role_at_root_yields_nothing():
    only = _ctrl("only", role="button", label="X")
    assert match_query(only, Query(with_parent_role="window")) == []


def test_near_matches_siblings():
    root = _dialog_tree()
    # Things near 'save': cancel (same parent), name_field (same parent).
    # 'save' itself is excluded.
    results = match_query(root, Query(near="save"))
    ids = {r.control.id for r in results}
    assert "cancel" in ids
    assert "name_field" in ids
    assert "save" not in ids


def test_near_matches_one_level_out():
    root = _dialog_tree()
    # 'help' is one level out from 'save' (save's parent is dlg, help's parent
    # is status_bar; dlg and status_bar share grandparent 'root').
    results = match_query(root, Query(near="save"))
    ids = {r.control.id for r in results}
    assert "help" in ids


def test_near_excludes_target_itself():
    root = _dialog_tree()
    results = match_query(root, Query(near="save"))
    assert all(r.control.id != "save" for r in results)


def test_near_yields_nothing_for_nonexistent_target():
    root = _dialog_tree()
    assert match_query(root, Query(near="nonexistent")) == []


def test_relationship_filter_combines_with_text_selector():
    root = _dialog_tree()
    # "Save" button inside the dialog → 1 hit at 1.0.
    results = match_query(root, Query(label="Save", inside="dlg"))
    assert len(results) == 1
    assert results[0].control.id == "save"
    assert results[0].match_confidence == 1.0

    # "Save" button outside the dialog → 0 hits even though label matches.
    results = match_query(root, Query(label="Save", inside="status"))
    assert results == []


def test_relationship_only_filter_scores_role_only_floor():
    root = _dialog_tree()
    # Just `inside=dlg` — no text selector — produces role-only-floor scores.
    results = match_query(root, Query(inside="dlg"))
    assert results, "expected descendants of dlg"
    assert all(r.match_confidence == 0.5 for r in results)


def test_with_parent_role_combined_with_role_filter():
    root = _dialog_tree()
    # role=button AND parent is a dialog → only save and cancel.
    # role=button AND parent is a status_bar → only help.
    in_dialog = match_query(root, Query(role="button", with_parent_role="dialog"))
    in_status = match_query(root, Query(role="button", with_parent_role="status_bar"))
    assert {r.control.id for r in in_dialog} == {"save", "cancel"}
    assert {r.control.id for r in in_status} == {"help"}
