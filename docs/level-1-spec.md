# Semantic GUI Control Layer: Level 1 Specs

## 1. Core Thesis

Modern LLM agents should not primarily operate graphical interfaces through screenshots, mouse coordinates, and visual guessing. They need a text-first control layer that discovers what is usable in a GUI, represents it as structured affordances, executes standardized actions, and verifies whether the result matched the intent.

The goal is not to replace the GUI. The goal is to expose the GUI as a commandable, inspectable environment.

## 2. Problem Statement

Agents can reason in text, but most desktop software exposes work through graphical interfaces. Current approaches tend to rely on brittle coordinate clicking, screenshots, OCR, or app-specific scripts. These methods are slow, unreliable, difficult to generalize, and hard to verify.

A generic GUI interaction layer should allow an agent to ask:

- What windows exist?
- What controls are available?
- What actions can be safely performed?
- What changed after an action?
- What should I do if the semantic action fails?

## 3. Product Goal

Build a cross-platform daemon and CLI that exposes GUI environments as structured, text-accessible interfaces for agents.

The system should discover windows and controls using available sources such as accessibility APIs, window manager metadata, keyboard focus behavior, OCR, screenshots, and eventually app-specific APIs. It should normalize these into a standard command vocabulary.

## 4. Non-Goals for the First Version

The first version should not attempt to:

- Automate every app perfectly.
- Replace full RPA tools like UiPath or Power Automate Desktop.
- Build a visual workflow designer.
- Solve computer vision as the primary interface layer.
- Automate high-risk actions without explicit safety gates.
- Provide domain-specific automation like “book a flight” or “submit an insurance claim” as native commands.

## 5. Conceptual Architecture

```text
Environment Sources
  - Accessibility APIs: Windows UIA, macOS AX, Linux AT-SPI
  - Window manager metadata
  - Keyboard focus traversal
  - OCR/screenshot fallback
  - Clipboard
  - Browser DOM / app APIs later
        ↓
Perception Adapters
        ↓
Affordance Discovery
        ↓
Normalized Interface Graph
        ↓
Standard Command Vocabulary
        ↓
Execution Engine
        ↓
Verification and Repair Loop
```

## 6. First-Level System Modules

### Observer

Discovers the current GUI environment.

Responsibilities:

- List open windows.
- Identify the active/focused window.
- Inspect a selected window.
- Extract controls from the best available accessibility tree.
- Capture role, label, enabled/disabled state, visibility, bounds, and parent/child relationships.
- Optionally capture screenshot metadata for fallback use.

### Affordance Mapper

Converts raw UI elements into normalized affordances.

Responsibilities:

- Convert platform-specific control types into standard roles.
- Infer possible actions for each element.
- Assign confidence scores.
- Identify likely labels, nearby text, and form relationships.
- Distinguish readable, editable, selectable, navigable, and invokable elements.

### Command Vocabulary

Defines the standard language agents can use.

Minimum viable commands:

```text
OBSERVE
FIND
READ
FOCUS
TYPE
INVOKE
SELECT
SCROLL
WAIT
VERIFY
ESCAPE
UNDO
```

### Executor

Performs actions against GUI elements using the best available backend.

Execution priority:

1. Native accessibility action.
2. Keyboard shortcut or focus-based action.
3. Clipboard-assisted text entry.
4. Coordinate action based on known bounds.
5. Vision/OCR fallback.

### Verifier

Checks whether an action produced the intended result.

Responsibilities:

- Compare pre-action and post-action state.
- Detect window changes, dialog openings, field updates, enabled/disabled changes, and visible text changes.
- Report success, failure, or uncertainty.

### Safety and Risk Layer

Classifies actions by risk and applies guardrails.

Initial risk classes:

```text
safe: observe, inspect, read, focus, hover
reversible: open menu, select field, type draft text, scroll
committing: submit, send, delete, purchase, overwrite, finalize
unknown: action semantics unclear
```

### State Memory

Stores learned information about apps and windows.

Responsibilities:

- Remember stable control mappings.
- Track known screens/states.
- Store successful action sequences.
- Store dangerous controls.
- Store app-specific quirks.

## 7. MVP Objective

Create a daemon and CLI that can inspect a running desktop app, expose its controls as structured JSON, and execute simple low-risk actions through a standard vocabulary.

## 8. Initial Target Apps

Use simple but representative apps:

1. A basic text editor.
2. A calculator app.
3. A native system settings/dialog window.
4. One legacy/native desktop app if available.
5. One Electron app as a stretch target.

## 9. Key Design Constraints

- The agent should consume structured JSON, not prose.
- The raw UI tree should be available, but not the primary interaction model.
- Every action should return an observation or verification result.
- Every executable control should have risk metadata.
- The system should prefer semantic execution over coordinate execution.
- Coordinates should be a fallback, not the main abstraction.
- Vision should repair or enrich the semantic model, not replace it.
- Ambiguity should be explicit.
