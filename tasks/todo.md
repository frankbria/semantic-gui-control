# SGCL — Next Actions

Short, ordered checklist of what to do next. Detailed acceptance criteria live in the per-phase docs and in `docs/github-issues-seed.md`; this file is just the running queue.

When a step is done, check it off. When a step opens up new questions, log them in `docs/open-questions.md`.

## A. GitHub housekeeping (one-time)

- [x] Set the repo About description on github.com.
- [x] Add topic tags (e.g., `ai-agents`, `llm`, `agentic-ai`, `gui`, `gui-automation`, `ui-automation`, `accessibility`, `desktop-automation`, `computer-use`, `cross-platform`, `windows`, `python`).
- [x] Verify the issue templates render on the "New issue" page (`.github/ISSUE_TEMPLATE/blunt-win.md`, `spike.md`).
- [x] Create the first 7 blunt-win issues from `docs/github-issues-seed.md`. Labels `blunt-win` and `spike` created; issues #1–#7 opened.
- [ ] (Optional) Create a GitHub Project board with one column per phase.

## B. Phase 0 prep — environment

- [x] Decide UIA library for the spike: **`uiautomation` (Yinkaisheng)**. Reasoning captured in `spikes/windows-observer-results.md` (close to raw UIA primitives, good fit for read-only tree dumping).
- [x] Confirm a Windows dev environment is available. (Available; specifics to be filled in when Phase 0 starts.)
- [x] Initialize Python project: `pyproject.toml` (>=3.11), `.python-version` (3.12), `ruff` + `black` config, `pytest` configured. `uv sync --extra dev` clean.
- [x] Create the empty package skeleton matching `docs/architecture-overview.md`:
  - [x] `sgcl/core/` (empty)
  - [x] `sgcl/adapters/windows_uia/` (empty)
  - [x] `sgcl/cli.py` (stub `main()` only — entry point registered as `sgcl`)
- [x] Set up pre-commit hooks (`.pre-commit-config.yaml` with ruff + black + standard pre-commit-hooks; installed via `uv run pre-commit install`). Note: no shared template existed at `/home/frankbria/projects/templates`; modeled config on `codeframe`'s.

## C. Phase 0 — Observe

Authoritative checklist: [`docs/phase-0-observe-spike.md`](../docs/phase-0-observe-spike.md). Summary:

- [x] Implement `sgcl windows` (list with title, process, pid, bounds, visible, active). _Implemented in `sgcl/adapters/windows_uia/`._
- [x] Implement `sgcl active` (foreground window).
- [x] Implement `sgcl inspect --active --depth N` (hierarchical control tree JSON). Also supports `--window hwnd_<int>`.
- [x] Verify JSON output for each command is parseable and conforms to the spike schema. _29 Linux-runnable tests, all green._
- [x] Test against **Notepad** end-to-end. _32 actionable controls; status bar exposes cursor/length/encoding as readable static_text._
- [x] Test against **Calculator** end-to-end. _Full scientific keypad (50 buttons) + display (`NormalOutput`) surfaced at depth 8._
- [x] Fill in `spikes/windows-observer-results.md` (every section). _Done across 3 runs._
- [x] Add any new unknowns to `docs/open-questions.md`. _System/shell window filtering added; focus-reliability question converted to a documented constraint._

## D. Phase 0 wrap-up — decide before Phase 1

