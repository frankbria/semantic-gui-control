"""Semantic matcher over a normalized affordance graph.

`match_query(root, query)` walks a `Control` tree and returns ranked
matches. The matcher is platform-neutral — it operates on the
normalized schema defined in `sgcl/core/schema.py` and never touches
adapter-specific objects.

## Selectors

A `Query` aggregates several optional fields. All specified selectors
must match (AND semantics):

- **Role / state filters** (filter without scoring):
  - `role` — exact normalized-role match.
  - `enabled`, `visible`, `focused` — tri-state. `True` requires the
    flag set, `False` requires it unset, `None` (default) ignores.
- **Text selectors** (filter AND produce match-confidence):
  - `label` — case-insensitive exact match.
  - `label_contains` — case-insensitive substring.
  - `text` — broad search: tries exact label, any synonym, the
    description, then label substring, in that order. Takes the
    best-scoring hit.
- **Relationship selectors** (added in F.2; placeholder fields below):
  - `inside`, `near`, `with_parent_role`.

## Match-confidence scoring

`match_confidence` is the adapter-independent strength of the *match*,
distinct from the affordance's own `confidence` (which is about how
well the adapter identified the control in the first place).

| Hit kind            | match_confidence |
|---------------------|------------------|
| Exact label         | 1.00             |
| Synonym             | 0.90             |
| Description         | 0.85             |
| Label substring     | 0.70             |
| Role/state-only     | 0.50             |

`combined_rank = match_confidence * control.confidence` is what
sorts the result list.

## Ambiguity is explicit

The matcher never silently picks one of N hits. It always returns
the full ranked list; collapsing to one is a caller's decision.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sgcl.core.schema import Control

# Scoring constants. Documented in the module docstring above.
_SCORE_EXACT = 1.0
_SCORE_SYNONYM = 0.9
_SCORE_DESCRIPTION = 0.85
_SCORE_CONTAINS = 0.7
_SCORE_ROLE_ONLY = 0.5


@dataclass(frozen=True)
class Query:
    """A semantic query over an affordance graph.

    All fields are optional. Unset fields don't filter.
    """

    # Filtering only — no contribution to match_confidence.
    role: str | None = None
    enabled: bool | None = None
    visible: bool | None = None
    focused: bool | None = None

    # Text-shaped selectors. Contribute to match_confidence.
    label: str | None = None
    label_contains: str | None = None
    text: str | None = None

    # Relationship selectors. Implemented in F.2; declared here so the
    # Query shape is stable across slices.
    inside: str | None = None
    near: str | None = None
    with_parent_role: str | None = None

    def has_text_selector(self) -> bool:
        return bool(self.label or self.label_contains or self.text)


@dataclass
class MatchResult:
    """One hit returned by the matcher."""

    control: Control
    match_confidence: float
    parents: list[dict[str, str | None]] = field(default_factory=list)

    @property
    def combined_rank(self) -> float:
        """Adapter confidence × match confidence, used for sort order."""
        return self.match_confidence * self.control.confidence

    def to_dict(self) -> dict:
        return {
            "control": self.control.to_dict(),
            "match_confidence": round(self.match_confidence, 4),
            "combined_rank": round(self.combined_rank, 4),
            "parents": list(self.parents),
        }


def match_query(root: Control, query: Query) -> list[MatchResult]:
    """Walk the tree under `root` and return ranked matches.

    Results are sorted by `combined_rank` descending. Ties are broken
    by document order (earlier first) — stable Python sort handles it.
    """
    parent_map = _build_parent_map(root)
    matches: list[MatchResult] = []
    _walk(root, query, ancestors=[], parent_map=parent_map, out=matches)
    matches.sort(key=lambda m: -m.combined_rank)
    return matches


def _walk(
    control: Control,
    query: Query,
    ancestors: list[Control],
    parent_map: dict[str, Control | None],
    out: list[MatchResult],
) -> None:
    score = _score_control(control, query, ancestors, parent_map)
    if score is not None:
        out.append(
            MatchResult(
                control=control,
                match_confidence=score,
                parents=[_parent_descriptor(a) for a in ancestors],
            )
        )
    next_ancestors = ancestors + [control]
    for child in control.children:
        _walk(child, query, next_ancestors, parent_map, out)


def _build_parent_map(root: Control) -> dict[str, Control | None]:
    """Map each control's id to its parent (None for the root)."""
    pmap: dict[str, Control | None] = {root.id: None}
    stack: list[Control] = [root]
    while stack:
        cur = stack.pop()
        for child in cur.children:
            pmap[child.id] = cur
            stack.append(child)
    return pmap


def _parent_descriptor(c: Control) -> dict[str, str | None]:
    """Lightweight ancestor shape for the result's `parents` list."""
    return {"id": c.id, "role": c.role, "label": c.label}


