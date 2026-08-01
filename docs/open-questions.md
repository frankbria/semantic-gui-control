# Open Questions

Things we have not decided. Some block future phases; some are fine to defer. Each spike should add to this list, and resolved questions should move to `docs/decisions/` as ADRs.

## Targeting

- ~~**System/shell windows.**~~ **Settled in Phase 1.** Tagged by the
  adapter, filtered by the CLI, on by default, `--include-system` to opt in.
  See [`ADR-0004`](decisions/ADR-0004-system-surface-filtering-default.md),
  which records a real revisit trigger: filtering is clearly right for
  observation and not obviously right once Phase 3 lets an agent act.

- **Focus-based targeting is unreliable from a CLI.** `--active` picks up the
  terminal running `sgcl`, not the application. A documented constraint
  rather than an open question (`spikes/windows-observer-results.md` Run 1);
  prefer `--process` or `--title`. Listed separately because it was
  previously written as the resolution to the filtering question above,
  which it never answered.

## FIND ergonomics (from Phase 2 spike)

- **Should `--label` check synonyms?** *(Documented in
  [`agent-guide.md`](agent-guide.md); the code decision is still open.)*
  Phase 2 confirmed that
  `--label "="` returns 0 matches against Calculator's Equals button,
  because synonyms only match via `--text`. An agent prompted to "find
  the = button" would naturally use `--label` and miss the hit.
  Options: (a) `--label` also checks synonyms at 0.9 confidence,
  (b) introduce `--name` that checks both, (c) document `--text` as the
  primary agent-facing selector. See `spikes/find-read-results.md`.

- **Selector by `AutomationId`.** Calculator's display label is
  dynamic ("Display is 0" → "Display is 42"), so agents can't rely on
  it. The stable hook is `raw_ref.AutomationId: "CalculatorResults"`.
  A `--automation-id` selector would let agents target stable surfaces
  in apps with otherwise volatile labels.

- **`--max-length` cap for ValuePattern.** Currently caps only
  TextPattern. Notepad's document came through ValuePattern at 21k
  characters with no truncation. Should `--max-length` also bound
  ValuePattern output? Trade-off: protect agent context windows vs.
  honest fidelity to what the app actually exposes.

- **Role naming for editable areas.** Notepad's editor is `document`,
  not `text_field`. UIA's naming, faithfully passed through. Phase 3
  should produce a small role-mapping guide for agents so they know to
  query both names.

- **TogglePattern and SelectionPattern paths are untested.** Phase 2
  spike didn't exercise either. Phase 3 should test against an app with
  checkboxes, radio buttons, combo boxes, or tab controls.

- **Linux tests cannot detect `uiautomation` API drift.** The suite runs
  against hand-written doubles, and those doubles are uniformly *more*
  capable than the real library — they define every `Get*Pattern` and
  every attribute the walker reads, unconditionally. So the Linux suite
  certifies the mocks' contract, not `uiautomation`'s.

  Because access is duck-typed, an upstream rename would not even fail to
  import. It would surface as a silently empty or degraded tree during a
  manual Windows session — the slowest feedback loop we have.

  Two partial mitigations are in place, neither of which closes it:
  `uiautomation` is capped `<3` (a major version is the likeliest source
  of such a break), and `tests/test_uia_conformance.py` asserts that a
  real control provides everything the mocks fake. That conformance suite
  **only runs on Windows**, so on CI it is always skipped. A skip is not a
  pass.

  The open question is whether that is good enough, or whether this
  warrants a Windows CI runner. Defining a `Protocol` for the control
  surface the adapter actually uses would also make the contract explicit
  in one place and give a type checker something to verify.

- **Risk classification for READ.** `docs/risk-model.md` doesn't
  explicitly classify READ. It's read-only and should be `risk: safe`,
  but write that down before Phase 3 (Act + Verify + Risk) starts so
  the policy is consistent.

## FIND match-result enrichment (post-stash-survey ideas)

These three ideas came out of surveying the Explore-agent stash that
was dropped after Phase 2. The implementations in the stash weren't
worth porting (different conventions, more opaque scoring), but each
is a one-paragraph design hook worth considering for Phase 3 / 4 if
ambiguity resolution gets harder.

- **Derived `dialog_title` field on each MatchResult.** Currently the
  agent has to walk the `parents` chain looking for a `role == "dialog"`
  to know "what dialog am I in?" A top-level `dialog_title: str | None`
  on `MatchResult.to_dict()` would let an ambiguity-resolution loop say
  "the OK button in the **Save Changes?** dialog" without that walk.

- **Derived `nearby_text` field for unlabeled controls.** When a
  text_field has no label of its own but a sibling static_text labels
  it ("Filename:" + edit box), an agent has to deduce the relationship.
  A `nearby_text: str | None` field that aggregates the immediate
  siblings' labels would surface the relationship directly. Useful for
  messy WinUI surfaces where labels live in sibling controls.

- **Tree-distance decay on `--near`.** The shipped `--near` filter is
  boolean: same parent OR one-level-out (uncle-cousin). For ambiguity
  resolution, scoring by edge distance gives a ranking signal — when
  three buttons all qualify as "near", the closest one ranks higher.
  Would replace the binary filter with a distance-weighted scorer.

## Interface and protocol

