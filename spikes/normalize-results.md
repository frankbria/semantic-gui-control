# Normalize Spike — Results

> Phase 1 acceptance: **met**. Findings consolidated below across six runs
> against the same Notepad + Calculator scenes used in Phase 0.

## Date

2026-05-19 (Phase 1 Runs 4–6, against the same Windows 11 environment as
the Phase 0 spike).

## Environment

- OS / build: Windows 11
- Shell host: Warp terminal (PowerShell profile)
- Python / language and version: 3.12 via `uv`
- UIA library: `uiautomation` (Yinkaisheng)
- Display config: multi-monitor; per-monitor DPI awareness honored.

## Apps tested

- [x] Notepad (Win11 WinUI; `Notepad.exe`) at depth 3
- [x] Calculator (Win11 WinUI inside `ApplicationFrameHost.exe`) at depth 8

Sample files in `spikes/samples/`: `10–15-*.json` are Phase 1 captures;
compare against the Phase 0 captures `06`/`07`/`08`/`09`.

## What was added in Phase 1

Six implementation slices, each independently mergeable:

| Slice | What it added |
|-------|---------------|
| E.1 | `confidence`, `description`, `synonyms` on `Control`; `is_system_surface` on `WindowInfo` |
| E.2 | Coarse adapter-confidence heuristic in `sgcl/core/confidence.py` (4 signals × 0.25 each) |
| E.3 | Walker exception logging; system-surface filter; refactor for Linux testability |
| E.4 | Icon-font glyph descriptions (PUA codepoint → human name) |
| E.5 | Structural pane reduction (collapse unlabeled single-child pane chains) |
| E.6 | Label synonyms for Calculator's word-named buttons |
| E.6b | `--output PATH` flag to bypass PowerShell pipe encoding |

## What the Phase 1 output actually looks like

### Calculator at depth 8

| Measure | Phase 0 | Phase 1 |
|---------|---------|---------|
| Control count | 126 | 126 |
| Panes flattened | n/a | 0 |
| Controls with synonyms | 0 | **20** |
| Controls with `description` (icon hint) | 0 | **2** |
| Confidence distribution (1.0 / 0.75 / 0.5 / 0.25 / 0) | n/a | **56 / 62 / 6 / 2 / 0** |

### Notepad at depth 3

| Measure | Phase 0 | Phase 1 |
|---------|---------|---------|
| Control count | 43 | **36 (−16%)** |
| Panes flattened (recorded in `raw_ref.flattened`) | n/a | **7** |
| Confidence distribution (1.0 / 0.75 / 0.5 / 0.25 / 0) | n/a | **11 / 17 / 6 / 2 / 0** |

Notepad's structural panes were exactly the noise the spec called out;
collapsing them dropped 7 controls without losing information (the
flattened ids are preserved in `raw_ref.flattened` for reconstruction).
Calculator's tree didn't shrink because its structural containers are
`GroupControl`, not `PaneControl` — the heuristic deliberately targets
panes only. Phase 2 (Find) can decide whether to extend the rule.

## Confidence distribution is honest

Both apps show a real spread, not uniformly 1.0:

- Top of the scale (1.0) = labeled, role-specific, actionable, has an
  `AutomationId`. Notepad toolbar buttons, Calculator's keypad buttons,
  Calculator's `NormalOutput` display all land here.
- 0.75 = three of four signals present. Most commonly: no `AutomationId`
  on a structurally well-formed control. Calculator's status text and
  many WinUI buttons.
- 0.5 = two signals. Typically a structural pane that's at least kept
  the role label.
- 0.25 = one signal. Truly bare structural containers.
- 0.0 was achievable in synthetic tests but never appeared in real
  output — every real UIA control had at least *some* signal.

That spread is what we wanted: the agent can prioritize 1.0 controls
and treat 0.25 as "ambient structure, probably not a target."

## Synonyms validated

20 Calculator controls got synonym lists. Round-trip check from sample
15:

```text
'Zero'              -> ['0']
'Plus'              -> ['+']
'Minus'             -> ['−', '-']
'Multiply by'       -> ['×', '*']
'Divide by'         -> ['÷', '/']
'Equals'            -> ['=']
'Pi'                -> ['π']
'Square root'       -> ['√']
'Decimal separator' -> ['.']
'Left parenthesis'  -> ['(']
```

Phase 2 (FIND) will match a `--label "0"` query against `synonyms` as
well as `label`. Without that, an LLM prompted to "click 0" would miss
the "Zero"-labeled button entirely.

## Icon-font descriptions partially validated

Calculator surfaces 27 controls whose `label` is a Private Use Area
codepoint (Segoe Fluent Icons). Of those, 2 mapped to our starter
dictionary as `"icon: ChevronDown"`. The other 25 returned
`description=None` — our policy refuses to invent names for
unrecognized codepoints.

Codepoints we observed but don't have names for yet:

```
U+E61D  U+E81C  U+E94F
U+F754  U+F755  U+F756  U+F757  U+F758
U+F7C8  U+F7CF
U+F892  U+F893  U+F897
```

These can be added to `sgcl/core/icon_glyphs.py` as their meanings are
identified (Microsoft's published Segoe Fluent Icons reference covers
most of these).

