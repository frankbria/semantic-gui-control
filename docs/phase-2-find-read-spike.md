# Phase 2 Plan — Find + Read

## Context

Phases 0 (Observe) and 1 (Normalize) are shipped on `main`. The repo
produces a normalized affordance graph with `confidence`, `synonyms`,
`description`, `is_system_surface`, and a structural-pane-reduced tree.
GitHub issues #1 and #2 are closed against their spike reports.

Phase 2 (Find + Read) — GitHub issues #3 and #4 — answers two of the
roadmap's coarse learning questions:

> Can an agent find the thing it means without knowing screen coordinates?
> Can the system read enough state to support agent reasoning and verification?

Phase 1 made those answers actually possible. The synonym map exists so
`--label "0"` can match a button named "Zero". The description field
exists so icon-glyph labels stop being opaque. The confidence field
exists so the affordance can carry its own quality signal separately
from an agent's match score. Phase 2 is where all of that gets
consumed.

A previous in-session attempt by a runaway Explore subagent produced
unreviewed code for parts of this work. That work is now in
`git stash@{0}` for later survey. This plan is written fresh from the
shipped state of `main`, not from the stashed code.

## Goal

Implement `sgcl find` and `sgcl read` against the normalized affordance
graph. FIND takes selectors (role, label, synonyms, description, text,
state, structural relationships) and returns ranked candidates. READ
takes the same selectors (or a `ctrl_id` from a fresh FIND) and
extracts value / state / selection / aggregated visible text via UIA
patterns (`ValuePattern`, `TextPattern`, `TogglePattern`,
`SelectionPattern`).

## Approach: state-free, selector-driven

Control IDs remain per-invocation (no session state yet). FIND returns
the **full normalized affordance** for each match — the agent has
everything (label, role, AutomationId in `raw_ref`, etc.) needed to
re-query in a later command without depending on an unstable id. READ
defaults to taking selectors directly and re-walking; a `--target
<ctrl_id>` mode exists for chaining inside the same fresh walk but is
documented as fragile.

Phase 2 stays read-only. No FOCUS, TYPE, INVOKE, SELECT, SCROLL —
those land in Phase 3.

## Persistence — where this plan lives once approved

On first exit from plan mode, the plan moves to the repo at
`docs/phase-2-find-read-spike.md` (replacing the stale Phase-1-era
draft). That file is the durable, versioned home. The
`~/.claude/plans/crystalline-jingling-clover.md` slug is ephemeral
and disappears with the plan session.

## Automation — splitting Linux dev from Windows testing

The recurring friction in Phases 0/1 was the manual round-trip:
Linux session writes code → push → user manually pulls on Windows →
runs commands → pushes samples → Linux session pulls → analyzes.
Each round is slow because a human (the user) couriers the artifacts.

Phase 2 splits along the same boundary, but with explicit automation:

- **Linux side (this session):** all slices F.1–F.6. All Linux-
  testable (matcher, reader, CLI plumbing, ergonomics). I push to
  `main` after each.
- **Windows side (a second Claude Code session, running natively
  in PowerShell):** slice F.7 (spike runs + report) **and**
  optionally per-slice smoke checks after each push.

I cannot orchestrate the Windows side from here — there is no
remote-execution channel to the user's Win11 box from this Linux
WSL session. The handoff is the user kicking off a Windows-native
Claude Code session and pasting a pre-written prompt.

Concretely, two new files in the repo (created on plan exit, not now):

1. `docs/windows-handoff-prompt-phase-2.md` — a self-contained
   prompt the user pastes into a Windows-side Claude Code session.
   That session pulls latest, runs the spike commands (FIND and
   READ against Notepad and Calculator), commits the samples to
   `spikes/samples/`, pushes them, and writes back a one-paragraph
   summary in the same commit. This Linux session then pulls and
   analyzes.

2. `docs/windows-claude-setup.md` — short doc covering: which
   `uv`-managed Python to install, how to enable
   `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` (so
   even non-`--output` commands behave), and any other one-time
   Windows-side setup. Phase 2 reuses the Windows env from Phase 1
   (already working), so this doc is short.

The Windows-handoff prompt is generic enough to reuse for Phase 3 and
beyond by parameterizing "which slice are we running" at the top.

## Slicing — independently mergeable

Same cadence as Phase 1's E.1–E.7. Each slice ends in tests + commit
+ push.

### F.1 — Matcher core (Linux-testable)

New module `sgcl/core/matcher.py`. Pure functions over a `Control`
tree. No CLI, no adapter dependency.

