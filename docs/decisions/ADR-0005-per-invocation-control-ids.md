# ADR 0005: Control Ids Are Per-Invocation, With No Session State

## Status

Accepted, retroactively. Decided during the Phase 2 spike and documented
there; `open-questions.md` still listed id stability as undecided. Revisit
when Phase 3 defines verification snapshots.

## Context

`ctrl_0`, `ctrl_1`, … are assigned by a counter as the walker descends
(`make_id_factory`). They are **not derived from anything about the
control** — a second walk of an unchanged window produces the same ids only
by coincidence of ordering, and any change to the tree shifts every id after
the change.

The question was whether to invest in stable ids, and what "stable" would
even mean:

- UIA's `AutomationId` is stable *when present*, and it is frequently absent.
  This is not a rare edge case: it is the single most common missing
  confidence signal (see [`ADR-0002`](ADR-0002-adapter-confidence-scoring.md)).
- A synthetic id derived from `(role, label, parent-chain, ordinal)` would be
  more stable, but it encodes the very things most likely to change — a
  relabelled button or a reordered toolbar breaks it, silently and with no
  way for the caller to tell.
- Holding session state — a cache mapping ids to controls across
  invocations — makes ids meaningful across calls at the cost of a whole
  class of staleness bugs, and requires a daemon, which is itself undecided.

`CLAUDE.md` lists stable cross-session control ids under "out of scope for
now", so the decision is consistent with stated project scope.

## Decision

**Ids are valid only within the invocation that produced them. No session
state, no synthetic stable ids.**

What makes this workable is that **FIND returns the full normalized
affordance**, not just an id. The agent gets the label, role, synonyms,
`parents` chain, and `raw_ref.AutomationId` — everything needed to re-query
in a later command without depending on an id surviving.

So the intended flow is *re-query by selector*, not *remember an id*. READ
takes selectors directly and re-walks the tree. A `--target <ctrl_id>` mode
exists for chaining within a single fresh walk, and is documented as fragile
in [`adapter_base.py`](../../sgcl/core/adapter_base.py) and
[`command-vocabulary.md`](../command-vocabulary.md).

## Consequences

- **Every command re-walks.** Correct, and potentially slow on large trees.
  Nothing measures this yet; no phase has been latency-sensitive.
- An agent that stores an id and reuses it later gets a wrong control or a
  `target_not_resolved` error. The docs say so; nothing enforces it. This is
  the sharpest edge of the decision.
- The failure is at least *loud* when the id no longer exists. It is
  **silent** when the id now names a different control — a re-walk after the
  tree changed can make `ctrl_7` a different affordance, and nothing detects
  that. Re-querying by selector avoids it entirely.
- No daemon is required, and no cache-invalidation logic exists to be wrong.
- `raw_ref.AutomationId` remains available for apps that expose it, so an
  agent working against a well-behaved application can be more stable than
  this default allows for.

## Alternatives considered

- **Synthetic ids from `(role, label, parent-chain, ordinal)`.** Stable
  against re-walks, fragile against exactly the UI changes worth detecting,
  and would present that fragility as stability.
- **Session cache in a daemon.** Solves it properly and requires deciding
  the daemon question first, plus owning staleness. Premature.
- **Expose `AutomationId` as the primary id.** Absent too often to be the
  contract; it stays on `raw_ref` where an agent can opt into it.

## Revisit triggers

- **Phase 3 verification snapshots.** VERIFY needs to compare before and
  after states of "the same" control, which is precisely an identity
  question. If a before/after diff cannot be expressed without stable ids,
  this decision blocks it. Flagged in
  [`handoff-phase-3-planning.md`](../handoff-phase-3-planning.md).
- **A daemon is adopted**, making session state cheap.
- **Re-walk cost becomes measurable** on a real application.
- **A second adapter (Win 9)** has a natively stable identity (DOM nodes,
  AX element refs) and the uniform per-invocation contract starts costing
  more than it buys.
