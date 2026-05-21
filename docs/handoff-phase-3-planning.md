# Handoff — Phase 3 Planning (Act + Verify + Risk)

This file is a self-contained prompt for a fresh Claude Code session
that will plan Phase 3 of the SGCL project. Paste the section under
`---` into the new session as the first message. The session needs no
chat history from earlier work — everything important is in the repo.

## How to use this file

1. Open a new Claude Code session with working directory set to this
   repository's root.
2. Copy everything below the horizontal rule.
3. Paste as the first message. The session will read the orientation
   docs, ask any clarifying questions, and produce the Phase 3 plan
   (a refreshed `docs/phase-3-act-verify-risk-spike.md` plus a sliced
   task list in `tasks/todo.md`).

---

You are picking up the **Semantic GUI Control Layer (SGCL)** project at
the start of Phase 3. The project is at `github.com/frankbria/semantic-gui-control`
and you are running in a fresh Claude Code session inside that repo.

## What SGCL is, in one paragraph

A text-first, cross-platform control layer that exposes graphical
interfaces to LLM agents as structured affordances instead of pixels.
Discovers controls from accessibility APIs (Windows UIA today; macOS AX,
Linux AT-SPI, browser DOM later), normalizes them into a platform-
neutral graph, exposes a small standard command vocabulary, executes
via platform adapters, and verifies state changes. Vision/OCR is the
spare tire, not the steering wheel.

## What's already shipped

Phases 0, 1, and 2 are done. Read these in order to get up to speed:

1. **`README.md`** — one-page overview.
2. **`docs/project-thesis.md`** — problem, thesis, non-goals, principles.
3. **`docs/roadmap-blunt-wins.md`** — the 10 coarse milestones and the
   "working capability / documented constraint / killed assumption"
   rule each must produce.
4. **`docs/architecture-overview.md`** — conceptual pipeline, core vs
   adapters discipline.
5. **`docs/affordance-model.md`** — the normalized schema.
6. **`docs/command-vocabulary.md`** — the verbs (observe / find / read
   already shipped; focus / type / invoke / select / scroll / wait /
   verify / escape / undo are Phase 3+).
7. **`docs/risk-model.md`** — risk classes and default policy. Phase 3
   makes this live.
8. **`spikes/windows-observer-results.md`** — Phase 0 spike report.
9. **`spikes/normalize-results.md`** — Phase 1 spike report.
10. **`spikes/find-read-results.md`** — Phase 2 spike report.
11. **`docs/open-questions.md`** — questions the prior phases surfaced.
    Eleven of these directly inform Phase 3 design.
12. **`docs/phase-3-act-verify-risk-spike.md`** — the existing
    placeholder/draft for Phase 3. You will rewrite this as part of
    planning, similar to how Phase 1 and Phase 2 plans were refreshed
    when their predecessors closed.
13. **`CLAUDE.md`** — project memory and principles.

## What's in main as of this handoff

```
sgcl/
  cli.py                          # sgcl windows / active / inspect / find / read
  core/
    adapter_base.py               # Adapter ABC, ReadResolution
    affordance schema, matcher, confidence, icon_glyphs, synonyms,
    read_result
  adapters/
    windows_uia/
      __init__.py                 # platform-gated re-export
      _adapter.py                 # WindowsUIAAdapter (imports uiautomation)
      _walker.py                  # duck-typed, Linux-testable
      _readers.py                 # duck-typed, Linux-testable
      _system.py                  # shell-window heuristic
tests/                            # 203 Linux-runnable tests, all green
docs/                             # phase docs, ADRs, open questions, handoffs
spikes/samples/                   # captured JSON from real Windows runs
```

Phase 0/1/2 closed against GitHub issues #1/#2/#3/#4. Issues #5
(Act), #6 (Verify), and #7 (Risk) are open and remain open through
Phase 3.

## What Phase 3 is

Phase 3 is the **first phase that changes the world being controlled.**
Prior phases were sense-only. Phase 3 introduces:

