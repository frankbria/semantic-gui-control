# Find + Read Spike — Results

> Phase 2 acceptance: **met with caveats**. FIND and READ work end-to-end
> against real UIA surfaces. The synonym path is functional but requires
> `--text` (not `--label`) for synonym matching — a documentation /
> ergonomic issue, not a code bug. READ extracts values from both
> Calculator and Notepad through different extractor paths.

## Date

2026-05-20 (Phase 2, F.7 spike runs against the same Windows 11
environment used in Phases 0 and 1).

## Environment

- OS / build: Windows 11
- Shell host: Warp terminal (PowerShell profile) via Claude Code (bash)
- Python: 3.12 via `uv`
- UIA library: `uiautomation` (Yinkaisheng)
- Display config: multi-monitor; per-monitor DPI awareness honored.
- SGCL version: post-F.6 (slices F.1–F.6 pulled from `main` at commit
  `29cdb9d`)

## Apps tested

- [x] Notepad (Win11 WinUI; `Notepad.exe`) — opened with a multi-page
  markdown document (`contreras_proposal.md`)
- [x] Calculator (Win11 WinUI inside `ApplicationFrameHost.exe`) —
  Scientific mode, display showing `0`

Window handles resolved via `sgcl windows`:
- Calculator: `hwnd_8131088`
- Notepad: `hwnd_132842`

## Commands run

All commands used `--output` to bypass shell-pipe encoding. Sample
files in `spikes/samples/f7-*.json`.

### FIND commands

| ID | Command | Matches | Sample file |
|----|---------|--------:|-------------|
| F.7-A | `find --window $calc --label "="` | **0** | `f7-a-find-equals-by-synonym.json` |
| F.7-A2 | `find --window $calc --text "="` | **1** | `f7-a2-find-equals-by-text.json` |
| F.7-B | `find --window $calc --label "0"` | **3** | `f7-b-find-zero-by-synonym.json` |
| F.7-B2 | `find --window $calc --text "0"` | **5** | `f7-b2-find-zero-by-text.json` |
| F.7-C | `find --window $calc --role button` | **50** | `f7-c-find-all-buttons.json` |
| F.7-D | `find --window $notepad --role text_field` | **0** | `f7-d-find-notepad-editor.json` |
| F.7-D2 | `find --window $notepad --role document` | **1** | `f7-d2-find-notepad-document.json` |

### READ commands

| ID | Command | Source | Sample file |
|----|---------|--------|-------------|
| F.7-E | `read --window $calc --label "Display is 0"` | `label` (fallback) | `f7-e-read-calc-display.json` |
| F.7-F | `read --window $notepad --role document --max-length 200` | `value_pattern` | `f7-f-read-notepad-document.json` |

### Discovery command

| ID | Command | Purpose | Sample file |
|----|---------|---------|-------------|
| — | `find --window $calc --role static_text` | Enumerate all static_text controls | `f7-e-discovery-calc-static-text.json` |

## What worked

### Synonym matching via `--text`

The `--text "="` query found the Equals button (label: "Equals",
synonyms: `["="]`) with `match_confidence: 0.9` — exactly the synonym
score documented in the matcher. One match, no ambiguity. See
`f7-a2-find-equals-by-text.json`.

### Role-only filter

`--role button` returned all 50 Calculator buttons, matching the
Phase 0/1 count exactly. All 20 synonym-bearing controls survived with
correct synonyms. `match_confidence: 0.5` for role-only queries, as
documented. See `f7-c-find-all-buttons.json`.

### Notepad document discovery

