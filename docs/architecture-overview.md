# Architecture Overview

## Conceptual pipeline

```
Environment Sources
        │
        ▼
Perception Adapters         (platform-specific; e.g., windows_uia)
        │
        ▼
Affordance Discovery        (walk trees, infer actions, label associations)
        │
        ▼
Normalized Interface Graph  (platform-neutral JSON; see affordance-model.md)
        │
        ▼
Command Vocabulary          (OBSERVE / FIND / READ / FOCUS / TYPE / ...)
        │
        ▼
Execution Engine            (dispatches commands back through adapters)
        │
        ▼
Verification and Repair     (diff observations; fall back; report evidence)
```

The pipeline is bidirectional in practice: execution flows down, observation flows up, and verification compares the two.

## Core vs adapters

**Core** is platform-neutral. It contains:

- Schemas: affordance model, command request/response shapes, verification result shape.
- Vocabulary: the small standard command set.
- Policies: risk classes, default risk policy.
- Engines: discovery walker, find/match, verifier, repair orchestrator.

The core must not import anything platform-specific. It must not contain the words `UIA`, `AX`, `AT-SPI`, or `DOM` in any user-facing type name.

**Adapters** are platform-specific. Each adapter:

- Knows how to enumerate windows and walk a native UI tree.
- Maps native control roles into the normalized role vocabulary.
- Maps normalized actions back to native execution paths.
- Reports its own capabilities honestly (some actions, like reading certain values, may not be supported).
- May expose adapter-specific metadata on `raw_ref` for debugging, but must not require the core to use it.

If a future adapter needs a concept the core does not have, that is a signal to evaluate whether the concept belongs in the core. Adapters do not get to mutate the core schema on the fly.

## Candidate adapters

| Adapter | Platform | Primary mechanism |
|---------|----------|-------------------|
| `windows_uia` | Windows | Microsoft UI Automation (UIA) |
| `macos_ax` | macOS | Accessibility API / AXUIElement |
| `linux_atspi` | Linux desktop | AT-SPI accessibility bus |
| `browser_dom` | Web browser | DOM via Playwright / CDP |
| `vision_ocr` | Any | Screenshot + OCR + coordinate execution; fallback only |

Adapters can be combined. For example, a Windows session might primarily use `windows_uia` but fall back to `vision_ocr` when a specific control's accessibility properties are missing.

## First proposed package shape

```
sgcl/
  core/
    affordance.py      # normalized affordance schema
    vocabulary.py      # command definitions and dispatch
    find.py            # semantic search over the affordance graph
    verify.py          # before/after diffing + verification status
    risk.py            # risk classes and default policy
    adapter_base.py    # abstract Adapter interface
  adapters/
    windows_uia/       # first spike target
    macos_ax/          # placeholder
    linux_atspi/       # placeholder
    browser_dom/       # placeholder
    vision_ocr/        # placeholder; repair fallback
  cli.py               # `sgcl` entry point
```

No code is implemented yet. The directory shape is documented here so Phase 0 has a target to commit into.

## Boundary discipline

The core defines the contract. Adapters implement it. The CLI consumes the core. Agents consume the CLI (or, later, a daemon API).

Hard rules:

- Adapter modules never import from each other.
- Adapter modules import from `core/` but `core/` never imports from `adapters/`.
- The CLI dispatches by adapter name; it does not branch on platform inside command handlers.
- Vision/OCR is registered as an adapter, not as a sibling layer to the affordance graph. Pixels go through the same contract as everything else.
