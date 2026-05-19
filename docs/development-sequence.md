# Development Sequence

## Phase 0: Spike

Goal: Prove the core automation path.

Build:

- List windows.
- Inspect active window through one platform adapter.
- Print control tree as JSON.
- Normalize controls into basic affordances.
- Invoke a simple button.
- Type into a text field.

Exit criteria:

- Can operate a basic text editor and calculator in a simple way without vision.

## Phase 1: CLI MVP

Goal: Make the prototype usable from a terminal.

Build:

- CLI command structure.
- Stable session IDs for windows and controls.
- JSON output mode.
- `find`, `read`, `focus`, `type`, `invoke`, and `hotkey` commands.
- Basic before/after observation.

Exit criteria:

- A human or LLM can use the CLI to complete the initial text editor and calculator use cases.

## Phase 2: Daemon/API Layer

Goal: Separate the automation runtime from the CLI.

Build:

- Local server or daemon.
- JSON-RPC, REST, or MCP-compatible interface.
- CLI becomes a client.
- Session management.
- Structured error responses.

Exit criteria:

- An agent can call the API repeatedly and maintain context across actions.

## Phase 3: Affordance Graph

Goal: Move from raw trees to normalized affordances.

Build:

- Role normalization.
- Action inference.
- Confidence scoring.
- Parent/child and label/control relationship inference.
- Ambiguity handling.

Exit criteria:

- Agent sees a compact, useful interface model instead of a giant raw UI tree.

## Phase 4: Safety and Verification

Goal: Make action execution trustworthy.

Build:

- Risk classification.
- Precondition handling.
- Action blocking/escalation for committing actions.
- Before/after diffing.
- Verification result model: success, failure, uncertain.

Exit criteria:

- The system can distinguish inspection, reversible interaction, and risky submission/deletion actions.

## Phase 5: Fallbacks

Goal: Handle weak or broken accessibility trees.

Build:

- Screenshot capture.
- OCR integration.
- Bounds-based fallback clicking.
- Keyboard probing.
- Menu probing.
- Escape/undo recovery.

Exit criteria:

- The system can still operate partially when semantic metadata is incomplete.

## Phase 6: Learned App Maps

Goal: Make repeated use better over time.

Build:

- Store known app/window states.
- Store successful control mappings.
- Store dangerous actions.
- Store common transitions.
- Let users or agents annotate controls.

Exit criteria:

- The system improves on repeated use of the same app.