`--role document` found the Notepad editor (ctrl_6, label: "Text
editor", native: `DocumentControl`). One match. See
`f7-d2-find-notepad-document.json`.

### READ — Calculator display

`read --label "Display is 0"` found the static_text control with
`AutomationId: CalculatorResults` and read it via the label fallback
reader. The result includes `descendant_text: "0 0"` (aggregated from
child controls). See `f7-e-read-calc-display.json`.

### READ — Notepad document content

`read --role document` extracted the full document text via
`ValuePattern.Value`. The `source: "value_pattern"` and
`details.read_only: false` confirm the ValuePattern path fired. See
`f7-f-read-notepad-document.json`.

### Non-ASCII survival

All Unicode characters survived intact in the JSON output files:

```
Pi          -> ['π']
Square root -> ['√']
Divide by   -> ['÷', '/']
Multiply by -> ['×', '*']
Minus       -> ['−', '-']
```

No mojibake observed. The `--output PATH` flag continues to be the
correct mitigation for the PowerShell pipe encoding issue from Phase 1.

## What failed / surprised

### `--label` does not search synonyms

**The handoff prompt's spike commands used `--label "="` expecting
synonym matching. That returned 0 matches.** This is by design — the
matcher's `--label` flag does case-insensitive exact match on the
`label` field only (line 257–261 of `matcher.py`). Synonym matching
requires `--text`, the broad selector that tries label → synonyms →
description → label_contains in priority order.

This is not a code bug; the matcher's module docstring documents the
distinction clearly. But it is an **ergonomic surprise** — an agent
asked to "find the = button" would naturally use `--label "="` and get
nothing.

**Recommendation for Phase 3:** Consider whether `--label` should also
check synonyms (with a lower match_confidence than exact label), or
whether the `--text` vs `--label` distinction should be made more
prominent in help text. Alternatively, make `--text` the default agent
interface and relegate `--label` to "strict exact match."

### `--text "0"` is noisy

The query `--text "0"` returned 5 matches:

1. Display pane (label "0", exact match, combined_rank 1.0)
2. NormalOutput static_text (label "0", exact match, combined_rank 1.0)
3. Zero button (synonym "0", combined_rank 0.9)
4. Child static_text of Zero button (label "0", combined_rank 0.75)
5. "Display is 0" static_text (label_contains, combined_rank 0.7)

The Zero button is rank #3. An agent would need `--text "0" --role
button` to isolate it (1 match, the Zero button). This pattern —
combining a text selector with a role filter — is the intended usage
but should be documented as the recommended pattern for digit queries.

### Notepad's role is `document`, not `text_field`

`--role text_field` returned 0 matches. Notepad's editable area exposes
`DocumentControl` (normalized to `document`). The handoff prompt
anticipated this ("If empty, try --role document"), but it means an
agent looking for "text fields" in Notepad won't find the editor unless
it knows to query `document`. This is a real UIA naming issue.

### `--max-length` does not apply to ValuePattern

The command `read --role document --max-length 200` returned the full
document (several thousand words). The `--max-length` parameter only
applies to `TextPattern.DocumentRange.GetText(max_length)` (extractor
priority #2). Notepad's document control exposed `ValuePattern` (priority
#1), which fired first and returned the full value without truncation.

This is correct behavior per the extractor priority order, but it means
`--max-length` is effectively a no-op for controls that have both
ValuePattern and TextPattern, since ValuePattern always wins. Phase 3
should decide whether to add a `--max-length` cap to ValuePattern as
well, or document this behavior.

### Calculator display label is dynamic

The label "Display is 0" changes as the display value changes (e.g.,
"Display is 42"). An agent cannot hardcode `--label "Display is 0"` for
repeated reads — it would need `--label-contains "Display is"` or target
by AutomationId. Since `--automation-id` is not a selector in the
current matcher, the most robust approach is probably
`--label-contains "Display is"` or a future `--automation-id` selector.

## Match-confidence calibration evidence

### Synonym hit: "=" → Equals button

```json
{
  "match_confidence": 0.9,
  "combined_rank": 0.9,
  "control": { "label": "Equals", "synonyms": ["="], "confidence": 1.0 }
}
```

Score of 0.9 for synonym hit feels correct — it's not an exact label
match but it's a strong signal. The combined_rank of 0.9 (0.9 × 1.0)
correctly reflects that both the match and the adapter confidence are
high.

### Broad text match: "0" across multiple controls

| Control | match_confidence | adapter confidence | combined_rank | Why |
|---------|------------------|--------------------|---------------|-----|
| Display pane (label "0") | 1.0 | 1.0 | 1.0 | Exact label match |
| NormalOutput (label "0") | 1.0 | 1.0 | 1.0 | Exact label match |
| Zero button (synonym "0") | 0.9 | 1.0 | 0.9 | Synonym hit |
| Zero child text (label "0") | 1.0 | 0.75 | 0.75 | Exact but low adapter conf |
| "Display is 0" (substring) | 0.7 | 1.0 | 0.7 | Label-contains match |

The ranking is reasonable: exact label matches outrank synonym matches,
and the combined_rank correctly down-weights controls with lower adapter
confidence. However, the display pane and NormalOutput tying at 1.0
while the Zero *button* is at 0.9 is unintuitive — an agent asking for
"0" probably wants the button, not the readout. A role filter
(`--role button`) solves this in practice.

### Role-only filter

All 50 Calculator buttons received `match_confidence: 0.5` (the
role-only score). This is appropriate — the match is structurally valid
but carries no text-based evidence.

## READ pattern hit-rate

| Command | Control | Reader path | Details |
|---------|---------|-------------|---------|
| F.7-E | Calculator CalculatorResults (static_text) | `label` (fallback #5) | `value: "Display is 0"`, `descendant_text: "0 0"` |
| F.7-F | Notepad document (DocumentControl) | `value_pattern` (#1) | Full document text, `read_only: false` |

Only two of the five reader paths fired across these two apps:

- **ValuePattern** (priority 1) — fired for Notepad's DocumentControl.
  This is the "text field" path.
- **Label fallback** (priority 5) — fired for Calculator's display.
  Calculator's CalculatorResults static_text doesn't expose ValuePattern,
  TextPattern, TogglePattern, or SelectionPattern, so the fallback
  aggregated the label and descendant text.

Not tested in this spike:
- **TextPattern** (priority 2) — would fire for controls with
  TextPattern but not ValuePattern. Notepad's DocumentControl had
  ValuePattern, which took priority.
- **TogglePattern** (priority 3) — would need a checkbox or toggle
  control. Calculator's Scientific mode has some toggle-like buttons
  but they may not expose TogglePattern via UIA.
- **SelectionPattern** (priority 4) — would need a list, tab, or combo
  box control.

## Performance notes

All commands completed in under 2 seconds. No noticeable wall-clock
difference between FIND and READ, or between Calculator (126 controls
at depth 8) and Notepad (36 controls at depth 3). The Notepad document
read returned several thousand words of text via ValuePattern without
observable delay.

The Calculator button query (`--role button`, 50 matches) was also fast
despite returning a large JSON payload (~30K characters).

## New questions for Phase 3

1. **Should `--label` check synonyms?** The current design makes
   `--label` strict-exact and `--text` broad. An agent prompted to "find
   the = button" would naturally use `--label`, miss the synonym, and
   need to be taught to use `--text`. Consider: (a) making `--label`
   check synonyms at 0.9, (b) adding an alias `--name` that checks both,
   or (c) documenting `--text` as the primary agent-facing selector.

2. **Should `--max-length` cap ValuePattern too?** Currently it only
   caps TextPattern. An agent reading a large document via ValuePattern
   gets the full text regardless of `--max-length`. This could be
   expensive or overwhelm context windows.

3. **How should an agent target Calculator's display reliably?** The
   label "Display is 0" is dynamic. Options: add `--automation-id`
   selector, use `--label-contains "Display is"`, or use
   `--role static_text --label-contains "Display"`.

4. **Role naming for editable areas:** Notepad's editor is `document`,
   not `text_field`. An agent needs to know this. Phase 3's agent
   documentation should include a role-mapping guide for common app
   surfaces.

5. **TogglePattern and SelectionPattern coverage:** Neither path was
   exercised in this spike. Phase 3 should test against a dialog with
   checkboxes, radio buttons, combo boxes, or tab controls to validate
   those reader paths against real UIA surfaces.

6. **Risk model for READ:** Phase 3 lands execution and risk together.
   READ is read-only and should be `risk: safe`, but the current risk
   model in `docs/risk-model.md` doesn't explicitly classify READ. It
   should.

## Linux-side verification (post-merge)

After the Windows session pushed, the Linux side cross-checked the
report's headline claims against the committed sample files:

- **F.7-A** (`--label "="`) really did return 0 matches. The empty
  `{"matches": []}` JSON is in the file.
- **F.7-A2** (`--text "="`) returned the Equals button at
  `match_confidence: 0.9`, `combined_rank: 0.9`. Synonym path confirmed.
- **F.7-B2** (`--text "0"`) returned 5 matches in the exact order the
  report describes: two exact-label `1.0` hits (the display pane and
  NormalOutput static_text), the Zero button via synonym at `0.9`, a
  child static_text at `0.75` (label hit × lower-confidence
  affordance), and "Display is 0" via label_contains at `0.7`.
- **F.7-E** (Calculator display read) returned `source: "label"`,
  `value: "Display is 0"`, `details.descendant_text: "0 0"`, with the
  affordance carrying `raw_ref.AutomationId: "CalculatorResults"` —
  confirming the dynamic-label finding and the stable AutomationId
  hook the report points at as the right long-term selector.
- **F.7-F** (Notepad document read) returned `source: "value_pattern"`,
  `read_only: False`, full document content at 21,783 characters.
  That length matches the "21,783 characters" status-bar readout that
  Phase 0's Notepad sample exposed at depth 3 — independent
  confirmation that ValuePattern is returning the same document the
  user sees.

## Acceptance against the F.7 checklist

- [x] All sample files exist and contain valid JSON with non-ASCII
      preserved.
- [x] Synonym match via `--text "="` returns one Equals button.
- [x] Role-only filter returns all 50 Calculator buttons.
- [x] Calculator display readable via FIND + READ.
- [x] Notepad document readable via READ (ValuePattern path).
- [x] No SGCL source files modified by the Windows session.
- [x] Spike report exists, well-structured, and lists concrete Phase 3
      questions.

## Decisions for Phase 3

The six "new questions" above are the Phase 3 carry-forwards. They
get propagated into `docs/open-questions.md` so they're not lost when
the spike note ages out. None of them block the start of Phase 3
(Act + Verify + Risk) — they're design refinements that fit naturally
alongside the execution work.

GitHub issues #3 (Find) and #4 (Read) close against this report.
