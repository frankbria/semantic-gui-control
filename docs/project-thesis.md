# Project Thesis

## Problem

Most desktop and many web applications expose work through graphical interfaces designed for humans. LLM agents that operate these interfaces today rely heavily on screenshots, OCR, and coordinate clicking. That approach is brittle, slow, hard to verify, and overconfident about what it just did.

The actual interface usually exists in a more structured form than pixels: an accessibility tree, a DOM, a window manager registry, focus traversal order, keyboard shortcuts, or an app-specific API. Agents skip that structure because no consistent layer exposes it.

## Thesis

Build a text-first control layer that:

1. Discovers the usable interface from the environment.
2. Normalizes it into structured affordances.
3. Exposes a small standard command vocabulary.
4. Executes through platform adapters.
5. Verifies state changes against observed evidence.
6. Uses vision/OCR only as fallback or cleanup.

> Vision is the spare tire, not the steering wheel.

A screenshot is not the interface. It is a rendering of the interface for human eyes. The actual interface is a tree of controls with roles, labels, states, and supported actions. SGCL surfaces that tree.

## Why structured sources first

Preference order, strongest to weakest:

1. **Accessibility APIs** — Windows UIA, macOS AX, Linux AT-SPI. Designed exactly for this: machine-readable role, label, state, supported actions.
2. **DOM** — for browser contexts via Playwright or CDP. Most semantically rich source available.
3. **OS automation APIs** — UI Automation invoke patterns, AppleScript, native scripting bridges.
4. **Keyboard traversal** — focus order, accelerators, mnemonics. Reveals which controls the app considers interactive.
5. **App APIs** — when present, prefer them over poking the GUI.
6. **Vision / OCR / pixel coordinates** — only when the above are missing, lying, or incomplete.

Each layer above pixels gives the agent more semantics and less guessing. Vision is the recovery path, not the entry point.

## Non-goals

The first version is not trying to:

- Automate every app perfectly.
- Replace full RPA platforms like UiPath or Power Automate Desktop.
- Provide a visual workflow designer.
- Treat computer vision as the primary interface layer.
- Automate high-risk actions without explicit safety gates.
- Offer domain-specific verbs like "book a flight" or "submit insurance claim" as native commands.
- Pretend cross-platform parity exists from day one. The contract is uniform; capability may vary by adapter.

## Guiding principles

- **Small, boring vocabulary.** OBSERVE, FIND, READ, FOCUS, TYPE, INVOKE, SELECT, SCROLL, WAIT, VERIFY, ESCAPE, UNDO. If a verb is not platform-neutral, it does not belong in the core.
- **Structured output, not prose.** Agents consume JSON. Humans read pretty-printed JSON or wrapped views of it.
- **Evidence over assertion.** Every action returns observation, not just "I clicked it."
- **Ambiguity is explicit.** When multiple controls match, return all of them with confidence. Do not guess silently.
- **Risk is first-class.** Every executable control has a risk class. Committing actions are not run blind.
- **Platform-neutral core, platform-specific adapters.** The core does not know it is talking to UIA. Adapters do not leak their dialect upward.
- **Raw is available but not primary.** The platform-native tree may be exposed for debugging. The agent-facing model is the normalized one.
- **Coordinates are a fallback.** They are not the abstraction. They appear in `bounds`, not in the command verbs.
