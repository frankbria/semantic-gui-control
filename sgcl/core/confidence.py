"""Adapter-confidence scoring.

`Control.confidence` is the adapter's confidence (0..1) that the affordance
was correctly identified, labeled, and classified. This is **not** a
match-confidence (that belongs to FIND in Phase 2); it is the adapter's
honest answer to "how much signal did I have about this control?"

The scoring is intentionally coarse and additive — four binary signals at
0.25 each — so the rule is auditable and platform-neutral. Each
adapter (`windows_uia`, future `macos_ax`, `browser_dom`, etc.) extracts
its own version of each signal and calls `score_control()` with the same
shape of inputs.

If a signal is hard to define for a given adapter (e.g., browser DOM has
no UIA `AutomationId`), pass the closest analogue (e.g., a stable DOM
selector) or omit it. The score reflects what was available.
"""

from __future__ import annotations

from collections.abc import Sequence


def score_control(
    *,
    label: str | None,
    role: str,
    actions: Sequence[str],
    stable_id: str | None,
) -> float:
    """Return adapter confidence (0..1) for a control.

    Signals, each contributing 0.25:

    1. **Label populated** — the control has a non-empty accessible name.
       Without this an agent cannot reference the control semantically.
    2. **Role is specific** — the role is something more useful than
       `"unknown"` or `"custom"`. A mapped, named role means the adapter
       could classify the control type.
    3. **At least one action inferred** — the control has at least one
       supported action (focus, invoke, read, etc.). An empty actions
       list usually means a structural-only node.
    4. **Stable identifier present** — the adapter could surface a stable
       per-control id (e.g., UIA `AutomationId`, browser DOM id). Without
       this the control may not survive a tree refresh.
    """
    score = 0.0
    if label and label.strip():
        score += 0.25
    if role and role.lower() not in {"unknown", "custom"}:
        score += 0.25
    if actions:
        score += 0.25
    if stable_id and stable_id.strip():
        score += 0.25
    return score
