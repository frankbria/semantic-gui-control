# Semantic GUI Control Layer (SGCL)

A text-first, cross-platform control layer for agentic interaction with graphical user interfaces.

## Thesis

Agents should not primarily operate GUIs through screenshots and coordinate clicks. SGCL should:

1. **Discover** the usable interface layer from the environment (accessibility trees, DOM, OS automation APIs, keyboard traversal, app APIs).
2. **Normalize** it into structured affordances.
3. **Expose** a small standard command vocabulary.
4. **Execute** actions through platform adapters.
5. **Verify** state changes.
6. **Fall back** to vision/OCR only when semantic paths are broken or incomplete.

> Vision is the spare tire, not the steering wheel.

## Current status

**Phases 0–2 are shipped. Phase 3 (Act + Verify + Risk) is planned and not started.**

| Phase | Capability | State |
|-------|------------|-------|
| 0 — Observe | `sgcl windows` / `active` / `inspect` — live windows and control trees as structured JSON | shipped |
| 1 — Normalize | Platform-neutral affordance schema, confidence scoring, icon-glyph descriptions, label synonyms | shipped |
| 2 — Find + Read | `sgcl find` / `read` — semantic matching and value extraction | shipped |
| 3 — Act + Verify + Risk | Execution with evidence and risk refusal | not started |

Today the only adapter is Windows UIA, so the CLI requires Windows at runtime. The core model and the whole test suite are platform-neutral and run anywhere — see [Local development](#local-development).

## Blunt-win roadmap

Coarse learning milestones. Each one must produce a working capability, a documented constraint, or a killed assumption. See [`docs/roadmap-blunt-wins.md`](docs/roadmap-blunt-wins.md) for detail.

| # | Win | Question it answers |
|---|-----|---------------------|
| 1 | Observe | Can we expose a real desktop GUI as structured text without screenshots? |
| 2 | Normalize | Can we hide UIA/AX/AT-SPI/DOM differences behind a common schema? |
| 3 | Find | Can an agent find the thing it means without knowing screen coordinates? |
| 4 | Read | Can the system read enough state to support agent reasoning and verification? |
| 5 | Act | Can we perform basic actions through the affordance layer rather than pixels? |
| 6 | Verify | Can every action return evidence, not just "I clicked it"? |
| 7 | Risk | Can the system avoid becoming a blind automation monkey on committing actions? |
| 8 | Repair & Fallback | Can the system recover from broken accessibility trees? |
| 9 | Cross-Platform Adapter Contract | Did we build a real abstraction, or just rename Windows UIA? |
| 10 | Agent Loop | Can an LLM use SGCL to complete a tiny task through structured state only? |

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/project-thesis.md`](docs/project-thesis.md) | Problem, thesis, non-goals, guiding principles |
| [`docs/roadmap-blunt-wins.md`](docs/roadmap-blunt-wins.md) | The 10 blunt wins, with exit criteria |
| [`docs/architecture-overview.md`](docs/architecture-overview.md) | Conceptual architecture and adapter model |
| [`docs/command-vocabulary.md`](docs/command-vocabulary.md) | Standard agent-facing commands |
| [`docs/affordance-model.md`](docs/affordance-model.md) | Normalized affordance schema |
| [`docs/risk-model.md`](docs/risk-model.md) | Risk classes and default policy |
| [`docs/use-cases.md`](docs/use-cases.md) | Initial target use cases |
| [`docs/phase-0-observe-spike.md`](docs/phase-0-observe-spike.md) | Detailed plan for the first spike |
| [`docs/phase-1-normalize-spike.md`](docs/phase-1-normalize-spike.md) | Normalize planning |
| [`docs/phase-2-find-read-spike.md`](docs/phase-2-find-read-spike.md) | Find + Read planning |
| [`docs/phase-3-act-verify-risk-spike.md`](docs/phase-3-act-verify-risk-spike.md) | Act + Verify + Risk planning |
| [`docs/open-questions.md`](docs/open-questions.md) | Unresolved questions |
| [`docs/decisions/`](docs/decisions/) | Architecture Decision Records |
| [`docs/github-issues-seed.md`](docs/github-issues-seed.md) | Copy-paste GitHub issue bodies for the first 7 wins |
| [`spikes/`](spikes/) | Results of each exploratory spike |

Legacy reference docs (kept for context, superseded by the above):

- [`docs/level-1-spec.md`](docs/level-1-spec.md) — early system spec
- [`docs/cross-platform-strategy.md`](docs/cross-platform-strategy.md) — adapter strategy notes
- [`docs/development-sequence.md`](docs/development-sequence.md) — earlier phase sequence

## Local development

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
./scripts/verify.sh    # sync, lint, format-check, test — the one command that matters
```

That is the same set of checks [CI](.github/workflows/ci.yml) runs. To run them piecemeal:

```bash
uv sync --extra dev
uv run pytest -q                               # test suite — runs on any platform
uv run ruff check . && uv run black --check .  # lint + format check
```

Optional, recommended — install the git hooks (lint/format at commit, tests at push):

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

The core and the tests are platform-neutral. The CLI needs Windows at runtime, because the UIA adapter is platform-gated — on anything else `sgcl` exits with a message rather than pretending:

```bash
uv run sgcl windows                  # Windows only; use a native shell, not WSL
uv run sgcl inspect --process notepad --depth 3
uv run sgcl find --process calc --text "=" --role button
uv run sgcl read --process calc --target ctrl_42
```

Package shape as it exists today:

```
sgcl/
  core/                # platform-neutral: schema, matcher, confidence, synonyms,
                       # icon_glyphs, read_result, adapter_base
  adapters/
    windows_uia/       # the only adapter so far
  cli.py               # `sgcl` entry point
```

`macos_ax`, `linux_atspi`, `browser_dom` and `vision_ocr` are planned, not present.

## Recommended invocation on Windows

Always use `sgcl --output PATH ...` instead of `> file.json`, `| Out-File`, or `| Tee-Object file.json`. Phase 1 confirmed that PowerShell's default `[Console]::OutputEncoding` mangles non-ASCII bytes when sgcl's UTF-8 stdout flows through the pipe; `--output` writes the file directly from Python in UTF-8 and avoids the round-trip.

Piped redirection produces correct UTF-8 *only* when `[Console]::OutputEncoding` is already UTF-8 in the session — that assumption was tested and killed in Phase 1 (see `spikes/normalize-results.md`), and the resulting corruption is silent in the JSON. See `docs/windows-claude-setup.md` for the optional one-time PowerShell profile additions that also fix interactive command output.

## Working metaphor

A terminal for the visual operating environment. Not because everything becomes text, but because the GUI becomes inspectable, commandable, and verifiable.