- **Should there be a `sgcl capabilities` command?** *Decided: not now.* An
  agent cannot currently ask what the tool supports — the verbs, the adapter
  in use, the 42-entry role vocabulary, the query selectors. All of that data
  exists (`Adapter.name` / `.platform`, `_UIA_TO_ROLE`, `Query`), so the
  command would be close to free.

  Deferred anyway, because
  [`ADR-0006`](decisions/ADR-0006-agent-integration-surface.md) chose MCP as
  the programmatic surface, and **MCP's `tools/list` is capability
  introspection**. Building a bespoke `capabilities` verb now risks shipping
  a second description of the same thing that then has to be kept in step
  with the first — the exact failure this repo has spent a tier of issues
  correcting in its docs.

  **Revisit if:** Win 10 runs over the CLI (as
  [ADR-0006](decisions/ADR-0006-agent-integration-surface.md) expects) and
  the agent's prompt ends up hard-coding the role vocabulary or selector
  list. That is the concrete symptom that would justify it — and it is
  measurable during Win 10 rather than arguable now.

  Note the role vocabulary and selector list are *not* MCP tool schemas, so
  MCP would not fully subsume this. If the revisit happens, the honest scope
  may be "expose the reference data", not "expose the verbs".

- ~~**CLI-first, REST, JSON-RPC, or MCP-native?**~~ **Settled.** The CLI stays the reference surface; when a programmatic surface is built it is MCP, stateless, and not before Phase 3 lands. The stateful daemon is rejected for now. See [`ADR-0006`](decisions/ADR-0006-agent-integration-surface.md), which also tracks it as Win 11 so it stops being invisible.
- **Streaming vs request/response.** Still open, and now narrower: WAIT and OBSERVE-during-a-long-action want streaming, and MCP's tool-call model is request/response. Whether those verbs need a different shape — progress notifications, polling, or something else — is undecided and does not need deciding until Phase 3 defines WAIT.

## Language and platform stack

- ~~**Python-first or .NET-first for Windows UIA?**~~ ~~**Where does the core live?**~~ **Both settled in Phase 0.** Python for the core and the first adapter, with `uiautomation` as the UIA wrapper. See [`ADR-0003`](decisions/ADR-0003-python-and-uiautomation-for-the-first-adapter.md). It was a convenience-first spike decision and the ADR names the trigger most likely to reopen it: Phase 3 input synthesis, which `pywinauto` handles better than `uiautomation` and which Phase 0 never needed.

## Affordance graph stability

- ~~**How stable can control IDs be across sessions?**~~ **Settled in Phase 2.** They are not stable and deliberately so: ids are valid only within the invocation that produced them, with no session state and no synthetic ids. FIND returns the full affordance so an agent re-queries by selector rather than remembering an id. See [`ADR-0005`](decisions/ADR-0005-per-invocation-control-ids.md).
- **What changes between two observations of "the same" screen?** We need a definition before VERIFY's diff can be reliable. Note this is the identity question ADR-0005 defers rather than answers — VERIFY has to compare before and after states of "the same" control.

## Confidence

- ~~**How should `confidence` be calculated?**~~ **Settled in Phase 1.** Four binary signals at 0.25 each — populated label, specific role, at least one inferred action, and a stable identifier. The last of those was not in this question's original sketch and is the reason `AutomationId`-less apps score 0.75 rather than 1.0. See [`ADR-0002`](decisions/ADR-0002-adapter-confidence-scoring.md).
- **Open:** nothing clamps or validates `confidence` to `0..1` at the schema boundary. The range is documented, not enforced.

## Multi-monitor and virtual desktops

- **How should bounds be reported with negative coordinates and DPI scaling differences?** Probably: report virtual-screen coordinates as-is plus the monitor id when known. Document.
- **Virtual desktops.** Whether SGCL can even see windows on other virtual desktops varies by platform. Adapters report what they can.

## Vision and OCR

- **When does OCR enter?** Strictly as Win 8 (Repair & Fallback). Phases 0–3 must succeed without it. Once OCR exists, it is tempting to default to it; the engine should require an explicit `--fallback` (or equivalent policy flag) to use it.
- **Which OCR engine?** Tesseract is the cheapest; ONNX-based modern OCR is more accurate. Decision deferred to Win 8.

## Second adapter

- **Should browser DOM be the first second adapter?** It is the easiest second adapter by far (DOM is richer than any accessibility API) and tests whether the schema generalizes. The counter-argument: it is *too* easy, and won't actually stress-test the abstraction the way AT-SPI or AX would.
- **Or should we go straight to AT-SPI / AX?** Higher fidelity test of the cross-platform claim. Higher cost.

## Daemon state

- **How much state should the daemon hold?** Options: stateless (each call re-walks), session-scoped affordance cache, learned app maps, persistent learned maps. The risk of holding too much state is stale IDs and silent drift; the risk of holding too little is huge per-call walk costs.

## Core vs adapter responsibilities

- **What belongs in the core model vs adapter metadata?** Currently: role, label, value, enabled, visible, focused, bounds, parent/children, actions, risk, confidence are core. UIA's `AutomationId`, DOM's `aria-*`, AX's role descriptors are adapter metadata under `raw_ref`. Some borderline cases:
  - Keyboard shortcuts: probably core when exposed.
  - Hierarchical IDs (path-based): probably core.
  - Per-platform input methods (Wayland synthesis quirks): adapter only.

## Verification fidelity

- **What constitutes "success" vs "uncertain" in VERIFY?** Honest answer: the diff has to match the expected effect. We need to specify expected effects for each command before VERIFY's classifier is reliable.

## Agent ergonomics

- **How much should the response prose-explain itself to the LLM?** Probably: machine-readable JSON only, no prose. The LLM is the prose layer. But a `--human` flag for pretty output is fine.
