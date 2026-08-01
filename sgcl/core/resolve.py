"""Resolving a read target to exactly one affordance.

Platform-neutral, like everything in `sgcl/core/`. Given a normalized tree
and either a control id or a query, produce the single `Control` a READ
should act on -- or refuse.

The refusal policy is the interesting part, and it is deliberate: an
ambiguous query raises rather than returning the top-ranked hit. FIND is
where multiple candidates are a legitimate answer; READ acts on one thing,
so guessing which one would be exactly the "confident stupidity" the
project's principles forbid. The caller gets a `LookupError` naming how many
matched, and can re-query with a narrower selector.

This lives in core because it is not Windows-specific in any way. It used to
be implemented twice -- once in the UIA adapter, once in the test double --
which meant the CLI suite certified the double's behaviour, not the
adapter's. See ADR-0001 on why adapters may not own contract logic.
"""

from __future__ import annotations

from sgcl.core.matcher import Query, match_query
from sgcl.core.schema import Control


def find_in_tree(root: Control, target_id: str) -> Control | None:
    """Depth-first search for a control id. Returns None if absent."""
    if root.id == target_id:
        return root
    for child in root.children:
        found = find_in_tree(child, target_id)
        if found is not None:
            return found
    return None


def require_exactly_one(query: Query | None, target_id: str | None) -> None:
    """Enforce that a read names its target exactly one way.

    Adapters call this *before* doing expensive work (resolving a window,
    walking a UIA tree) so a malformed request fails fast and reports the
    argument error rather than a window-not-found that happened to surface
    first. `resolve_one` calls it again; it is cheap and idempotent.
    """
    if (query is None) == (target_id is None):
        raise ValueError("read() requires exactly one of query / target_id")


def resolve_one(
    tree: Control,
    *,
    query: Query | None = None,
    target_id: str | None = None,
) -> Control:
    """Return the one control a READ should act on.

    Raises `ValueError` if the request names neither or both, and
    `LookupError` if the target cannot be resolved to exactly one
    affordance -- unknown id, no match, or several matches.
    """
    require_exactly_one(query, target_id)

    if target_id is not None:
        control = find_in_tree(tree, target_id)
        if control is None:
            raise LookupError(f"no control with id {target_id!r}")
        return control

    assert query is not None  # guaranteed by require_exactly_one
    matches = match_query(tree, query)
    if not matches:
        raise LookupError("no control matched the query")
    if len(matches) > 1:
        raise LookupError(f"{len(matches)} controls matched the query")
    return matches[0].control
