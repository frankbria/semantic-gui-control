# Windows Observer Spike — Results

> Filled in across three runs (2026-05-19) against Windows 11.
> Phase 0 acceptance: **met**. Findings consolidated below.

## Date

- Run 1: 2026-05-19 — initial commands; surfaced focus-targeting constraint.
- Run 2: 2026-05-19 — Notepad + Calculator at depth 3 via new targeting flags.
- Run 3: 2026-05-19 — Calculator at depth 8; surfaced full keypad + display.

## Environment

- OS / build: Windows 11
- Shell host: Warp terminal (PowerShell profile)
- Python / language and version: 3.12 via `uv`
- UIA library and version: `uiautomation` (Yinkaisheng) — chosen for Phase 0
  because it sits close to raw UIA primitives, which suits read-only tree
  dumping. To be revisited at Phase 3 (Act) if its execution ergonomics
  become limiting.
- Display config: multi-monitor (negative x bounds visible in window list;
  second display is to the left of the primary).
- DPI: per-monitor DPI awareness set at adapter init; reported `bounds` are
  in physical screen coordinates and matched visually.
- Elevated or non-elevated session: non-elevated. Not yet tested across
  the elevation boundary.

## Apps tested

- [x] Notepad (Win11 WinUI; `Notepad.exe`)
- [x] Calculator (Win11 WinUI; runs inside `ApplicationFrameHost.exe`)
- [ ] Stretch: classic Win32 app (regedit / mspaint / Control Panel) —
      deferred to Phase 1 spike if useful.

## Commands run

```powershell
# Run 1
sgcl --pretty windows
sgcl --pretty active
sgcl --pretty inspect --active --depth 3

# Run 2 (after non-focus-based targeting was added)
sgcl --pretty inspect --process Notepad    --depth 3
sgcl --pretty inspect --title Calculator   --depth 3   # disambiguation caught Warp's title
sgcl --pretty inspect --window hwnd_<...>  --depth 3

# Run 3
sgcl --pretty inspect --window hwnd_<calc> --depth 8
```

Samples committed at `spikes/samples/01-windows.json` …
`09-calculator-d8.json`.

## What worked

- **Window enumeration.** `sgcl windows` returns HWND ids, real titles,
  process names, PIDs, bounds (including negative x on multi-monitor),
  `visible`, `is_active`. Clean JSON.
- **Targeting by HWND, process, title, PID.** Reliable and predictable.
  Ambiguous matches refuse to guess and list the candidates.
- **Tree walks** for Notepad and Calculator. At depth 8 Calculator
  surfaces its full scientific keypad (Zero–Nine, Plus/Minus/Multiply/
  Divide/Equals, Pi, Square root, Factorial, Memory ops, etc.) plus the
  display field as a `static_text` with `AutomationId: "NormalOutput"`.
- **Action inference.** Buttons → `["focus", "invoke"]`. Static text →
  `["read"]`. Panes/menus → `["focus"]`. Matches what the controls
  actually support.
- **Rich labels.** Notepad toolbar buttons include keyboard shortcuts in
  the accessible name: "Bold (Ctrl+B)", "Clear formatting (Ctrl+Space)".
  Calculator buttons are human-readable across the board: "Divide by",
  "Memory recall", "Open history flyout".
- **State-revealing text.** Notepad status bar exposes cursor position
  ("Line 520, Column 21"), document length ("21,783 characters"), and
  encoding ("UTF-8") as readable static_text. This is the Phase 0 thesis
  literally working: agent can verify state without a screenshot.
- **`raw_ref`** preserves UIA `AutomationId`, `ClassName`,
  `LocalizedControlType`, and `ControlTypeName` for debugging without
  polluting the normalized fields.
- **UTF-8 stdout.** After a fix, icon-font glyphs in the Unicode Private
  Use Area survive the JSON round-trip.

## What failed (and was fixed mid-spike)

- **`--active` from a CLI.** Always returns the terminal hosting `sgcl`.
  Fix: added `--process`, `--title`, `--pid`, `--window`, `--delay`.
  `--active` is retained but documented as unreliable from CLI contexts.
- **UnicodeEncodeError on Calculator at depth 8.** Calculator's tree
  includes PUA codepoints (e.g., ``, almost certainly a Segoe
  Fluent Icons glyph). Python on Windows defaulted stdout to cp1252.
  Fix: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at
  CLI entry. Regression test added.
- **Default depth 3 misses Calculator's keypad.** Not a bug — UWP apps
  are deeper than classic Win32. Workaround for spike: depth 8. Phase 1
  (Normalize) will want a smarter walker, or different default depths
  by adapter / app, or a flatten-structural-panes pass.
- **Apparent empty Warp tree** in Run 1. Confirmed Warp-specific in
  Run 2 — Notepad and Calculator returned full trees with the same
  walker. Warp's window genuinely doesn't expose a UIA subtree.

## Raw observations

Selected data points from Run 3 (Calculator, depth 8):

