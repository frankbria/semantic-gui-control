"""The docs are a contract, so the contract gets a test.

`docs/affordance-model.md` is what a second-adapter author implements
against (CLAUDE.md calls it "the public contract"). It drifted from the
code once already -- documenting a flat `children: string[]` graph the
code never emitted, omitting `synonyms` and `native_role` entirely, and
listing 15 of 41 roles. Prose has no compiler, so these tests are it.

Both tests parse the shipped markdown rather than a copy, so a table
edited without touching the code fails just as loudly as the reverse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sgcl.adapters.windows_uia._walker import _UIA_TO_ROLE
from sgcl.core.schema import Bounds, Control

DOCS = Path(__file__).resolve().parent.parent / "docs"
AFFORDANCE_MODEL = DOCS / "affordance-model.md"


def _section(text: str, heading: str) -> str:
    """Return the body under a `## heading`, up to the next `## `."""
    start = text.index(f"\n## {heading}\n")
    rest = text[start + 1 :]
    end = rest.find("\n## ", 1)
    return rest if end == -1 else rest[:end]


def _table_rows(section: str) -> list[list[str]]:
    """Parse a pipe table into cells, skipping the header and separator."""
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Split on unescaped pipes only -- type cells write `string \| null`.
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if not cells or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(cells)
    return rows[1:]  # drop the header row


def _backticked(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


@pytest.fixture(scope="module")
def model_doc() -> str:
    return AFFORDANCE_MODEL.read_text(encoding="utf-8")


def _sample_control() -> Control:
    return Control(
        id="ctrl_0",
        role="button",
        native_role="ButtonControl",
        label="Save",
        enabled=True,
        visible=True,
        focused=False,
        bounds=Bounds(x=0, y=0, width=10, height=10),
        actions=["focus", "invoke"],
    )


def test_schema_table_matches_control_to_dict(model_doc):
    """Every emitted key is documented, and every documented key is emitted.

    Rows marked `Phase 3` are the exception: they are specified-but-not-
    shipped on purpose, so they must be documented and must NOT be emitted.
    """
    rows = _table_rows(_section(model_doc, "Schema"))

    documented = {}
    for cells in rows:
        names = _backticked(cells[0])
        assert names, f"schema table row has no field name: {cells}"
        documented[names[0]] = cells[2]  # the Status column

    emitted = set(_sample_control().to_dict())
    shipped = {f for f, status in documented.items() if status == "shipped"}
    deferred = {f for f, status in documented.items() if status != "shipped"}

    assert emitted == shipped, (
        f"schema table out of sync with Control.to_dict(): "
        f"undocumented={sorted(emitted - shipped)} "
        f"documented-but-absent={sorted(shipped - emitted)}"
    )
    # A field cannot be both deferred and already shipping.
    assert not (deferred & emitted), sorted(deferred & emitted)


def test_schema_table_lists_fields_in_emission_order(model_doc):
    """Order is part of the contract -- the table is read as a walkthrough."""
    rows = _table_rows(_section(model_doc, "Schema"))
    documented = [_backticked(c[0])[0] for c in rows if c[2] == "shipped"]
    assert documented == list(_sample_control().to_dict())


def test_role_table_covers_every_mapped_role(model_doc):
    """All 42 native types and all 41 roles appear, mapped correctly."""
    rows = _table_rows(_section(model_doc, "Role vocabulary"))

    documented: dict[str, set[str]] = {}
    for role_cell, native_cell in ((c[0], c[1]) for c in rows):
        role = _backticked(role_cell)[0]
        documented[role] = set(_backticked(native_cell))

    actual: dict[str, set[str]] = {}
    for native, role in _UIA_TO_ROLE.items():
        actual.setdefault(role, set()).add(native)

    assert documented == actual, (
        "role table out of sync with _UIA_TO_ROLE: "
        f"missing={sorted(set(actual) - set(documented))} "
        f"extra={sorted(set(documented) - set(actual))}"
    )


def test_document_vs_text_field_confusion_is_called_out(model_doc):
    """The single most expensive role confusion must stay documented.

    `spikes/find-read-results.md` and `open-questions.md` both record agents
    reaching for `text_field` and missing Notepad's editing surface. If a
    future edit trims the role section, this is the sentence that must not
    silently vanish.
    """
    section = _section(model_doc, "Role vocabulary")
    assert "`document`, not a `text_field`" in section