## System-surface filter validated

`sgcl windows` defaults to filtering shell surfaces; `--include-system`
shows them.

| Mode | Windows returned |
|------|------------------|
| `sgcl windows` (default) | 10 |
| `sgcl windows --include-system` | 13 |
| Filtered: | `Taskbar`, secondary taskbar (empty title + `explorer.exe`), `Program Manager` |

Targeting by `--process`/`--title`/`--pid` also skips system surfaces by
default. `--window <hwnd>` always honors the explicit choice.

## New finding: PowerShell pipe encoding corruption

Run 4 produced a sample where every non-ASCII synonym and every icon-
glyph label had been corrupted — `π` came out as `╧Ç`, button labels
showed up as `εá£` and `∩¥ö` patterns. We initially misdiagnosed this
as a Python source-file encoding issue and rewrote `synonyms.py` with
`\uXXXX` escapes. That fix changed nothing.

The actual cause: PowerShell's pipe (`Out-File`, `Tee-Object`, `|`)
decodes our UTF-8 stdout bytes as cp437 by default on this machine,
then re-encodes the resulting mojibake string as UTF-8 on write. The
bytes `\xcf\x80` (UTF-8 for π) became `╧Ç` (cp437 of those two bytes),
which then got written as UTF-8 `\xe2\x95\xa7\xc3\x87`.

`_LABEL_SYNONYMS['pi']` was always correct in Python memory; we
confirmed by running `uv run python -c "from sgcl.core.synonyms import
_LABEL_SYNONYMS; print(_LABEL_SYNONYMS['pi'])"` which returned `('π',)`
correctly.

The fix that actually works: **don't go through the shell pipe.**
Slice E.6b added `sgcl --output PATH`, which opens the destination
file with explicit UTF-8 encoding from Python and writes directly.
Sample 15 (Run 6) was produced this way and all non-ASCII survives.

The defensive `\uXXXX` escapes in `synonyms.py` were reverted to
literal Unicode — they weren't fixing anything.

This finding also retroactively explained the "weird Greek/Latin
labels" in Calculator (`εá£`, `∩¥ö`, etc.). Those weren't real button
labels — they were Segoe Fluent Icons PUA codepoints garbled through
the same pipe. With `--output`, they come through as real PUA
codepoints (``, ``, …) that our icon-font policy can
recognize when we extend the map.

## Constraints discovered

- The walker still has `except Exception: pass` blocks around individual
  property accesses (label, bounds, pattern checks). Those are
  legitimate — UIA's COM interface throws on some property reads. Only
  the `GetChildren()` failure is logged because that's the one that
  hides subtree-shaped bugs.
- `confidence` is a Phase 1 *adapter* confidence. Phase 2 (FIND) will
  add a separate match confidence; we shouldn't conflate them.
- Pane flattening currently runs unconditionally. Some agents may want
  the raw tree for debugging. If that becomes a real ask, add
  `--no-flatten` to `inspect`. Don't add it until someone needs it.
- Calculator's `GroupControl` containers are not flattened (heuristic
  targets `PaneControl` only). If those start to feel like noise too,
  extend the heuristic with a `--flatten-groups` flag or auto-detect
  based on label/action presence.

## Assumptions killed

- "All the weird non-ASCII labels Calculator returned in Phase 0 are
  real text." **Killed** — many were mojibake from the same pipe issue,
  and the real labels were icon-font PUA codepoints.
- "If our Python source has literal Unicode, Windows Python will read
  it correctly." **Validated** (we verified it). The earlier defensive
  fix was unnecessary.
- "PowerShell `Tee-Object -Encoding utf8` produces correct UTF-8 from a
  child process's UTF-8 stdout." **Killed** — only when
  `[Console]::OutputEncoding` is also UTF-8 in the session.
  `sgcl --output PATH` is the safe pattern instead.

## Recommended next step

Phase 1 is done. The thesis holds: the normalized output is smaller,
more uniform, and more honest about its own confidence than the raw
UIA dump. Synonyms and icon-glyph descriptions give the agent
alternative ways to recognize the same control.

**Phase 2 (Find + Read) can begin** with:

1. Implement FIND queries: `role`, `label`, `label_contains`, `text`,
   `state`, `near`, `inside`. Match against both `label` and `synonyms`.
2. Implement READ for: text fields (use UIA `ValuePattern.Value`),
   Calculator's `NormalOutput` (use the `static_text` we already
   surface), and checkbox/radio state (use `TogglePattern`).
3. Ranked candidate results with `confidence` from the affordance plus
   a separate match-confidence. Ambiguous queries return all matches
   with parent/dialog context, not one silent guess.

GitHub issue #2 (`[blunt-win] Normalize`) can be closed against this
report.

Out-of-band follow-ups (do not block Phase 2):

- Extend `_ICON_NAMES` in `sgcl/core/icon_glyphs.py` to cover the 12
  codepoints we observed but don't yet name.
- Consider whether `GroupControl` should also be eligible for the
  pane-reduction heuristic.
- Document `--output PATH` as the recommended invocation in the README
  setup notes, with a brief note about why.