def _score_control(
    control: Control,
    query: Query,
    ancestors: list[Control],
    parent_map: dict[str, Control | None],
) -> float | None:
    """Return the control's match_confidence, or None if it doesn't match.

    Filtering selectors (role, state, relationship) prune before the
    text-shaped selectors decide a score.
    """
    if query.role is not None and control.role != query.role:
        return None
    if query.enabled is not None and bool(control.enabled) != query.enabled:
        return None
    if query.visible is not None and bool(control.visible) != query.visible:
        return None
    if query.focused is not None and bool(control.focused) != query.focused:
        return None

    # Relationship filters (added in F.2). These prune; they do not
    # contribute to match_confidence.
    if query.inside is not None and not _is_descendant_of(control, query.inside, ancestors):
        return None
    if query.with_parent_role is not None and not _has_parent_role(
        ancestors, query.with_parent_role
    ):
        return None
    if query.near is not None and not _is_near(control, query.near, parent_map):
        return None

    if query.has_text_selector():
        score = _score_text_selectors(control, query)
        if score is None:
            return None
        return score

    # No text selector — role/state/relationship-only filter.
    return _SCORE_ROLE_ONLY


def _is_descendant_of(control: Control, ancestor_id: str, ancestors: list[Control]) -> bool:
    """True if `control` has an ancestor with the given id. Excludes self."""
    return any(a.id == ancestor_id for a in ancestors)


def _has_parent_role(ancestors: list[Control], parent_role: str) -> bool:
    """True if the control's direct parent has the given role."""
    if not ancestors:
        return False
    return ancestors[-1].role == parent_role


def _is_near(
    control: Control,
    target_id: str,
    parent_map: dict[str, Control | None],
) -> bool:
    """True if `control` is a sibling or near-sibling of the target.

    Near = same parent OR parent's parent is the target's grandparent
    AND the candidate's parent != target's parent (i.e., uncle-cousin
    relationship, one level out). The target control itself is excluded.
    """
    if control.id == target_id:
        return False
    if target_id not in parent_map:
        return False

    candidate_parent = parent_map.get(control.id)
    target_parent = parent_map[target_id]

    if candidate_parent is None or target_parent is None:
        return False
    if candidate_parent.id == target_parent.id:
        return True  # same parent → sibling

    candidate_grandparent = parent_map.get(candidate_parent.id)
    target_grandparent = parent_map.get(target_parent.id)
    if candidate_grandparent is None or target_grandparent is None:
        return False
    return candidate_grandparent.id == target_grandparent.id


def _score_text_selectors(control: Control, query: Query) -> float | None:
    """Try the text selectors in their declared priority order.

    Returns the highest-priority score that fires, or None if no text
    selector matched.
    """
    best: float | None = None

    if query.label is not None:
        if _label_exact(control.label, query.label):
            best = _max(best, _SCORE_EXACT)
        else:
            return None  # label was specified and didn't match exactly

    if query.label_contains is not None:
        if _label_contains(control.label, query.label_contains):
            best = _max(best, _SCORE_CONTAINS)
        else:
            return None  # label_contains was specified and didn't substring-match

    if query.text is not None:
        text_score = _score_text(control, query.text)
        if text_score is None:
            return None  # text was specified and matched nothing
        best = _max(best, text_score)

    return best


def _score_text(control: Control, needle: str) -> float | None:
    """`text` is the broadest selector. Try every surface in priority order."""
    if _label_exact(control.label, needle):
        return _SCORE_EXACT
    if _any_synonym_exact(control.synonyms, needle):
        return _SCORE_SYNONYM
    if _description_match(control.description, needle):
        return _SCORE_DESCRIPTION
    if _label_contains(control.label, needle):
        return _SCORE_CONTAINS
    return None


# --- Text-comparison primitives ---------------------------------------------


def _label_exact(label: str | None, needle: str) -> bool:
    if not label or not needle:
        return False
    return label.strip().lower() == needle.strip().lower()


def _label_contains(label: str | None, needle: str) -> bool:
    if not label or not needle:
        return False
    return needle.strip().lower() in label.strip().lower()


def _any_synonym_exact(synonyms: Iterable[str], needle: str) -> bool:
    if not needle:
        return False
    n = needle.strip().lower()
    return any(s.strip().lower() == n for s in synonyms if s)


def _description_match(description: str | None, needle: str) -> bool:
    if not description or not needle:
        return False
    # Description strings from our icon map look like "icon: Settings".
    # Substring (case-insensitive) is the right granularity.
    return needle.strip().lower() in description.strip().lower()


def _max(a: float | None, b: float) -> float:
    return b if a is None else max(a, b)
