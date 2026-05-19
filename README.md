# Semantic GUI Control

A cross-platform, text-first control layer for agentic interaction with graphical user interfaces.

The core thesis: agents should not treat a GUI as pixels first. They should discover the usable interface surface, normalize it into structured affordances, execute through a small standard vocabulary, and verify what changed.

## Current status

Planning/specification stage. No production code yet.

## Near-term goal

Build a small spike that can:

1. List active windows.
2. Inspect a selected window's interface tree.
3. Normalize discovered controls into a compact affordance model.
4. Execute simple actions such as focus, type, invoke, and hotkey.
5. Verify before/after state changes.

## Documentation

See `docs/`:

- `level-1-spec.md` — first-level product and system specs.
- `cross-platform-strategy.md` — Windows, Linux, and macOS abstraction strategy.
- `development-sequence.md` — build order from spike to learned app maps.
- `command-vocabulary.md` — proposed universal command grammar.
- `use-cases.md` — initial demo/use cases.
- `adr-0001-cross-platform-first.md` — initial architecture decision record.

## Working metaphor

A terminal for the visual operating environment.

Not because everything becomes text, but because the GUI becomes inspectable, commandable, and verifiable.
