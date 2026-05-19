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

**Discovery / spike phase.** No production code yet. Planning and architecture only.

The first executable milestone (Phase 0) targets a Windows UIA observer that can list windows and dump an active window's control tree as JSON. Windows is a convenient first spike; the core model is intentionally cross-platform.

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

Nothing to run yet. The proposed package shape is:

```
sgcl/
  core/        # platform-neutral schemas, vocabulary, verifier, risk
  adapters/    # windows_uia, macos_ax, linux_atspi, browser_dom, vision_ocr
  cli.py       # `sgcl` entry point
```

The first spike (Phase 0) will likely use Python with `pywinauto` or `uiautomation` on Windows. Setup steps will be documented once they exist.

## Working metaphor

A terminal for the visual operating environment. Not because everything becomes text, but because the GUI becomes inspectable, commandable, and verifiable.
