# Windows Observer Spike — Results

> Living document. Fill in as Phase 0 progresses. Do not delete unanswered
> sections — leave them blank if not yet known and note why.

## Date

Run 1: 2026-05-19 (initial commands ran against Warp terminal; revealed
the focus-targeting constraint; non-focus-based flags added in response).

## Environment

- OS / build: Windows 11
- Shell host: Warp terminal (PowerShell profile)
- Python / language and version: 3.12 via `uv`
- UIA library and version: `uiautomation` (Yinkaisheng) — chosen for Phase 0
  because it sits close to raw UIA primitives, which suits read-only tree
  dumping; we can revisit at Phase 3 (Act) if its execution ergonomics
  become limiting.
- Display config (monitors, DPI, scaling): multi-monitor (negative x bounds
  visible in `01-windows.json`; second display is to the left of the primary).
- Elevated or non-elevated session: non-elevated (default).

## Apps tested

- [x] `sgcl windows` against the live desktop (Run 1)
- [ ] Notepad (control tree via `--window` or `--process`)
- [ ] Calculator (control tree via `--window` or `--process`)
- [ ] Stretch: classic Win32 app (regedit / mspaint / Control Panel) for
      contrast against WinUI apps

## Commands run (Run 1)

```powershell
sgcl --pretty windows                              # OK; full enumeration
sgcl --pretty active                               # returned Warp, not target
sgcl --pretty inspect --active --depth 3           # inspected Warp instead
```

Samples committed to `spike/phase-0-samples` branch:
`spikes/samples/01-windows.json` through `05-inspect-calculator-d3.json`.

## What worked

- `sgcl windows` produced a clean JSON enumeration: HWND ids, populated
  titles, process names, real PIDs, bounds (including negative-x on a
  multi-monitor setup), `visible`, `is_active`.
- Notepad's process name came back as `Notepad.exe` (capital N — likely the
  modern Notepad). Calculator showed up similarly.
- JSON output round-trips cleanly; nothing required post-processing.
- `--pretty` formatting works both before and after the subcommand.

## What failed

- `sgcl active` and `sgcl inspect --active` both targeted the terminal
  running the command (Warp), never the intended app. See "Assumptions
  killed" below.
- `inspect` of the Warp window returned `children: []` even at depth 3.
  Could be (a) Warp exposes no UIA subtree below its top window, or
  (b) `GetChildren()` threw and we swallowed it. **Cannot disambiguate
  until we re-run against a UIA-friendly app (Notepad / Calculator) via
  `--window hwnd_<int>` or `--process Notepad`.** That is the Run 2 task.

## Raw observations

Selected highlights from Run 1 samples:

- Warp updates its window title to the currently running command line.
  This means `active`/`inspect --active` outputs contain a `title` /
  `label` of the form `"uv run sgcl --pretty active | Tee-Object ..."`.
  Win32 truncates long titles, producing trailing `à` glyphs.
- `is_active: true` consistently matched Warp's HWND in `01-windows.json`.
- The window list included taskbar entries (`explorer.exe`) and
  `Program Manager`, which is the desktop shell window. These are
  technically top-level but agents probably don't want them surfaced.
  Worth a filter/flag in Phase 1.
- Multiple Notepad windows would be ambiguous by process name; the new
  `--process` flag errors with a structured list rather than guessing.

## Surprises

1. **The terminal is the foreground.** Obvious in hindsight, not predicted
   by the planning docs. Every "active" query from a CLI sees the terminal,
   never the intended target.
2. **Warp's UIA tree appears empty below the top window.** May be a
   non-standard shell; may be a walk error we swallowed. Telemetry is
   missing — we should at least log when `GetChildren()` throws.
3. **Title truncation** from Win32 produces non-printable trailing chars
   that survive into JSON. Not our bug, but worth knowing.

## Constraints discovered

- **Focus is not a reliable selector** in a multi-window environment. The
  CLI cannot assume "what's focused" is what the user means. Targeting
  must work without focus: by HWND, process name, title substring, or PID.
- The `Program Manager` window and taskbar are surfaced as top-level
  windows. Need a way to filter them or mark them as system surfaces.
- Some windows (Proton Mail in the Run 1 dump) report `0×0` bounds while
  still being `visible: true`. Likely background-only / system-tray
  presences. The current code emits the bounds as-is rather than guessing.

## Assumptions killed

- **"If the user focuses an app and runs `sgcl`, the command will see that
  app as active."** False. The terminal that runs `sgcl` holds focus.
  This is the primary Run 1 finding, and the reason `--active` is now
  documented as unreliable from a CLI and `--process` / `--title` /
  `--window` are the recommended targeting flags.
- **"`--active` is the natural default for inspect."** No. It is one of
  several target selectors, and probably not the right default for a CLI.

## Recommended next step

1. **Run 2 with the new flags.** Open Notepad and Calculator (both modern
   WinUI on Win11). From a Warp PowerShell tab:
   ```powershell
   uv run sgcl --pretty inspect --process Notepad     --depth 3 | Tee-Object spikes\samples\06-notepad.json
   uv run sgcl --pretty inspect --process Calculator  --depth 3 | Tee-Object spikes\samples\07-calculator.json
   ```
   This answers: does Phase 0's walk actually work, or is Finding 2
   universal?
2. **If trees come back empty too**, add diagnostic logging around the
   `GetChildren()` call in `_build_control` and re-run. Should not happen
   silently.
3. **If trees come back populated**, fill in the remaining sections of
   this doc, then move to Phase 1 (Normalize). The schema design will
   need to handle: WinUI vs classic Win32 differences, missing accessible
   names, and the system/shell windows we currently surface.
