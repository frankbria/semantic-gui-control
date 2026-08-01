# CLAUDE.md — Semantic GUI Control Layer (SGCL)

This file is project-specific guidance for Claude when working in this repo. It overrides nothing in the user's global instructions; it adds context for *this* project.

## Project state

**Phases 0–2 are shipped on `main`. Phase 3 is planned and not started.**

- **Phase 0 (Observe)** — `sgcl windows` / `active` / `inspect`, structured JSON out of live Windows UIA.
- **Phase 1 (Normalize)** — platform-neutral affordance schema, confidence scoring, icon-glyph descriptions, label synonyms, system-surface filtering.
- **Phase 2 (Find + Read)** — `sgcl find` / `read` with a semantic matcher and pattern-based value extraction.
- **Phase 3 (Act + Verify + Risk)** — not started. Begins with a planning session; see [`docs/handoff-phase-3-planning.md`](docs/handoff-phase-3-planning.md).

The working code lives in `sgcl/` (see the package shape below) with a Linux-runnable test suite in `tests/`. Run `uv run pytest -q` to confirm the current state rather than trusting this paragraph.

Before writing code, read at minimum:

1. [`docs/project-thesis.md`](docs/project-thesis.md) — the thing this project is and is not.
2. [`docs/roadmap-blunt-wins.md`](docs/roadmap-blunt-wins.md) — what we are doing in what order.
3. The phase doc for the phase you are working on (currently `docs/phase-3-act-verify-risk-spike.md`).
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
- **Vision/OCR is Win 8.** Do not introduce it earlier. When it does land, it is an adapter, not a sibling layer.

## Phase discipline

### "Win N" and "Phase N" are different numbering schemes

Read this before acting on any numbered reference. There is **no fixed offset
between them**: Phase 2 fuses wins 3–4, Phase 3 fuses wins 5–7.

- **Win N** — one of the roadmap milestones in [`docs/roadmap-blunt-wins.md`](docs/roadmap-blunt-wins.md).
- **Phase N** — an implementation phase. **Only 0–3 exist.** There is no Phase 4.

So anything numbered above 7 is a *win*, never a phase. Wins 8–11 have no
phase assigned; nobody has made that call, so do not infer one. The mapping
table is in [`README.md`](README.md).

A third scheme exists in [`docs/development-sequence.md`](docs/development-sequence.md),
which is **superseded**. If you cite it, say so explicitly.

Each blunt win must produce **a working capability, a documented constraint, or a killed assumption**. If a change does not produce one of those, it is not a win — name it differently.

Do not pre-implement future phases. Specifically:

- Phase 0 (Observe) is read-only. No clicking, typing, or OCR.
- Phase 1 (Normalize) is design + mapping. No FIND or execution.
- Phase 2 (Find + Read) is still read-only.
- Phase 3 (Act + Verify + Risk) lands execution and safety together. Do not ship Act without Verify and Risk.

If a task feels like it needs functionality from a later phase to be useful, that is a signal that the current phase's scope is wrong, not that you should reach forward.

## Stack expectations

These are working assumptions, not commitments. Update [`docs/open-questions.md`](docs/open-questions.md) when one is settled and write an ADR when one is decided for real.

- **Language for Phase 0 / first adapter:** Python with `uiautomation` for Windows UIA. Decided convenience-first; see [`ADR-0003`](docs/decisions/ADR-0003-python-and-uiautomation-for-the-first-adapter.md).
- **Package manager:** `uv` (per the user's global standard).
- **Tests:** `pytest`, 100% pass. Coverage is **enforced**, not aspirational: `--cov-fail-under=85` in `pyproject.toml`. Currently ~91%. `sgcl/adapters/windows_uia/_adapter.py` is omitted from the measurement because it raises `ImportError` off-Windows and no Linux test can reach it.
- **`pytest-bdd`** is a stated intent, not an installed dependency. Add it when a scenario actually needs BDD, not before.
- **Lint/format:** `ruff` + `black`.
- **Agent integration surface:** the CLI is the reference surface. A stateless MCP server over `Adapter` is the intended programmatic one, not before Phase 3 lands; the stateful daemon is rejected for now. See [`ADR-0006`](docs/decisions/ADR-0006-agent-integration-surface.md).

The package shape as it exists today:

```
sgcl/
  core/                # platform-neutral: schema, matcher, confidence, synonyms,
                       # icon_glyphs, read_result, adapter_base
  adapters/
    windows_uia/       # the only adapter so far
  cli.py               # `sgcl` entry point — windows / active / inspect / find / read
```

`macos_ax`, `linux_atspi`, `browser_dom` and `vision_ocr` remain planned, not present.

## Working in this repo

- **Source control:** GitHub at `https://github.com/frankbria/semantic-gui-control`. Feature branches → PR to `main`. Pre-commit hooks expected once tooling is set up.
- **No mocking of real services.** Integration tests for adapters run against real UI surfaces (Notepad, Calculator, etc.). If the test surface is not available on the dev machine, say so — do not fake the adapter.
- **Spike results live in `spikes/`.** Each Phase has or will have a results file. Fill in surprises, constraints discovered, and assumptions killed honestly — those entries are the actual value of the spike.
- **ADRs live in `docs/decisions/`.** When you decide something irreversible, write one.
- **GitHub issues:** the `[blunt-win]` and `[spike]` issue templates are in `.github/ISSUE_TEMPLATE/`. Seed bodies for the first 7 wins are in [`docs/github-issues-seed.md`](docs/github-issues-seed.md).

## When in doubt

- **Stay inside the current phase.** Phase 3 (Act + Verify + Risk) is the active surface, and it is the last phase defined — there is no Phase 4. Do not pre-implement work beyond it: no vision/OCR (Win 8), no second adapter (Win 9), no agent loop (Win 10), no daemon. If a task seems to need it, the current phase's scope is wrong, not the phase boundary.
- **Smaller wins.** If a planned task feels like more than one blunt win, split it.
- **Refuse confident stupidity.** When a request would silently guess (a coordinate click, a single FIND result chosen from many, a `committing` action without approval, an `uncertain` verification reported as success), push back instead of complying.

## Out of scope (for now)

These are real but deliberately deferred:

- Full RPA-replacement features.
- Visual workflow designer.
- Cross-platform parity from day one. The contract is uniform; capability varies by adapter, honestly.
- Domain-specific verbs ("book a flight"). The vocabulary stays small and boring.
- Stable cross-session control IDs. Within-session is enough for now.
- A learned app-map / memory layer. Phase 6 of the **superseded** [`docs/development-sequence.md`](docs/development-sequence.md), whose numbering is a third scheme and matches neither the wins nor the phases. Not on the blunt-wins critical path.

## Quick reference

| If you need… | Read… |
|--------------|-------|
| What we're doing and why | `docs/project-thesis.md` |
| The roadmap milestones | `docs/roadmap-blunt-wins.md` |
| The shape of the agent-facing data | `docs/affordance-model.md` |
| The verbs an agent can use | `docs/command-vocabulary.md` |
| When to refuse to execute | `docs/risk-model.md` |
| What Phase 0 actually has to do | `docs/phase-0-observe-spike.md` |
| What is still undecided | `docs/open-questions.md` |
| What has been decided | `docs/decisions/` |
| What broke or surprised us | `spikes/` |
