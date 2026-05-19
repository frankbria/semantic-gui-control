# CLAUDE.md — Semantic GUI Control Layer (SGCL)

This file is project-specific guidance for Claude when working in this repo. It overrides nothing in the user's global instructions; it adds context for *this* project.

## Project state

**Discovery / spike phase. No production code yet.** The repo currently contains only planning and design documents. Phase 0 (Observe) has not been implemented.

Before writing code, read at minimum:

1. [`docs/project-thesis.md`](docs/project-thesis.md) — the thing this project is and is not.
2. [`docs/roadmap-blunt-wins.md`](docs/roadmap-blunt-wins.md) — what we are doing in what order.
3. The phase doc for the phase you are working on (e.g., `docs/phase-0-observe-spike.md`).
4. [`docs/affordance-model.md`](docs/affordance-model.md) and [`docs/command-vocabulary.md`](docs/command-vocabulary.md) — the public contract.
5. [`docs/decisions/`](docs/decisions/) — ADRs.

## Core thesis (one paragraph)

Agents should not primarily operate GUIs through screenshots and coordinate clicks. SGCL discovers the usable interface from the environment (accessibility trees, DOM, OS automation APIs, keyboard traversal, app APIs), normalizes it into structured affordances, exposes a small standard command vocabulary, executes through platform adapters, verifies state changes, and uses vision/OCR only as fallback.

> Vision is the spare tire, not the steering wheel.

## Principles to enforce when writing code or docs

These are the things to push back on if a request would violate them:

- **Cross-platform core.** Anything in `sgcl/core/` is platform-neutral. No `UIA`, `AX`, `AT-SPI`, `DOM` in user-facing type names. Platform specifics belong in `sgcl/adapters/<name>/`. See [`ADR-0001`](docs/decisions/ADR-0001-cross-platform-core-windows-first-spike.md).
- **Adapters import from core; core never imports from adapters.** Adapter modules do not import each other.
- **Structured output, not prose.** Agents consume JSON. CLI defaults to JSON; pretty output is a flag.
- **Evidence over assertion.** Every action returns a `verification` payload with `before` / `after` / `diff` / `status`. `uncertain` is first-class and is not a synonym for `success`.
- **Risk is first-class.** Every executable affordance has a `risk` class. `committing` and `unknown` actions are refused without explicit approval. The risky-verbs list in [`docs/risk-model.md`](docs/risk-model.md) is authoritative.
- **Ambiguity is explicit.** FIND returns multiple candidates with context, not one silent guess.
- **Raw is available but not primary.** Adapter-specific data lives on `raw_ref`. The normalized model is what the agent reasons over.
- **Coordinates are a fallback.** They live in `bounds`. They do not appear in command verbs.
- **Vision/OCR is Phase 8.** Do not introduce it earlier. When it does land, it is an adapter, not a sibling layer.

## Phase discipline

Each blunt win must produce **a working capability, a documented constraint, or a killed assumption**. If a change does not produce one of those, it is not a win — name it differently.

Do not pre-implement future phases. Specifically:

- Phase 0 (Observe) is read-only. No clicking, typing, or OCR.
- Phase 1 (Normalize) is design + mapping. No FIND or execution.
- Phase 2 (Find + Read) is still read-only.
- Phase 3 (Act + Verify + Risk) lands execution and safety together. Do not ship Act without Verify and Risk.

If a task feels like it needs functionality from a later phase to be useful, that is a signal that the current phase's scope is wrong, not that you should reach forward.

## Stack expectations

These are working assumptions, not commitments. Update [`docs/open-questions.md`](docs/open-questions.md) when one is settled and write an ADR when one is decided for real.

- **Language for Phase 0 / first adapter:** Python (likely with `pywinauto` or `uiautomation` for Windows UIA). Decision is convenience-first and documented in the Phase 0 spike.
- **Package manager:** `uv` (per the user's global standard).
- **Tests:** `pytest` + `pytest-bdd` once code exists. >85% coverage, 100% pass.
- **Lint/format:** `ruff` + `black`.
- **Protocol for an eventual daemon:** undecided. See open questions.

When code exists, the proposed package shape is:

```
sgcl/
  core/        # platform-neutral schemas, vocabulary, find, verify, risk
  adapters/    # windows_uia, macos_ax, linux_atspi, browser_dom, vision_ocr
  cli.py       # `sgcl` entry point
```

## Working in this repo

- **Source control:** GitHub at `https://github.com/frankbria/semantic-gui-control`. Feature branches → PR to `main`. Pre-commit hooks expected once tooling is set up.
- **No mocking of real services.** Integration tests for adapters run against real UI surfaces (Notepad, Calculator, etc.). If the test surface is not available on the dev machine, say so — do not fake the adapter.
- **Spike results live in `spikes/`.** Each Phase has or will have a results file. Fill in surprises, constraints discovered, and assumptions killed honestly — those entries are the actual value of the spike.
- **ADRs live in `docs/decisions/`.** When you decide something irreversible, write one.
- **GitHub issues:** the `[blunt-win]` and `[spike]` issue templates are in `.github/ISSUE_TEMPLATE/`. Seed bodies for the first 7 wins are in [`docs/github-issues-seed.md`](docs/github-issues-seed.md).

## When in doubt

- **Documents over implementation.** Until Phase 0 is started, doc edits are the right surface to push on. Do not stub code "to make it real" — the proposed package shape is documented and that is enough.
- **Smaller wins.** If a planned task feels like more than one blunt win, split it.
- **Refuse confident stupidity.** When a request would silently guess (a coordinate click, a single FIND result chosen from many, a `committing` action without approval, an `uncertain` verification reported as success), push back instead of complying.

## Out of scope (for now)

These are real but deliberately deferred:

- Full RPA-replacement features.
- Visual workflow designer.
- Cross-platform parity from day one. The contract is uniform; capability varies by adapter, honestly.
- Domain-specific verbs ("book a flight"). The vocabulary stays small and boring.
- Stable cross-session control IDs. Within-session is enough for now.
- A learned app-map / memory layer. That's Phase 6+ territory in the legacy sequence and is not on the blunt-wins critical path yet.

## Quick reference

| If you need… | Read… |
|--------------|-------|
| What we're doing and why | `docs/project-thesis.md` |
| The 10 milestones | `docs/roadmap-blunt-wins.md` |
| The shape of the agent-facing data | `docs/affordance-model.md` |
| The verbs an agent can use | `docs/command-vocabulary.md` |
| When to refuse to execute | `docs/risk-model.md` |
| What Phase 0 actually has to do | `docs/phase-0-observe-spike.md` |
| What is still undecided | `docs/open-questions.md` |
| What has been decided | `docs/decisions/` |
| What broke or surprised us | `spikes/` |
