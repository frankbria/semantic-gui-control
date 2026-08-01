# ADR 0002: Adapter Confidence Scoring

## Status

Accepted, retroactively. The rule shipped in Phase 1 (slice E.2) without an
ADR; this records the decision that was already made and corrects the two
documents that described a different one. Revisit when Phase 3 ranking
feedback arrives (see triggers below).

## Context

Every affordance carries `confidence` — the adapter's answer to "how much
signal did I actually have about this control?" It is not a match score.
FIND multiplies it: `combined_rank = match_confidence * control.confidence`
(`sgcl/core/matcher.py`), so it is load-bearing for result ordering, not
merely advisory.

The question is what produces that number, and it needed answering in a way
that a second adapter — macOS AX, AT-SPI, browser DOM — could implement
without inheriting UIA's shape.

Two documents specified a **three-signal** rule:

- `docs/phase-1-normalize-spike.md` — "clean label + role + at least one
  action = 1.0".
- `docs/open-questions.md` — "clean role + non-empty label + supported
  patterns = 1.0", still filed as open despite the code having shipped an
  answer.

The code implements **four** signals. The fourth is a stable identifier
(UIA `AutomationId`, or a platform's equivalent).

That gap is not cosmetic. `spikes/normalize-results.md` records the observed
result: "0.75 = three of four signals present. Most commonly: no
`AutomationId`." A control with a clean label, a mapped role, and an inferred
action scores **0.75** where both documents predict **1.0** — and Win32 and
other legacy apps routinely omit `AutomationId`. Those are precisely the
"legacy/native desktop app" targets named in `docs/level-1-spec.md`.

So the written spec mispredicted ranking for an entire class of application,
and `docs/phase-2-find-read-spike.md` already flags ranking calibration as
needing tuning. Tuning against a wrong written spec compounds the error.

## Decision

**Four binary signals, 0.25 each, summed.** Coarse and additive on purpose:
the rule stays auditable by a human reading one control's JSON, and
platform-neutral enough that each adapter supplies its own analogue of each
signal.

1. **Label populated** — a non-empty accessible name. Without one an agent
   cannot refer to the control semantically.
2. **Role is specific** — something more useful than `unknown` or `custom`.
   A mapped role means the adapter could classify the control.
3. **At least one action inferred** — an empty `actions` list usually means a
   structural-only node.
4. **Stable identifier present** — UIA `AutomationId`, a DOM `id`, or the
   closest equivalent. Without one the control may not survive a tree
   refresh.

The fourth signal is kept, and the two documents are corrected to match it.
It is a genuine quality signal: an affordance you cannot re-find after a
refresh is worth less than one you can, and that is exactly what
`confidence` is supposed to express. Dropping it to satisfy the older prose
would have made the number less honest.

**`Control.confidence` is a required constructor argument.** It previously
defaulted to `1.0` — a placeholder from before `score_control` existed. Once
scoring shipped, that default became a trap: any synthesized node, or a
future adapter that forgot to score, silently claimed *maximum* confidence
and outranked every honestly-scored control. Requiring it surfaces every
unscored construction site, which is the point. Defaulting to `0.0` was the
alternative and was rejected — it would have been quietly wrong instead of
loudly wrong.

## Consequences

- **Legacy Windows apps score 0.75, not 1.0**, whenever they omit
  `AutomationId`. This is correct behaviour, not a bug to be tuned away.
  Anything calibrating rank should expect it.
- `1.0` means all four signals were present. It is genuinely uncommon in
  real trees, and it should be.
- A second adapter must map each signal to its own platform or omit it
  honestly. It must not invent a substitute to inflate the score.
- The range `0..1` is documented but **not enforced** at the schema
  boundary. Nothing clamps or validates it. That is a known gap; the
  required-argument change removes the worst instance of it (the silent
  `1.0`) without adding validation.
- Because scoring is uniform across adapters, cross-adapter comparison of
  `confidence` is meaningful in principle. It is untested in practice —
  there is only one adapter.

## Alternatives considered

- **Keep three signals, drop `stable_id`.** Would have made the docs correct
  by making the code worse. Re-findability is real signal.
- **Weight the signals unevenly.** No evidence yet supports any particular
  weighting, and a tuned-looking constant invites false confidence in its
  precision. Equal weights are honest about how coarse this is.
- **Continuous rather than binary signals** (e.g. label quality as a
  gradient). Not auditable by inspection, and there is no data to fit it to.

## Revisit triggers

- Phase 2/3 ranking feedback shows `combined_rank` ordering results in a way
  a user would call wrong, and the cause traces to `confidence` rather than
  `match_confidence`. This is the trigger anticipated by
  `docs/phase-1-normalize-spike.md`.
- A second adapter cannot supply a meaningful analogue for one of the four
  signals, making cross-adapter scores incomparable.
- The icon-glyph gap becomes material: `score_control` counts a private-use
  glyph as a populated label, so an icon-only control scores as though it
  were well-labeled (see `docs/affordance-model.md`). If that starts
  distorting ranking, signal 1 needs refining rather than reweighting.
- Real evidence arrives that equal weights are wrong — at which point this
  ADR is superseded rather than amended, because the weights are the
  decision.