- **Act**: focus, type, invoke, select, scroll. Real input synthesized
  into the target application via UIA patterns first, keyboard
  synthesis second, coordinate fallback last.
- **Verify**: every action returns a `verification` payload with
  `before`, `after`, `diff`, `status` (success / failure / uncertain).
  `uncertain` is first-class and is not a synonym for success.
- **Risk**: every executable affordance carries a risk class
  (`safe` / `reversible` / `committing` / `unknown`).
  `committing` and `unknown` are refused by default; require explicit
  `--approve` (or equivalent policy override).

These three land **together**, not separately. Shipping Act without
Verify and Risk violates the project's thesis. The blunt-wins roadmap
treats them as three wins but the implementation phase fuses them.

## Operating mode (read this carefully before doing anything)

This project has been worked on in tight slices with a specific
discipline. Honor it.

1. **Plan first.** Use plan mode. Produce a refreshed
   `docs/phase-3-act-verify-risk-spike.md` and a sliced task list in
   `tasks/todo.md` before writing any code. Get the user's signoff
   via `ExitPlanMode` before implementing.

2. **DO NOT spawn Explore or Plan subagents to survey code that was
   shipped on `main`.** The earlier session learned this the hard way:
   plan-mode Explore agents can use `Bash` to write files. An overscoped
   prompt led to ~1,950 lines of unreviewed code being created during
   what was supposed to be exploration. You can `Read` and `Grep`
   yourself; the codebase is small. If you do launch a subagent, set
   explicit guardrails: "Read and Grep only. Do not run Bash. Do not
   modify the filesystem. Do not create tasks."

3. **Slice the work like Phases 1 and 2 did.** See `tasks/todo.md`
   for the E.1–E.7 (Phase 1) and F.0–F.7 (Phase 2) examples. Each
   slice ends in tests + commit + push. Phase 3 will probably have
   8–10 slices; the larger scope (three blunt wins) earns the
   extra count.

