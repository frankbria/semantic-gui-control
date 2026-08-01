# ADR 0004: System Surfaces Are Filtered by Default

## Status

Accepted, retroactively. Shipped in Phase 1; the question was left open in
`open-questions.md` even though the code had answered it. Revisit when Phase 3
lands execution — see the trigger below, which is a real one.

## Context

Phase 0 surfaced `Program Manager`, the taskbar, notification centres and
similar shell windows in `sgcl windows`, because they *are* top-level windows.
An agent asking "what windows are open" almost never means them, and they
crowd out the handful of application windows that were actually wanted.

Three options were live:

1. Filter them by default, with a flag to opt in.
2. Always emit everything and let the agent filter.
3. Filter with no way to see them at all.

Option 3 was never seriously considered — it would make shell windows
unreachable, and an adapter that cannot describe part of the desktop is
lying about what it observes.

The tension between 1 and 2 is real. Filtering by default is a
*policy* decision baked into an observation tool, and this project's
principle is that the adapter reports and the caller decides.

## Decision

**Tag in the adapter; filter in the CLI; default to filtering; expose
`--include-system` to opt in.**

The split matters:

- `WindowInfo.is_system_surface` is set by the adapter
  (`sgcl/adapters/windows_uia/_system.py`). The adapter **only tags** — it
  never omits a window.
- The CLI applies the default filter. `--include-system` turns it off.

So the policy lives in exactly one place, the data always carries the tag,
and any other consumer of the adapter sees everything and can decide for
itself. Nothing is hidden at the layer whose job is to observe.

The heuristic is deliberately narrow: a window owned by `explorer.exe` whose
title is empty or matches a known shell-window name. A real Explorer folder
window has a folder name as its title and is not tagged.

Validated in `spikes/normalize-results.md`.

## Consequences

- The common case — "what applications are open" — returns a short, useful
  list without the agent writing a filter.
- The heuristic is **Windows-shaped and name-based**. A second adapter must
  supply its own notion of a system surface; there is nothing portable about
  `explorer.exe`. The *field* is portable, its derivation is not.
- Localized Windows installs are a known gap: the shell-title list is
  English. A non-English system will under-tag, and the failure is silent —
  extra windows appear rather than an error.
- An empty-titled `explorer.exe` window is tagged on the assumption it is a
  secondary taskbar or shell artifact. That assumption is untested against
  multi-monitor setups beyond the ones in the spike.

## Revisit triggers

- **Phase 3, when actions arrive.** This is the important one, flagged in
  [`handoff-phase-3-planning.md`](../handoff-phase-3-planning.md). Filtering
  is clearly right for *observation*. It is not obviously right once an agent
  can act: a task that genuinely needs the taskbar or a notification centre
  would find the target absent by default, with no signal explaining why.
  Whether `--include-system` is the right ergonomics for an acting agent is
  open.
- **A second adapter (Win 9)** needs a system-surface notion that does not
  reduce to a process name.
- **A non-English Windows install** is used in earnest, exposing the
  hardcoded title list.
