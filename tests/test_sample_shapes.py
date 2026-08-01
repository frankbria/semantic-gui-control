"""Golden-shape tests over the committed Windows captures.

`spikes/samples/` holds 20 JSON captures from real Windows runs and nothing
executed them -- the Linux-side cross-check in `spikes/find-read-results.md`
was done by hand, once. Meanwhile there is no machine-readable schema
anywhere: `Control.to_dict()` is hand-written with no validator, so drift is
invisible until somebody reads a diff.

These tests are the detector ADR-0001 asks for and does not have. Its revisit
trigger is "the platform-neutral core acquires its third UIA-shaped field",
and until now nothing would notice a first, second or third.

**Shape, not content.** Nothing here asserts a label, a bound, or a count.
Those are properties of one Windows machine on one afternoon.

## Why there is a drift table

The samples are not one generation. They predate schema changes that landed
after they were captured, and they **cannot be regenerated on Linux** -- they
are real UIA output, so refreshing them needs a Windows session. Deleting or
editing them to make tests pass would invert the purpose of a fixture.

So `_KNOWN_ABSENT` records, per sample, which current fields legitimately did
not exist yet, with the reason. That table is the point:

- A field *missing* from a sample must be listed there, or the test fails.
- A field *present* but unknown to the current schema always fails.
- Adding a new field to `Control` makes every sample fail as undocumented
  drift until someone records why -- which is exactly the ADR-0001 tripwire.

Entries are removed as samples are recaptured on Windows, not added to
casually.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sgcl.core.read_result import ReadResult
from sgcl.core.schema import Control, WindowInfo

SAMPLES = sorted((Path(__file__).resolve().parent.parent / "spikes" / "samples").glob("*.json"))


def _control_keys() -> set[str]:
    return set(
        Control(
            id="x",
            role="button",
            native_role="ButtonControl",
            label=None,
            enabled=True,
            visible=True,
            focused=False,
            bounds=None,
            actions=[],
            confidence=1.0,
        ).to_dict()
    )


def _window_keys() -> set[str]:
    return set(
        WindowInfo(
            id="x",
            title="t",
            process_name=None,
            pid=1,
            bounds=None,
            visible=True,
            is_active=False,
        ).to_dict()
    )


def _read_keys() -> set[str]:
    return set(ReadResult(supported=True, source="label", value="v").to_dict())


# Sample name -> (fields absent, why). Keep the reasons specific; a vague
# entry here silently licenses real drift.
_PRE_NORMALIZE = (
    frozenset({"confidence", "description", "synonyms", "parent_id"}),
    "Phase 0 raw dump, captured before the Normalize fields existed",
)
_PRE_PARENT_ID = (
    frozenset({"parent_id"}),
    "captured before parent_id was added to the graph",
)
_PRE_SYSTEM_FILTER = (
    frozenset({"is_system_surface"}),
    "Phase 0 windows dump, captured before system-surface tagging",
)

_KNOWN_ABSENT: dict[str, tuple[frozenset[str], str]] = {
    "06-notepad-d3.json": _PRE_NORMALIZE,
    "07-calculator-d3.json": _PRE_NORMALIZE,
    "09-calculator-d8.json": _PRE_NORMALIZE,
    "08-windows-run2.json": _PRE_SYSTEM_FILTER,
    "10-windows-phase1.json": _PRE_PARENT_ID,
    "11-windows-phase1-filtered.json": _PRE_PARENT_ID,
    "12-notepad-phase1-d3.json": _PRE_PARENT_ID,
    "13-calculator-phase1-d8.json": _PRE_PARENT_ID,
    "14-calculator-phase1-fixed-d8.json": _PRE_PARENT_ID,
    "15-calculator-phase1-clean-d8.json": _PRE_PARENT_ID,
    "f7-a-find-equals-by-synonym.json": _PRE_PARENT_ID,
    "f7-a2-find-equals-by-text.json": _PRE_PARENT_ID,
    "f7-b-find-zero-by-synonym.json": _PRE_PARENT_ID,
    "f7-b2-find-zero-by-text.json": _PRE_PARENT_ID,
    "f7-c-find-all-buttons.json": _PRE_PARENT_ID,
    "f7-d-find-notepad-editor.json": _PRE_PARENT_ID,
    "f7-d2-find-notepad-document.json": _PRE_PARENT_ID,
    "f7-e-discovery-calc-static-text.json": _PRE_PARENT_ID,
    "f7-e-read-calc-display.json": _PRE_PARENT_ID,
    "f7-f-read-notepad-document.json": _PRE_PARENT_ID,
}

# The samples also predate the `status`/`adapter`/`platform` response
# envelope, so a FIND capture is a bare {"matches": [...]}.
_ENVELOPE_KEYS = frozenset({"status", "adapter", "platform"})


def _allowed_absent(sample: Path) -> frozenset[str]:
    entry = _KNOWN_ABSENT.get(sample.name)
    return entry[0] if entry else frozenset()


def _iter_controls(node: dict):
    yield node
    for child in node.get("children", []):
        yield from _iter_controls(child)


def _check(obj: dict, expected: set[str], allowed_absent: frozenset[str], where: str) -> None:
    present = set(obj)
    unexpected = present - expected
    assert not unexpected, f"{where}: keys not in the current schema: {sorted(unexpected)}"

    absent = expected - present
    undocumented = absent - allowed_absent
    assert not undocumented, (
        f"{where}: fields missing with no entry in _KNOWN_ABSENT: {sorted(undocumented)}. "
        "If the schema just gained a field, record why each sample lacks it "
        "(and see ADR-0001 on core acquiring adapter-shaped fields)."
    )


def _load(sample: Path):
    return json.loads(sample.read_text(encoding="utf-8"))


def _shape_of(data) -> str:
    if isinstance(data, list):
        return "window_list"
    if "matches" in data:
        return "find_response"
    if "supported" in data and "affordance" in data:
        return "read_response"
    return "control_tree"


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.name)
def test_sample_matches_the_current_schema_shape(sample):
    """Every capture validates against today's schema, drift table included."""
    data = _load(sample)
    shape = _shape_of(data)
    allowed = _allowed_absent(sample)

    if shape == "window_list":
        assert data, f"{sample.name}: empty window list proves nothing"
        for i, window in enumerate(data):
            _check(window, _window_keys(), allowed, f"{sample.name}[{i}]")
        return

    if shape == "find_response":
        assert set(data) - _ENVELOPE_KEYS == {"matches"}, sorted(data)
        for i, match in enumerate(data["matches"]):
            assert set(match) == {"control", "match_confidence", "combined_rank", "parents"}
            for control in _iter_controls(match["control"]):
                _check(control, _control_keys(), allowed, f"{sample.name} match[{i}]")
        return

    if shape == "read_response":
        _check(
            {k: v for k, v in data.items() if k != "affordance"},
            _read_keys(),
            frozenset(),
            f"{sample.name} result",
        )
        for control in _iter_controls(data["affordance"]):
            _check(control, _control_keys(), allowed, f"{sample.name} affordance")
        return

    for control in _iter_controls(data):
        _check(control, _control_keys(), allowed, sample.name)


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.name)
def test_confidence_stays_in_range(sample):
    """`confidence` is documented 0..1 and nothing in the code enforces it.

    Recorded as an open question in `open-questions.md`; this at least
    catches a violation that already reached a capture.
    """
    data = _load(sample)
    if isinstance(data, list) or _shape_of(data) == "read_response":
        roots = [data["affordance"]] if isinstance(data, dict) else []
    elif _shape_of(data) == "find_response":
        roots = [m["control"] for m in data["matches"]]
    else:
        roots = [data]

    for root in roots:
        for control in _iter_controls(root):
            if "confidence" in control:
                assert 0.0 <= control["confidence"] <= 1.0, f"{sample.name}: {control['id']}"


def test_every_sample_is_covered_by_a_shape():
    """No capture may be silently unvalidated."""
    assert SAMPLES, "no samples found -- the fixture path is wrong"
    for sample in SAMPLES:
        assert _shape_of(_load(sample)) in {
            "window_list",
            "find_response",
            "read_response",
            "control_tree",
        }


def test_drift_table_has_no_stale_entries():
    """An entry naming a sample that no longer exists is dead documentation."""
    names = {s.name for s in SAMPLES}
    stale = sorted(set(_KNOWN_ABSENT) - names)
    assert not stale, f"_KNOWN_ABSENT names samples that do not exist: {stale}"


def test_drift_table_does_not_excuse_fields_that_are_current():
    """The table may only list fields the schema actually has.

    Guards the failure mode where someone renames a field and the old name
    lingers in the table, silently excusing the new one's absence.
    """
    known = _control_keys() | _window_keys()
    for name, (fields, reason) in _KNOWN_ABSENT.items():
        assert fields <= known, f"{name}: excuses unknown fields {sorted(fields - known)}"
        assert reason.strip(), f"{name}: drift entry needs a reason"
