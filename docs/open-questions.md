# Open Questions

Things we have not decided. Some block future phases; some are fine to defer. Each spike should add to this list, and resolved questions should move to `docs/decisions/` as ADRs.

## Targeting

- **System/shell windows.** Phase 0 surfaces `Program Manager`, the taskbar,
  and other shell windows in `sgcl windows`. Should the CLI filter these by
  default, expose a `--include-system` flag, or always emit and let the
  agent filter? Resolved finding: focus-based targeting is unreliable from a
  CLI (see `spikes/windows-observer-results.md` Run 1) — this is now a
  documented constraint, not an open question.

## FIND ergonomics (from Phase 2 spike)

- **Should `--label` check synonyms?** Phase 2 confirmed that
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

- **CLI-first, REST, JSON-RPC, or MCP-native?** Phase 0 is CLI-only. Phase 2/3 may want a daemon. Should the daemon expose a generic JSON-RPC, a REST surface, or an MCP server natively so an LLM client can use the verbs as MCP tools? MCP-native is appealing for agent use; JSON-RPC is simpler to implement; REST is most generic.
- **Streaming vs request/response.** Some operations (WAIT, OBSERVE during a long-running action) want streaming. Worth deciding before the daemon API is fixed.

## Language and platform stack

- **Python-first or .NET-first for Windows UIA?** Python (`pywinauto`, `uiautomation`, `comtypes`) is faster to spike and easier to compose with cross-platform glue. .NET / C# gives the most direct, fastest UIA access. The choice may differ for the adapter vs the core.
- **Where does the core live?** Most natural to keep the core in one language (Python) and let adapters be language-specific subprocesses or sidecars when needed.

## Affordance graph stability

- **How stable can control IDs be across sessions?** UIA `AutomationId` is sometimes stable, sometimes empty, sometimes generated. AT-SPI and AX have similar fragility. We may need a synthetic stable id derived from `(role, label, parent-chain, ordinal)`.
- **What changes between two observations of "the same" screen?** We need a definition before VERIFY's diff can be reliable.

## Confidence

- **How should `confidence` be calculated?** Phase 1 will start with a coarse rule (clean role + non-empty label + supported patterns = 1.0; degrade per missing input). A more principled scheme can wait, but the coarse rule must be documented so adapters do not invent their own.

## Multi-monitor and virtual desktops

- **How should bounds be reported with negative coordinates and DPI scaling differences?** Probably: report virtual-screen coordinates as-is plus the monitor id when known. Document.
- **Virtual desktops.** Whether SGCL can even see windows on other virtual desktops varies by platform. Adapters report what they can.

## Vision and OCR

- **When does OCR enter?** Strictly as Phase 8 (Repair & Fallback). Phases 0–3 must succeed without it. Once OCR exists, it is tempting to default to it; the engine should require an explicit `--fallback` (or equivalent policy flag) to use it.
- **Which OCR engine?** Tesseract is the cheapest; ONNX-based modern OCR is more accurate. Decision deferred to Phase 8.

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
