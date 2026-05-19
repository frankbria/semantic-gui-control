# ADR 0001: Cross-Platform Core, Adapter-Specific Execution

## Status

Proposed

## Context

The project should not overfit to Windows even if Windows is the first or easiest spike target. The same conceptual model should apply to Windows, macOS, Linux, browser DOMs, remote desktops, and possibly mobile environments.

Each platform exposes different mechanisms:

- Windows: UI Automation, Win32, COM, PowerShell.
- macOS: AX accessibility APIs, AppleScript, Shortcuts.
- Linux: AT-SPI, D-Bus, wmctrl, xdotool/ydotool, compositor-specific APIs.
- Browser: DOM and browser automation protocols.

## Decision

The core system will define platform-neutral schemas and commands. Platform-specific adapters will translate native accessibility/windowing data into the normalized affordance model.

The agent-facing vocabulary will not expose platform-native implementation details unless explicitly requested for debugging.

## Consequences

Positive:

- The core can support multiple operating systems.
- The agent gets a stable vocabulary.
- Platform quirks stay contained behind adapter boundaries.
- Browser automation and desktop automation can eventually share a command model.

Negative:

- The first implementation requires more discipline.
- Some platform-native capabilities may be awkward to represent generically.
- The generic affordance model may need iterative refinement.

## Guiding Rule

If a concept cannot plausibly exist across Windows, macOS, Linux, and browser DOMs, it should not be part of the core command vocabulary. It may still exist as adapter-specific metadata.
