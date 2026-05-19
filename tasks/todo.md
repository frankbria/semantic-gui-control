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

- [ ] Decide UIA library for the spike (`pywinauto`, `uiautomation`, or COM directly). Capture the choice + reasoning in `spikes/windows-observer-results.md` under "Environment".
- [ ] Confirm a Windows dev environment is available (local VM, dual boot, or remote).
- [ ] Initialize Python project: `uv venv`, `pyproject.toml`, `ruff` + `black` config.
- [ ] Create the empty package skeleton matching `docs/architecture-overview.md`:
  - [ ] `sgcl/core/` (empty)
  - [ ] `sgcl/adapters/windows_uia/` (empty)
  - [ ] `sgcl/cli.py` (stub `main()` only)
- [ ] Set up pre-commit hooks (template at `/home/frankbria/projects/templates`).

## C. Phase 0 — Observe

Authoritative checklist: [`docs/phase-0-observe-spike.md`](../docs/phase-0-observe-spike.md). Summary:

- [ ] Implement `sgcl windows` (list with title, process, pid, bounds, visible, active).
- [ ] Implement `sgcl active` (foreground window).
- [ ] Implement `sgcl inspect --active --depth N` (hierarchical control tree JSON).
- [ ] Verify JSON output for each command is parseable and conforms to the spike schema.
- [ ] Test against **Notepad** end-to-end.
- [ ] Test against **Calculator** end-to-end.
- [ ] Fill in `spikes/windows-observer-results.md` (every section, even the awkward ones — surprises and assumptions killed are the point).
- [ ] Add any new unknowns to `docs/open-questions.md`.

## D. Phase 0 wrap-up — decide before Phase 1

- [ ] Review the spike note: did Phase 0 produce a working capability, a documented constraint, or a killed assumption? (Required to count as a blunt win.)
- [ ] If any Phase 1 assumption in `docs/phase-1-normalize-spike.md` was contradicted, update that doc before starting Phase 1.
- [ ] Close the `[blunt-win] Observe` GitHub issue with a link to the spike note.
- [ ] Open the `[blunt-win] Normalize` issue if it isn't already, and confirm scope is still right.

## E. Phase 1+ — pointer

Don't start until D is done. Authoritative checklists:

- [`docs/phase-1-normalize-spike.md`](../docs/phase-1-normalize-spike.md) — Normalize.
- [`docs/phase-2-find-read-spike.md`](../docs/phase-2-find-read-spike.md) — Find + Read.
- [`docs/phase-3-act-verify-risk-spike.md`](../docs/phase-3-act-verify-risk-spike.md) — Act + Verify + Risk.

## Notes

- **One phase at a time.** Don't pre-implement Phase 2 work inside Phase 0. If a Phase 0 task feels like it needs Phase 2 functionality to be useful, that means Phase 0 scope is wrong, not that you should reach forward.
- **No mocking of real surfaces.** Notepad and Calculator are the real test targets. If they're not available, say so — don't fake the adapter.
- **Vision is Phase 8.** Not earlier. Even if it's tempting when UIA returns garbage.
