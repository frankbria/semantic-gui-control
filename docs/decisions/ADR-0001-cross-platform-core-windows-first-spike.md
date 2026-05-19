# ADR 0001: Cross-Platform Core, Windows-First Spike

## Status

Accepted (initial planning pass). Revisit at the end of Phase 9 (Cross-Platform Adapter Contract).

## Context

SGCL aims to be a text-first control layer for graphical environments. Several questions affect the first executable steps:

- Should we begin with Windows because UIA is mature and most legacy business software runs on Windows?
- Should we begin with Linux because the project author runs Linux and iteration is faster?
- Should we begin with browser DOM because it is the richest accessibility surface?
- Should the core attempt to be cross-platform from day one, or should we first build "the Windows version" and abstract later?

The relevant prior art:

- Windows UI Automation (UIA) is mature and has accessible API surfaces from Python (`pywinauto`, `uiautomation`), .NET, and COM directly.
- macOS Accessibility (AX) is mature but requires user-granted accessibility permissions and is awkward outside Swift/ObjC.
- Linux AT-SPI is mature in concept but uneven in practice across desktop environments and especially under Wayland.
- Browser DOM via Playwright/CDP is the richest source available, but it is its own world.

The risk of "build Windows first, abstract later" is that the abstraction never happens and the project becomes Windows-only by accident.

## Decision

1. **The core model is cross-platform.** Schemas (`affordance-model.md`), command vocabulary (`command-vocabulary.md`), risk classes (`risk-model.md`), and engine logic are platform-neutral. The core does not import platform-specific code and does not use platform-specific terminology in user-facing types.

2. **The first practical spike targets Windows via UI Automation.** This is a convenience choice (mature API, simple test apps like Notepad and Calculator), not a long-term commitment. Phase 0's deliverable lives inside an adapter, not inside the core.

3. **Platform details remain inside adapters.** Adapters may carry adapter-specific data on `raw_ref`, but the agent-facing schema never gains adapter-specific fields. Adapter modules import from `core/`; `core/` never imports from `adapters/`.

4. **Phase 9 is the proof.** "Cross-platform" is not validated until at least one second adapter (Linux AT-SPI, macOS AX, or browser DOM) produces the same normalized model and passes the same contract tests.

## Consequences

**Positive.**

- The first executable step is reachable quickly (Windows UIA + Notepad/Calculator).
- The agent-facing vocabulary is stable across platforms by construction.
- Adapter quirks stay contained.
- A future browser-DOM adapter is a natural fit, not a separate product.

**Negative.**

- The first implementation requires more discipline than "just call UIA from anywhere." The temptation to leak `ControlType` into the core will be real.
- Some platform-native capabilities (e.g., AppleScript-driven Office automation) will feel awkward to model generically.
- The normalized schema will need iteration once the second adapter exists. Plan for that.

**Neutral.**

- The choice of language for the core (currently presumed Python) is independent of this decision. Adapters can be subprocess sidecars in another language if needed.

## Guiding rule

If a concept cannot plausibly exist across Windows UIA, macOS AX, Linux AT-SPI, and browser DOM, it does not belong in the core command vocabulary or the agent-facing affordance schema. It may still live as adapter-specific metadata on `raw_ref`.

## Revisit triggers

Revisit this ADR if any of the following happens:

- Phase 9 (Cross-Platform Adapter Contract) cannot make a second adapter pass the contract tests without changing the schema in a way that breaks the Windows adapter.
- Two adapters disagree on a core verb's semantics in a way that cannot be reconciled by adapter-level translation.
- The "platform-neutral" core acquires its third UIA-shaped field. That is a sign we are renaming Windows, not abstracting it.
- An agent built on top of SGCL works on Windows and fails predictably on the second platform in a way that is not the adapter's fault but the schema's.