- `match_query(root, query)` — walks the tree and returns
  `list[MatchResult]`. Each `MatchResult` carries the matched
  `Control` plus a `match_confidence: float` (separate from the
  affordance's own `confidence`).
- Query fields, all optional:
  - `role: str` (exact match against normalized role)
  - `label: str` (case-insensitive exact)
  - `label_contains: str` (case-insensitive substring)
  - `text: str` (matches `label`, any entry in `synonyms`, or
    `description`)
  - `state` flags: `enabled`, `visible`, `focused` (each tri-state:
    True/False/None)
- Match-confidence scoring (documented in module docstring):
  - Exact label = 1.0
  - Synonym hit = 0.9
  - Description hit = 0.85
  - `label_contains` = 0.7
  - Role-only filter (no text criterion) = 0.5
- Combined ranking key = `match_confidence * affordance.confidence`.
  Ambiguity is **explicit** — multiple matches are returned, never
  guessed away.
- Tests: synthetic `Control` trees (no walker, no CLI). Cover each
  selector type, synonym-hit precedence, role-only filters, state
  filters, ambiguity.

### F.2 — Relationship filters

Extend the matcher.

- `inside: str` — id of an ancestor control. Match only if the
  candidate is a descendant.
- `near: str` — id of a sibling or near-sibling control. "Near" =
  same parent, or parent's sibling chain within one level (kept
  simple; documented).
- `with_parent_role: str` — direct parent has the given role. Useful
  for "OK button inside a Dialog".
- Tests: synthetic trees that exercise each relationship and
  combinations.

### F.3 — Reader core (Linux-testable, duck-typed)

New module `sgcl/adapters/windows_uia/_readers.py`. Duck-typed (mirrors
the Phase 1 walker split) so unit tests pass on Linux against mocks.
The actual COM-level pattern calls happen here but the function takes
a control object via parameter, so a mock works.

- `read_value(ctrl) -> ReadResult` with extractor priority:
  1. `ValuePattern.Value` → `{value, read_only}`
  2. `TextPattern.DocumentRange.GetText(n)` → `{value, truncated}`
     (cap `n` at a `--max-length` default, e.g. 4096 chars)
  3. `TogglePattern.ToggleState` → `{state: "on" | "off" |
     "indeterminate"}`
  4. `SelectionPattern.GetSelection()` → list of selected items
  5. Fallback: the control's `label` plus aggregated visible text
     from descendants
- `ReadResult` shape includes `supported: bool` — honest `False` when
  none of the extractors fired.
- Tests: mock controls exercising each pattern path, fallback,
  truncation, and the `supported: false` path.

### F.4 — CLI plumbing for FIND

- New subcommand `sgcl find` accepting:
  - Window targeting: same flags as `inspect` (`--active`,
    `--window`, `--process`, `--title`, `--pid`, `--include-system`).
  - Query flags: `--role`, `--label`, `--label-contains`, `--text`,
    `--enabled` / `--disabled`, `--visible` / `--hidden`, `--focused`
    / `--unfocused`, `--inside`, `--near`, `--with-parent-role`.
  - `--limit N` (default unlimited; print all matches).
  - `--depth N` (default `8`; see F.6).
  - Honors `--pretty` and `--output PATH` from the top-level parser.
- Output JSON: `{ "matches": [ {affordance, match_confidence,
  combined_rank, parents: [list of ancestor labels/roles for context]}
  ] }`. Always a list, even for one match.
- Linux-testable via the `FakeAdapter` plus a small static graph
  fixture.

### F.5 — CLI plumbing for READ

- New subcommand `sgcl read` accepting:
  - Window targeting: same as FIND.
  - One of (mutually exclusive):
    - A FIND-style selector group (`--role`, `--label`, etc.) — does
      a fresh walk + match + read. Errors on ambiguity (≥2 matches)
      the same way inspect's `--process` does today.
    - `--target ctrl_X` — only valid against a freshly-walked tree.
      Documented as fragile across invocations.
  - `--max-length N` (default 4096) for `TextPattern` extraction.
- Output JSON: the `ReadResult` shape from F.3 plus `affordance` (the
  resolved control) and `supported`.

### F.6 — Defaults and ergonomics

Small things that surfaced from Phase 1 we should fix while touching
the CLI:

- Change `inspect --depth` default from `3` to `8`. Phase 1 proved
  the WinUI keypad is at depth 7+, and `3` was a Phase 0 placeholder.
