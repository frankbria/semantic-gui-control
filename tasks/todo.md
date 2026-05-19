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

- [ ] Add `confidence: float` and `description: str | None` and `synonyms: list[str]` to `Control`.
- [ ] Add `is_system_surface: bool` to `WindowInfo`.
- [ ] Update `to_dict()` on both. Round-trip tests.
- [ ] Update `docs/affordance-model.md` to reflect what we actually ship.

### E.2 — Confidence scoring (Linux-testable heuristic)

- [ ] Implement a coarse heuristic: clean label + role + ≥1 action = 1.0; missing label or generic role downgrades. Document the heuristic in `sgcl/core/`.
- [ ] Wire into the Windows UIA adapter.
- [ ] Linux tests with synthetic inputs.

### E.3 — Walker exception logging + system-surface filter

- [ ] Replace silent `except Exception: pass` around `GetChildren()` with stderr logging (include control id + ControlTypeName).
- [ ] Tag known system windows (`Program Manager`, taskbar / shell windows) with `is_system_surface=True`.
- [ ] `sgcl windows` excludes them by default; `--include-system` opts in.
- [ ] Tests.

### E.4 — Icon-font label handling

- [ ] Small static map of PUA codepoints (Segoe Fluent Icons) → human description; start with the few we see in Notepad/Calculator dumps.
- [ ] Populate `description` when a label is purely PUA glyphs.
- [ ] Tests.

### E.5 — Structural pane reduction

- [ ] Walker post-process: collapse unlabeled single-child `pane` chains. Retain flattened ids in `raw_ref.flattened` for debugging.
- [ ] Tests.

### E.6 — Label synonyms (Calculator-focused, easy to extend)

- [ ] Static map: "Zero"→"0", "Plus"→"+", "Minus"→"−"/"-", "Multiply by"→"*"/"×", "Divide by"→"/"/"÷", "Equals"→"=", etc.
- [ ] Populate `synonyms` on matching buttons.
- [ ] Phase 1 just emits; Phase 2 (Find) consumes.

### E.7 — Windows re-runs + spike report

- [ ] Re-run Notepad and Calculator captures with the normalized output.
- [ ] Compare control counts (raw vs normalized). Should go down.
- [ ] Compare confidence distribution. Should not be uniformly 1.0.
- [ ] Write `spikes/normalize-results.md`: size delta, confidence histogram, role mapping decisions, new questions for Phase 2/9.
- [ ] Close GitHub issue #2 (`[blunt-win] Normalize`) with a link.

## F. Phase 2+ — pointer

Don't start until E is done.

- [`docs/phase-2-find-read-spike.md`](../docs/phase-2-find-read-spike.md) — Find + Read.
- [`docs/phase-3-act-verify-risk-spike.md`](../docs/phase-3-act-verify-risk-spike.md) — Act + Verify + Risk.

## Notes

- **One phase at a time.** Don't pre-implement Phase 2 work inside Phase 0. If a Phase 0 task feels like it needs Phase 2 functionality to be useful, that means Phase 0 scope is wrong, not that you should reach forward.
- **No mocking of real surfaces.** Notepad and Calculator are the real test targets. If they're not available, say so — don't fake the adapter.
- **Vision is Phase 8.** Not earlier. Even if it's tempting when UIA returns garbage.
