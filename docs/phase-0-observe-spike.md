# Phase 0: Observe Spike

The first thing SGCL must prove is that it can look at a real desktop and return structured text. Nothing else matters until this works.

## Goal

Prove that SGCL can observe a real desktop GUI and return a useful structured JSON representation of it, using exactly one platform adapter.

## Learning question

> Can we expose a real desktop GUI as structured text without screenshots?

If the answer is yes — even partially — we have something to build on. If the answer is no, we need to know exactly *why* before we proceed (this is itself a valid blunt-win outcome).

## Scope

Three CLI commands:

```bash
sgcl windows
sgcl active
sgcl inspect --active --depth <n>
```

Optionally also:

```bash
sgcl inspect --window <window_id> --depth <n>
```

All output is JSON by default.

### `sgcl windows`

Lists open top-level windows.

Per window, return at minimum:

- `id` — stable within this CLI invocation (and ideally within the daemon session, but not required for the spike).
- `title`
- `process_name`
- `pid`
- `bounds` — `{ x, y, width, height }` if available.
- `visible` — boolean.
- `is_active` / `is_foreground` — boolean, if available.

### `sgcl active`

Returns the currently focused / foreground window in the same shape as one entry of `sgcl windows`.

### `sgcl inspect --active --depth N`

Walks the chosen window's UI Automation tree up to depth `N` and returns a hierarchical JSON representation.

Each control node should contain at minimum:

- `id` — stable within this invocation.
- `role` — adapter-mapped to the normalized role vocabulary (see `affordance-model.md`). Where mapping is uncertain, keep the native role and flag it.
- `label` / `name` — best-effort accessible name.
- `enabled`
- `visible` — if available.
- `bounds` — if available.
- `actions` — supported normalized actions inferred from the available UIA patterns (e.g., `Invoke`, `Toggle`, `Value`, `Selection`).
- `children` — array of nested controls.
- Optional `raw_ref` containing UIA fields useful for debugging (ControlType, AutomationId, ClassName, FrameworkId).

The schema can be a simplified subset of the full affordance model for the spike. Phase 1 (Normalize) will tighten it.

## Initial platform

Windows, via UI Automation. Likely tools:

- `pywinauto` — high-level Python wrapper.
- `uiautomation` (Yinkaisheng) — closer to raw UIA.
- `comtypes` + UIA COM interfaces directly — most control, most code.

The spike picks whichever is fastest to get to a working JSON dump. Library choice is documented in the spike notes; it is not a long-term commitment.

## Acceptance criteria

The Phase 0 spike is done when **all** of the following hold:

- [ ] `sgcl windows` returns the list of open windows for the current session with title, process name, bounds, and active/foreground state where available.
- [ ] `sgcl active` correctly identifies the foreground window.
- [ ] `sgcl inspect --active --depth N` returns a hierarchical JSON tree of the active window's controls.
- [ ] Each control includes `id`, `role`, `label` (or accessible name), `enabled`, `visible` (where available), `bounds`, and `actions` (where inferable).
- [ ] Output is valid JSON by default. A `--pretty` flag is optional but nice.
- [ ] Works against **Notepad** and **Calculator** end-to-end.
- [ ] A spike note exists at `spikes/windows-observer-results.md` covering: environment, apps tested, what worked, what failed, surprises, constraints discovered, assumptions killed, and a recommended next step for Phase 1.

## Non-goals

Phase 0 explicitly does **not**:

- Click, type, invoke, or otherwise change any state.
- Use vision, screenshots, or OCR.
- Implement an agent planner or LLM loop.
- Define the full daemon API.
- Ship a cross-platform implementation. Windows-only is fine here.
- Stabilize control IDs across sessions. Within-invocation is enough.
- Build a final affordance schema. This spike informs Phase 1.

## Risks to watch

- **Shallow trees.** Some apps return a flat or near-empty UIA tree even when they look interactive. Document which apps.
- **Slow walks.** Walking large trees over COM can be very slow. Time and report.
- **Garbage labels.** Some controls expose empty `Name` and only a `ControlType`. Note coverage rates.
- **Permission quirks.** Elevated apps may be invisible to unelevated UIA. Document.
- **Multi-monitor.** Bounds may be negative or span virtual desktops. Don't break on it; report what was seen.

## Deliverables

1. The three CLI commands above, working against Notepad and Calculator.
2. JSON output that conforms to the simplified spike schema and is rich enough to inform the Phase 1 normalization design.
3. The completed `spikes/windows-observer-results.md`.
4. A short note in `docs/open-questions.md` listing every question the spike opened.