- README: add the recommended invocation pattern using `--output
  PATH` (per the Phase 1 spike's "out-of-band follow-ups").
- Extend `sgcl/core/icon_glyphs.py` with the 12 codepoints listed in
  `spikes/normalize-results.md` (U+E61D, U+E81C, U+E94F, U+F754–F758,
  U+F7C8, U+F7CF, U+F892, U+F893, U+F897).

### F.7 — Windows re-runs + spike report (executed by Windows-side Claude)

The Windows-side Claude session, kicked off by the user pasting
`docs/windows-handoff-prompt-phase-2.md`, performs:

- `git pull` and `uv sync --extra dev --extra windows`.
- Spike commands (each writes to `spikes/samples/` via `--output`,
  no shell-pipe encoding traps):
  - `sgcl find --window <calc> --label "="` — should match Equals
    via synonym, return one result.
  - `sgcl find --window <calc> --label "0"` — should match Zero via
    synonym.
  - `sgcl find --window <calc> --role button` — should return all
    50 buttons.
  - `sgcl find --window <notepad> --role text_field` — should find
    the document area.
  - `sgcl read --window <calc> --label "="` after some button
    presses — verifies display readback through the synonyms path.
  - `sgcl read --window <notepad> --role document --max-length 200`
    — Notepad's content, truncated.
- A first draft of `spikes/find-read-results.md` covering: which
  selectors worked best, match-confidence calibration evidence, READ
  pattern hit-rates, performance observations, new questions for
  Phase 3.
- Commit + push.

This Linux session then pulls, reviews, refines the spike note, and
closes GitHub issues #3 (Find) and #4 (Read).

## Out of scope

- Any execution: FOCUS, TYPE, INVOKE, SELECT, SCROLL — Phase 3.
- Session / persistent control IDs — Phase 5+ if ever.
- Fuzzy matching beyond `label_contains`. YAGNI; revisit if Phase 2
  spike runs show it's a real gap.
- A second adapter (browser DOM / AT-SPI / AX) — Phase 9.
- Vision / OCR fallback — Phase 8.

## Critical files

To create on plan exit:

- `docs/phase-2-find-read-spike.md` — durable plan home (overwrite
  the stale draft).
- `docs/windows-handoff-prompt-phase-2.md` — the prompt the user
  pastes into a Windows-side Claude session.
- `docs/windows-claude-setup.md` — one-time Windows env notes (short;
  Phase 1's env is already working).

To create during slices:

- `sgcl/core/matcher.py` — pure matcher.
- `sgcl/adapters/windows_uia/_readers.py` — duck-typed reader.
- `tests/test_matcher.py`, `tests/test_readers.py`.

To modify:

- `sgcl/cli.py` — `find` and `read` subcommands.
- `sgcl/adapters/windows_uia/_adapter.py` — wire `read_value` through
  a new `Adapter.read(window_id, ctrl_id)` method (or similar).
- `sgcl/core/adapter_base.py` — add the `read` abstract method.
- `sgcl/core/icon_glyphs.py` — extend `_ICON_NAMES`.
- `tests/conftest.py` — extend `FakeAdapter` with a richer fixture
  tree (multiple buttons, a checkbox, a text field, a static-text
  display) so CLI tests cover real query scenarios.

## Reusing existing code

- `sgcl/cli.py:_filter_windows`, `_process_matches`, `_title_matches`,
  `_resolve_window_id` (lines ~175–225) — the FIND-targeting flags
  match the same patterns; implementation should follow the same
  shape.
- `sgcl/core/confidence.py:score_control` — defines adapter
  confidence. The matcher's `match_confidence` is a separate signal
  with its own scoring; combine via `match_confidence * confidence`.
- `sgcl/adapters/windows_uia/_walker.py:infer_actions` — already
  inspects pattern availability for action inference. The READ
  module uses the same pattern getters but invokes their value
  accessors (e.g., `ValuePattern.Value`, not just
  `GetValuePattern() is not None`).
- `tests/test_walker.py:_FakeCtrl` — the mock pattern. Extend it
  with `Value`, `Text`, `Toggle`, `Selection` pattern returns for
  reader tests.

## Verification

After all slices:

1. `uv run pytest -q` — full suite green on Linux, target ~150 tests.
2. `uv run ruff check . && uv run black --check .` — clean.
3. Windows-side Claude session per F.7 produces non-empty match
   lists and readable values for both Notepad and Calculator.
4. `sgcl find --window <calc> --label "0"` returns exactly one
   match (the "Zero" button) — proves the synonym path works
   end-to-end.
5. `sgcl read` against Calculator's `NormalOutput` returns the
   current display value as a string — proves the static-text
   fallback works.

## Risks

- **Match-confidence calibration is vibes-based** until Phase 10
  (Agent Loop) gives real feedback. Mitigation: keep the scoring
  rule small and documented so it can be tuned.
- **`TextPattern.DocumentRange` for Notepad's document may be slow
  or huge.** `--max-length` and a default cap protect the spike.
- **Per-invocation control IDs may surprise agents.** Mitigation:
  FIND returns the full affordance, not just an id; the recommended
  usage is selector-based throughout.
- **The Windows-handoff prompt is a new dependency on the user
  remembering to start a Windows-side Claude session.** Mitigation:
  the prompt is one-shot; the user pastes it, the Windows session
  does the whole F.7 sequence without further hand-holding.
- **The stashed previous-attempt code might have made different
  decisions** (e.g., different field names, different module layout).
  After this plan ships, do a survey pass to extract any reusable
  bits before discarding the stash.