- [x] Review the spike note: did Phase 0 produce a working capability, a documented constraint, or a killed assumption? _All three. See `spikes/windows-observer-results.md`._
- [x] Update `docs/phase-1-normalize-spike.md` with the contradictions Phase 0 surfaced (walker strategy, icon-font handling, system surfaces filter, pane reduction, synonyms).
- [x] Close GitHub issue #1 (`[blunt-win] Observe`) with a link to the spike note.
- [x] Open the `[blunt-win] Normalize` issue (already issue #2).

## E. Phase 1 — Normalize

Authoritative checklist: [`docs/phase-1-normalize-spike.md`](../docs/phase-1-normalize-spike.md).
Sliced into independently mergeable chunks. Do them in order; each one
ends in a commit + push, and the Windows-side runs can re-verify between
slices.

### E.1 — Schema additions (Linux-testable)

- [x] Add `confidence: float` and `description: str | None` and `synonyms: list[str]` to `Control`.
- [x] Add `is_system_surface: bool` to `WindowInfo`.
- [x] Update `to_dict()` on both. Round-trip tests. (33 tests passing.)
- [x] Updates to `docs/affordance-model.md` deferred — the doc is the target spec, and E.1 only adds defaulted fields. E.2–E.6 populate them; spike report in E.7 will sync the doc once content is real.

### E.2 — Confidence scoring (Linux-testable heuristic)

- [x] Implement a coarse heuristic: 0.25 per signal (label populated / role specific / actions present / stable id present). Lives in `sgcl/core/confidence.py`, platform-neutral.
- [x] Wire into the Windows UIA adapter; AutomationId acts as `stable_id`.
- [x] Linux tests with synthetic inputs (11 tests covering each signal, realistic cases, and edge conditions). 44 tests total, all green.

### E.3 — Walker exception logging + system-surface filter

- [x] Replace silent `except Exception: pass` around `GetChildren()` with stderr logging (`[sgcl] WARN: GetChildren() failed on <id> (<role>): <exc>`).
- [x] Tag known system windows (`Program Manager`, taskbar / shell windows) with `is_system_surface=True`. Heuristic in `sgcl/adapters/windows_uia/_system.py`: `explorer.exe` + empty/known-shell title. Doesn't false-positive on opened File Explorer folders.
- [x] `sgcl windows` excludes them by default; `--include-system` opts in. Same flag added to `sgcl inspect` (applied to `--process`/`--title`/`--pid` matching; `--window` and `--active` are explicit and unaffected).
- [x] Walker refactored into `_walker.py` (duck-typed, no UIA import) so it's importable + testable from Linux. Adapter glue moved to `_adapter.py`; `__init__.py` conditionally re-exports. 66 tests, all green.

### E.4 — Icon-font label handling

- [x] Small static map of PUA codepoints (Segoe Fluent Icons / Segoe MDL2 Assets) → human description in `sgcl/core/icon_glyphs.py`. Starter set sourced from Microsoft's published references. Easy to extend as new codepoints turn up.
- [x] Populate `description` when a label is purely PUA glyphs *and* all codepoints are in the map. Mixed text+glyph and partially-known cases yield `None` (prefer silence to half-truth).
- [x] 10 unit tests + 2 walker integration tests. 76 total, all green.

### E.5 — Structural pane reduction

- [x] Walker post-process (`flatten_structural_panes`): bottom-up collapse of unlabeled single-child `pane` chains. Description-bearing panes (icon-font hints) are preserved. Root preserved even if it qualifies.
- [x] Flattened ids recorded in survivor's `raw_ref.flattened` (bottom-up order).
- [x] Adapter's `inspect_window` applies the pass after `build_control`. 7 new tests covering single-pane collapse, chain collapse, labeled-pane preservation, multi-child preservation, root preservation, description-bearing preservation, non-pane preservation. 83 tests total, all green.

### E.6 — Label synonyms (Calculator-focused, easy to extend)

- [x] Static map in `sgcl/core/synonyms.py`: digits Zero–Nine → "0"–"9"; Plus/Minus/Multiply by/Divide by/Equals → operator symbols (both Unicode and ASCII for ± / × / ÷); Decimal separator → "."; parens, Pi, Square root.
- [x] Lookup is case-insensitive, trims whitespace, refuses partial matches ("Positive negative" doesn't get Plus/Minus synonyms).
- [x] Walker populates `synonyms` on every control via `synonyms_for(label)`.
- [x] 14 unit tests + 2 walker integration tests.

### E.6b — `--output PATH` flag

Phase 1 Run 4/5 revealed that PowerShell's pipe decodes our UTF-8 stdout bytes as cp437 before re-encoding through `Out-File`. Result: every non-ASCII synonym became mojibake on disk. Python's in-memory values were correct (`_LABEL_SYNONYMS['pi']` returns `('π',)` on Windows).

- [x] Add `--output PATH` to all subcommands (accepted before or after the subcommand). When given, sgcl opens the file with explicit UTF-8 encoding from Python and writes JSON directly — no shell pipe involved.
- [x] Revert the defensive `\uXXXX` escapes in `synonyms.py` back to literal Unicode (the escapes were a misdiagnosed fix; runtime values were always correct).
- [x] 3 new tests (writes UTF-8, preserves non-ASCII bytes, works before subcommand). 110 tests total, all green.

### E.7 — Windows re-runs + spike report

- [x] Re-run Notepad and Calculator captures with the normalized output (samples 10–15).
- [x] Compare control counts: Notepad −16% (43 → 36, 7 panes flattened). Calculator unchanged at 126 (GroupControl, not PaneControl — heuristic deliberately targets panes).
- [x] Confidence is not uniformly 1.0: Notepad 11/17/6/2/0 across tiers; Calculator 56/62/6/2/0.
- [x] Write `spikes/normalize-results.md`: size delta, confidence histogram, synonyms validated (20 controls), icon-glyph descriptions (2 of 27 PUA codepoints mapped — clear extension path), PowerShell-pipe encoding finding documented.
- [x] Close GitHub issue #2 (`[blunt-win] Normalize`) with a link.

## F. Phase 2+ — pointer

Don't start until E is done.

- [`docs/phase-2-find-read-spike.md`](../docs/phase-2-find-read-spike.md) — Find + Read.
- [`docs/phase-3-act-verify-risk-spike.md`](../docs/phase-3-act-verify-risk-spike.md) — Act + Verify + Risk.

## Notes

- **One phase at a time.** Don't pre-implement Phase 2 work inside Phase 0. If a Phase 0 task feels like it needs Phase 2 functionality to be useful, that means Phase 0 scope is wrong, not that you should reach forward.
- **No mocking of real surfaces.** Notepad and Calculator are the real test targets. If they're not available, say so — don't fake the adapter.
- **Vision is Phase 8.** Not earlier. Even if it's tempting when UIA returns garbage.
