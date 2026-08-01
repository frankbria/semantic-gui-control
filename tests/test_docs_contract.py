"""The docs are a contract, so the contract gets a test.

Two documents are load-bearing. `docs/affordance-model.md` is what a
second-adapter author implements against (CLAUDE.md calls it "the public
contract"); `docs/command-vocabulary.md` is what an agent is handed as its
tool specification. Both had drifted from the code:

- affordance-model documented a flat `children: string[]` graph the code
  never emitted, omitted `synonyms` and `native_role`, listed 15 of 41 roles.
- command-vocabulary advertised a `state` FIND selector that never existed,
  and READ keys (`state`, `selection`, `visible_text`) that are really
  nested inside `details`.

Prose has no compiler, so these tests are it. Every one parses the shipped
markdown rather than a copy, so a table edited without touching the code
fails just as loudly as the reverse.

The assertions on specific sentences (the `--label` vs `--text` trap, the
`document` vs `text_field` confusion) look brittle on purpose. Both are
recorded in `spikes/` as having cost real debugging time; a future tidy-up
that trims them should have to say so out loud.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sgcl.adapters.windows_uia._walker import _UIA_TO_ROLE
from sgcl.core.matcher import Query
from sgcl.core.schema import Bounds, Control

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
AFFORDANCE_MODEL = DOCS / "affordance-model.md"
COMMAND_VOCABULARY = DOCS / "command-vocabulary.md"
READERS = ROOT / "sgcl" / "adapters" / "windows_uia" / "_readers.py"


def _section(text: str, heading: str) -> str:
    """Return the body under a heading, up to the next same-or-higher one.

    Finds the heading at whatever level it is written (`##` or `###`) so a
    later doc reshuffle that promotes or demotes a section doesn't silently
    turn these assertions into no-ops.
    """
    m = re.search(rf"^(#{{2,4}}) {re.escape(heading)}$", text, re.M)
    assert m, f"heading not found in doc: {heading}"
    level = len(m.group(1))
    body = text[m.end() :]  # everything after the heading line
    nxt = re.search(rf"^#{{1,{level}}} ", body, re.M)
    return body if not nxt else body[: nxt.start()]


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
        confidence=0.75,
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


@pytest.fixture(scope="module")
def vocab_doc() -> str:
    return COMMAND_VOCABULARY.read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", [AFFORDANCE_MODEL, COMMAND_VOCABULARY], ids=lambda p: p.name)
def test_json_examples_parse(doc):
    """Examples an agent may copy must be valid JSON.

    One block shipped with a literal `[ ... ]` placeholder that no parser
    accepts. Abridge with a string (`["...abridged..."]`) instead.
    """
    for i, block in enumerate(re.findall(r"```json\n(.*?)```", doc.read_text("utf-8"), re.S)):
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{doc.name} json block {i} does not parse: {exc}\n{block}")


def test_find_selector_table_matches_query_fields(vocab_doc):
    """Documented selectors must all exist, and all must be documented.

    The doc previously advertised a `state` selector the matcher never had.
    """
    rows = _table_rows(_section(vocab_doc, "FIND"))
    # The FIND section holds two tables; selectors are the one whose second
    # column carries CLI flags.
    documented = {_backticked(c[0])[0] for c in rows if len(c) > 1 and c[1].startswith("`--")}
    actual = set(Query.__dataclass_fields__)

    assert documented == actual, (
        f"FIND selector table out of sync with Query: "
        f"undocumented={sorted(actual - documented)} "
        f"documented-but-nonexistent={sorted(documented - actual)}"
    )


def test_read_source_table_matches_adapter(vocab_doc):
    """Every `source` the UIA reader can emit is documented, and vice versa."""
    rows = _table_rows(_section(vocab_doc, "READ"))
    documented = {_backticked(c[0])[0] for c in rows if c and c[0].startswith("`") and len(c) > 1}
    emitted = set(re.findall(r'source="([a-z_]+)"', READERS.read_text(encoding="utf-8")))

    assert documented == emitted, (
        f"READ source table out of sync with _readers.py: "
        f"undocumented={sorted(emitted - documented)} "
        f"documented-but-never-emitted={sorted(documented - emitted)}"
    )


def test_label_vs_text_ergonomic_trap_stays_documented(vocab_doc):
    """The repo's most-repeated surprise must not be edited away.

    `--label "="` returns zero matches against Calculator because the button
    is labeled "Equals"; `--text` reaches synonyms. Spike logs record this
    costing time more than once.
    """
    section = _section(vocab_doc, "FIND")
    assert "`--label` is exact" in section
    assert "synonym" in section.lower()


def test_document_vs_text_field_confusion_is_called_out(model_doc):
    """The single most expensive role confusion must stay documented.

    `spikes/find-read-results.md` and `open-questions.md` both record agents
    reaching for `text_field` and missing Notepad's editing surface. If a
    future edit trims the role section, this is the sentence that must not
    silently vanish.
    """
    section = _section(model_doc, "Role vocabulary")
    assert "`document`, not a `text_field`" in section


# ---- superseded docs ----


def _readme_legacy_docs() -> set[str]:
    """Filenames listed under README's "Legacy reference docs" heading."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "Legacy reference docs"
    start = readme.index(marker)
    # The list ends at the next blank-line-separated non-list block.
    body = readme[start:].split("\n##", 1)[0]
    return set(re.findall(r"\(docs/([a-z0-9-]+\.md)\)", body))


def _bannered_docs() -> set[str]:
    """Docs whose first line marks them superseded."""
    found = set()
    for path in (DOCS).glob("*.md"):
        first = path.read_text(encoding="utf-8").lstrip().splitlines()[0]
        if "Superseded" in first:
            found.add(path.name)
    return found


def test_readme_legacy_list_matches_the_bannered_files():
    """The two must not disagree about what is superseded.

    A file listed as legacy in README but carrying no banner is invisible to
    anyone who opens it directly -- which is how docs are normally reached,
    via search or a link or an agent reading `docs/`. The reverse, a
    bannered file README still presents as current, is worse.
    """
    listed, bannered = _readme_legacy_docs(), _bannered_docs()
    assert listed == bannered, (
        f"README lists as legacy but has no banner: {sorted(listed - bannered)}; "
        f"carries a banner but README does not list it: {sorted(bannered - listed)}"
    )


def test_superseded_banners_point_somewhere_current():
    """A banner that only says "superseded" leaves the reader stranded."""
    for name in _bannered_docs():
        head = "\n".join((DOCS / name).read_text(encoding="utf-8").splitlines()[:12])
        assert "roadmap-blunt-wins.md" in head, f"{name}: banner names no current successor"
        assert "Do not plan work from this file" in head, f"{name}: banner lacks the instruction"