- 126 controls under one window.
- 50 buttons, 57 static_text nodes, 7 groups.
- Buttons named "Zero" through "Nine" (English number words, not digits).
- Scientific keypad: "Pi", "Euler's number", "Square root", "Factorial",
  "Trigonometry", "Log", "Natural log", "Exponential", "Scientific
  notation", "Absolute value", "Inverse function", "Reciprocal",
  "'X' to the exponent", "Ten to the exponent".
- Memory keypad: "Memory add", "Memory subtract", "Memory store",
  "Memory recall", "Clear all memory".
- Display: `static_text` with `AutomationId: "NormalOutput"` and value
  `"0"` — directly readable.
- Mode indicator: `static_text` "Scientific Calculator mode".

Notepad (depth 3, 32 actionable controls):

- Toolbar buttons with kb-shortcut labels.
- ClassNames like `Microsoft.UI.Xaml.Controls.DropDownButton` and
  `ToggleButton` preserved in `raw_ref` for Phase 1 disambiguation.
- A pane label revealed Copilot integration: "Local AI model must
  complete downloading to use this feature while signed out."

## Surprises

1. **The terminal is the foreground.** Not predicted by the planning
   docs. Drove the non-focus-based targeting redesign.
2. **UWP apps run inside `ApplicationFrameHost.exe`.** Process-name
   targeting unreliable for UWP/WinUI; title or HWND is the right
   selector. Documented in the CLI help and risk model context.
3. **Self-titling terminals corrupt substring title matching.** Warp
   echoes the running command into its window title, so `--title Calc`
   matched both Warp and the real Calculator. The "ambiguity is
   explicit" rule kicked in correctly and refused to guess.
4. **Icon-font glyphs in accessible labels.** WinUI uses PUA codepoints
   from Segoe Fluent Icons inside `Name`. These survive into JSON
   (now), but Phase 1 should decide: strip, preserve, or render as a
   description (e.g., `"<icon: hamburger>"`).
5. **Depth 3 is enough for some apps, nowhere near enough for others.**
   Notepad's toolbar happens to be flat. UWP visual trees are deep.
   Phase 1's walker needs a smarter strategy than fixed depth.
6. **Calculator buttons named in English words** ("Zero", "Plus"), not
   `"0"`, `"+"`. Agents querying by literal symbol will miss. FIND
   semantics need to know both surfaces.
7. **The window list includes shell surfaces** — Taskbar, Program
   Manager — as top-level windows. Probably not what agents want by
   default.

## Constraints discovered

- Focus-based targeting is not reliable in a multi-window environment.
  Documented in `docs/phase-0-observe-spike.md` and CLI help.
- Tree depth is not a one-size-fits-all parameter; different app
  frameworks expose different shapes. The walker probably needs to
  detect/flatten structural panes rather than rely on caller depth.
- The walker swallows `GetChildren()` exceptions silently. Acceptable
  for Phase 0 but Phase 1 should log them — we can't otherwise tell
  "empty tree" from "walker failed."
- UWP / WinUI process name is the host, not the app. Title or HWND is
  the agent-facing selector.

## Assumptions killed

- "If the user focuses an app and runs `sgcl`, the command will see
  that app as active." **Killed.**
- "`--active` is the natural default for `inspect`." **Killed.** It is
  one of several selectors, and not the right default for a CLI.
- "Calculator process is `Calculator.exe`." **Killed** — it's
  `ApplicationFrameHost.exe`.
- "Substring title matching is safe." **Killed** when the terminal is
  self-titling.
- "Python's `print()` of JSON-serialized text always works." **Killed**
  on Windows when PUA codepoints are present in labels.
- "A single fixed depth is enough to inspect representative apps."
  **Killed** — Notepad and Calculator wanted very different depths to
  reach their interactive surfaces.

## Recommended next step

Phase 0 is done. The thesis holds: a real desktop GUI can be exposed
as structured text, and an agent can plan against that structure
without screenshots. We have the full Calculator vocabulary and the
Notepad state-readback fields as evidence.

Phase 1 (Normalize) should specifically address:

1. **Walker strategy.** Move from fixed `--depth` to a smarter walk that
   collapses structural panes and stops at semantically meaningful
   subtrees. Default depth should be larger than 3 (probably 8–10) but
   the walker should also know when to keep going.
2. **Icon-font labels.** Decide on a canonical handling for PUA
   codepoints. Probably: keep the raw label, add a `description` field
   when we can map the glyph to a known meaning.
3. **System surfaces filter.** Tag Taskbar / Program Manager / shell
   windows as system surfaces; let CLI/agents opt out by default.
4. **Walker exception logging.** Diagnose empty subtrees instead of
   swallowing.
5. **Synonyms / alternative labels.** Calculator names buttons
   "Zero"/"Plus"; agents may query "0"/"+". The FIND phase needs to
   know both. Likely belongs in the affordance schema, not in FIND.
6. **Pane reduction.** 12 unlabeled panes in a Notepad tree is noise.
   The normalizer should flatten or hide structural-only panes.

Issue #1 (Observe) on GitHub can be closed against this report.
