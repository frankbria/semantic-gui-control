# ADR 0003: Python and `uiautomation` for the First Adapter

## Status

Accepted, retroactively. The choice was made during Phase 0 prep and
recorded only as a checklist line in `tasks/todo.md`; this writes down the
reasoning and the trigger for revisiting it. Revisit when a second adapter
lands (Win 9) or if `uiautomation` proves inadequate for Phase 3 input
synthesis.

## Context

Two questions were open, and they are related:

**Python-first or .NET-first for Windows UIA?** .NET/C# gives the most
direct and fastest access to UI Automation — it is Microsoft's own surface
for it. Python reaches UIA through `comtypes` and wrapper libraries, which is
slower and one indirection further from the API.

**Where does the core live?** Splitting languages across core and adapter was
possible: a .NET adapter subprocess speaking to a Python core, or the reverse.

The project's constraint is that Phase 0 was a *spike* — its job was to
answer "can we expose a real desktop GUI as structured text at all?" A spike
optimizes for time-to-answer, not for the fastest steady-state runtime.

Within Python there were two candidate wrappers. `pywinauto` is the
better-known automation library; `uiautomation` (Yinkaisheng) is a thinner
wrapper closer to the raw UIA primitives.

## Decision

**Python for both the core and the first adapter. `uiautomation` as the UIA
wrapper.**

`uiautomation` was chosen over `pywinauto` because it sits closer to raw UIA
and is a better fit for read-only tree dumping — Phase 0's entire job.
`pywinauto` adds an automation-framework layer (window specs, waiting,
retry semantics) that Phase 0 did not need and that would have obscured what
UIA itself reports. When the question is "what does the accessibility tree
actually contain", a thinner wrapper gives a more honest answer.

Keeping the core in Python too avoids a cross-process protocol before there
is any evidence one is needed. Adapters may become language-specific
subprocesses later; nothing in the design prevents it.

This is a **convenience-first** decision, consistent with how `CLAUDE.md`
describes it. It is not a claim that Python is the right long-term host.

## Consequences

- The adapter accesses `uiautomation` **duck-typed**, which is what makes the
  walker, readers and window helpers testable on Linux. That is a real
  benefit of the wrapper being thin.
- The same duck-typing means an upstream API change would not fail to
  import — it would produce a degraded tree at runtime. See the mock-drift
  entry in [`open-questions.md`](../open-questions.md); the dependency is
  capped `<3` and `tests/test_uia_conformance.py` is the only detector.
- The CLI requires Windows at runtime. The core model and the whole test
  suite do not.
- Performance is untested. No phase so far has been latency-sensitive; a
  daemon (still undecided — see open questions) would change that.
- `pywinauto` was not evaluated against Phase 3's needs. It has richer
  *input synthesis*, which is exactly what Phase 3 requires and Phase 0 did
  not. That is a genuine open risk, not a settled matter.

## Alternatives considered

- **.NET/C# adapter with a Python core.** Fastest UIA access, but adds a
  cross-process protocol and a second toolchain before the project had
  proven its central premise. Deferred, not rejected — if Phase 3 finds
  Python's input synthesis inadequate, this is the first thing to look at.
- **`pywinauto`.** Better known and more capable for driving applications;
  more layers between the caller and what UIA reports, which is the wrong
  trade for an observation spike.
- **Raw `comtypes` against UIA COM directly.** Maximum fidelity, maximum
  boilerplate. Neither wrapper's cost had been shown to matter.

## Revisit triggers

- **Phase 3 input synthesis.** If `uiautomation` cannot reliably synthesize
  the keyboard and invoke patterns Act needs, re-evaluate `pywinauto` or a
  .NET adapter. This is the most likely trigger.
- **A second adapter (Win 9)** shows the Python core is the wrong host for
  cross-platform work.
- **`uiautomation` becomes unmaintained**, or ships a 3.0 that breaks the
  duck-typed surface.
- **Latency becomes a constraint** — most likely when a daemon lands, if it
  does.