4. **Linux dev / Windows test.** The pattern from Phases 1 and 2:
   you ship code from this Linux session; a separate Windows-side
   Claude session runs the live spike against Notepad and Calculator
   via `docs/windows-handoff-prompt-phase-2.md` (template — write a
   `windows-handoff-prompt-phase-3.md` for Phase 3's spike). Do not
   try to drive a remote Windows machine from this session; there is
   no channel.

5. **Tests must stay green and growing.** The current count is 203.
   Lint with `uv run ruff check . && uv run black --check .` after
   every edit. Tests run via `uv run pytest -q`.

6. **No state changes to the working world during planning.** Phase 3
   is risky — typing or invoking real controls can have consequences
   on the user's actual desktop. The Windows-side spike runs against
   Notepad and Calculator only, and the prompt template should bias
   the Windows session toward disposable test data (scratch files,
   not the user's real documents).

## The 11 design questions you must address

These came out of Phases 1 and 2 and are documented in
`docs/open-questions.md`. Phase 3 either resolves each or explicitly
defers it. Don't ignore any.

**From `## FIND ergonomics`:**

1. Should `--label` also check synonyms? Phase 2 confirmed
   `--label "="` returns 0 matches against Calculator's Equals button.
2. Should there be an `--automation-id` selector for stable hooks
   like Calculator's `CalculatorResults`?
3. Should `--max-length` cap `ValuePattern` as well as `TextPattern`?
4. Notepad's editor is `document`, not `text_field`. Should we
   document a role-mapping guide or alias one to the other?
5. `TogglePattern` and `SelectionPattern` reader paths are untested
   against real controls. Phase 3 must exercise them.
6. Risk classification for READ — should be `risk: safe`, but isn't
   written down yet.

**From `## FIND match-result enrichment`:**

7. `dialog_title` derived field on each MatchResult.
8. `nearby_text` derived field for unlabeled controls.
9. Tree-distance decay on `--near`.

**From `## Targeting`:**

10. System/shell window filtering policy — currently
    `is_system_surface=True` hides from `sgcl windows` by default.
    Confirm this stays correct when actions get involved.

**From elsewhere (`docs/open-questions.md`):**

11. Daemon state — should Phase 3 still be stateless, or does
    verification need before/after snapshot caching? If snapshots
    get cached, that's the first piece of session state in the
    project. Decide deliberately.

## Concrete deliverables for Phase 3 planning

The fresh session's job is to produce:

1. **A refreshed `docs/phase-3-act-verify-risk-spike.md`** that:
   - Replaces the existing draft (currently a Phase-1-era sketch).
   - Lists what's known from Phases 0/1/2 as background, not
     assumptions.
   - Slices Phase 3 into independently mergeable chunks (suggest 8–10
     slices, but propose whatever shape fits).
   - Names each slice's deliverable, tests, and how it stays Linux-
     testable.
   - Explicitly addresses each of the 11 questions above (resolve or
     defer with reason).
   - Includes a Windows-side spike plan (the "F.7 of Phase 3").
   - Names the risks to watch (the biggest is: irreversible actions
     against the user's real desktop).

2. **A `docs/windows-handoff-prompt-phase-3.md`** modeled on
   `docs/windows-handoff-prompt-phase-2.md` but adapted for Phase 3's
   spike commands. The Windows-side session will use Notepad and
   Calculator with scratch data only, and exercise the risk-refusal
   path explicitly.

3. **A sliced task list in `tasks/todo.md`** following the cadence
   from Phase 1 (E.0–E.7) and Phase 2 (F.0–F.7). Phase 3's prefix is
   open — pick something memorable.

4. **An updated CLAUDE.md** if you discover something new about how
   this project should be worked on.

## Key design constraints (non-negotiable)

These come from the project thesis and prior decisions. If your plan
violates them, reconsider the plan.

- **Patterns first, keyboard second, coordinates last.** UIA's
  `InvokePattern.Invoke()` and `ValuePattern.SetValue()` are the
  primary mechanisms. Keyboard synthesis (Ctrl+S, etc.) is the
  fallback. Coordinate clicks are last-resort and must reference
  `bounds` from the affordance, not be guessed.
- **Every action returns evidence.** Even `uncertain` is structured —
  the agent gets a verification block, never bare success/failure.
- **Committing actions refuse by default.** No "I'll just do it" on
  Submit / Send / Delete / Purchase / Finalize / Pay / Transfer /
  Overwrite / Confirm.
- **Idempotent if possible.** Repeating a typed value should not
  re-type unless the value differs.
- **Per-invocation control IDs are still the model.** No persistent
  session state was added in Phase 2; if Phase 3 needs it for
  verification snapshots, write an ADR.
- **No second adapter in Phase 3.** Phase 9 is where cross-platform
  parity gets proven. Don't pre-build for it.

## Recommended reading order for a fresh session

About 25–30 minutes of careful reading before you start planning:

1. `README.md` (2 min)
2. `docs/project-thesis.md` (3 min)
3. `docs/roadmap-blunt-wins.md` (3 min)
4. `docs/risk-model.md` (5 min — Phase 3 makes this live)
5. `docs/command-vocabulary.md` (5 min — Phase 3 implements verbs)
6. `docs/architecture-overview.md` (3 min)
7. `spikes/find-read-results.md` (5 min — most recent context)
8. `docs/open-questions.md` (5 min — the 11 questions)
9. `docs/phase-3-act-verify-risk-spike.md` (2 min — what to replace)
10. `CLAUDE.md` (2 min)

Skim the Phase 0 and 1 spike reports if helpful, but Phase 2's covers
the most current state of the codebase.

## Once you're ready

Enter plan mode (`EnterPlanMode`). Do **not** spawn Explore subagents
to re-survey the code — read directly with `Read` and `Grep`. The
codebase is small (about 2,500 lines of code + tests). Write the plan
file directly. When done, `ExitPlanMode` and wait for the user's
signoff. Then start implementation slice by slice.

Good luck. The thesis holds so far; Phase 3 is where the project earns
its name.
