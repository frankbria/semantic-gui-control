# Phase 1: Normalize Spike

After Phase 0, we have UIA trees from real Windows apps and a clear picture
of how much normalization is actually needed. Phase 1 turns the raw walk
into a normalized affordance graph that is smaller, more uniform, and
honest about its own confidence.

## Goal

Produce a normalized affordance graph from the Windows UIA adapter output
that conforms to `docs/affordance-model.md` and contains no UIA-specific
fields above `raw_ref`. The output should also be (a) **smaller** than the
raw Phase 0 dump after structural noise is removed, and (b) **honest**
about confidence and about what was thrown away.

## Learning question

> Can we hide UIA / AX / AT-SPI / DOM differences behind a common
> control/action schema?

## What Phase 0 already proved

These are validated facts, not assumptions:

- UIA `ControlTypeName` values map cleanly to a normalized role vocabulary
  for the apps we tested. ButtonControl, EditControl, DocumentControl,
  TextControl, MenuItemControl, etc. all mapped without loss.
- UIA pattern availability is reliable enough to derive `actions`. The
  `GetInvokePattern()` / `GetValuePattern()` / etc. approach works.
- Accessible `Name` is usually populated for the controls an agent cares
  about. Where it is empty, nearby static text often supplies meaning
  (e.g., Notepad's status bar exposes cursor/length/encoding as separate
  static_text nodes).
- `bounds` are reportable in physical screen coordinates with per-monitor
  DPI awareness. Multi-monitor negative-x coordinates work.
- Walking depth-8 trees completes in well under a second for the apps
  tested. No performance work is needed yet.

These were Phase 0 assumptions; treat them as background, not as risks
to re-test.

## What Phase 0 surfaced as new work

Documented in detail at `spikes/windows-observer-results.md`. The six
concrete asks for Phase 1:

1. **Smarter walker** — fixed `--depth` is too crude. Notepad's
   interactive layer is at depth 2–3; Calculator's keypad is at depth 7+.
   The walker should keep going through unlabeled structural panes and
   stop at semantically meaningful subtrees, instead of cutting based on
   a single integer.
2. **Icon-font label policy** — WinUI labels routinely contain Private
   Use Area codepoints from Segoe Fluent Icons. We need to decide:
   strip, preserve, or render a description (e.g.,
   `""` → `"<icon: hamburger>"`). Preserve raw for `raw_ref`;
   surface a `description` when we can map the glyph.
3. **System-surfaces filter** — `Taskbar`, `Program Manager`, and other
   shell windows currently leak into `sgcl windows`. Add an
   `is_system_surface` marker and have `sgcl windows` exclude them by
   default, with `--include-system` to opt in.
4. **Walker exception logging** — `GetChildren()` failures are currently
   swallowed. Phase 0 took two runs to confirm Warp's empty tree was
   Warp-specific and not a bug. Log to stderr (or a `--debug` flag).
5. **Label synonyms** — Calculator names buttons "Zero" / "Plus" / etc.,
   not `"0"` / `"+"`. Agents prompted with literal symbols will miss.
   Emit a `synonyms` list so FIND in Phase 2 can match both surfaces.
6. **Structural pane reduction** — 12 unlabeled `pane` controls in one
   Notepad tree is noise. The normalizer should flatten chains of
   unlabeled single-child panes upward, preserving them in `raw_ref` if
   anyone cares.

## Scope

Implement, in this order. Each item is independently mergeable.

### 1.1 — Schema additions

Add to `Control`:

- `confidence: float` — 0..1. Computed from signal availability (clean
  label + role + at least one action = 1.0; missing label or generic
  role downgrades).
- `description: str | None` — populated by the icon-glyph map (item 1.3)
  when a label is just a PUA codepoint. Optional otherwise.
- `synonyms: list[str]` — alternative labels. Empty for most controls;
  populated by item 1.5.

Add to `WindowInfo`:

- `is_system_surface: bool` — `True` for Taskbar / Program Manager /
  known shell windows; `False` otherwise.

### 1.2 — Walker exception logging + system-surface filter

- Replace `except Exception: pass` on `GetChildren()` with a logged
  exception (stderr, with the control's id and ControlTypeName).
- Tag known system windows in `WindowInfo` and have `sgcl windows`
  default to excluding them. Add `--include-system` flag.

### 1.3 — Icon-font handling

- Maintain a small static map of PUA codepoints → human description for
  Segoe Fluent Icons. Start with the handful we observe in Notepad and
  Calculator dumps; extend as we see more.
- Populate `description` when the label consists only of glyphs in the
  map. Keep the raw label intact.

### 1.4 — Structural pane reduction

- Walker post-process: collapse chains of unlabeled `pane` controls
  that have exactly one child. The grandchild becomes the parent of the
  retained branch. Original collapsed panes recorded in `raw_ref`
  (`flattened: ["ctrl_3", "ctrl_5"]`) for debugging.

### 1.5 — Label synonyms

- Static map for Calculator's word-named buttons: "Zero" → "0", "One"
  → "1", "Plus" → "+", "Minus" → "−" / "-", "Multiply by" → "*" / "×",
  "Divide by" → "/" / "÷", "Equals" → "=", "Decimal separator" → ".".
- Phase 1 just emits them; Phase 2 (Find) consumes them.

### 1.6 — Spike report

Write `spikes/normalize-results.md`:

- Size comparison: raw Phase 0 control count vs normalized count for
  Notepad and Calculator.
- Confidence histogram: how many controls landed at each confidence
  tier? Is the distribution sensible?
- Which UIA roles mapped cleanly, which were dropped or coerced.
- Any new questions raised for Phase 2 (Find) or Phase 9 (Cross-Platform
  Adapter Contract).

## Out of scope

- Semantic FIND across the graph (Phase 2).
- READ of complex values (Phase 2).
- Any execution.
- A second adapter. The point of Phase 1 is to design the contract;
  Phase 9 (Cross-Platform Adapter Contract) is where we *prove* it with
  a second backend.

## Exit criteria

- [ ] `Control` has `confidence`, `description`, `synonyms`. `WindowInfo`
      has `is_system_surface`. No UIA-specific field at the schema level.
- [ ] Notepad and Calculator emit normalized affordance graphs with the
      new fields populated meaningfully.
- [ ] The Phase 0 raw dump and the Phase 1 normalized output for the
      same scene can be diffed; the normalized output is **smaller** and
      **more uniform** (structural panes collapsed, system windows
      filterable, icon labels described).
- [ ] Confidence scores are present and **not uniformly 1.0**. Apps with
      missing names or generic roles show measurably lower confidence.
- [ ] Walker exceptions are logged to stderr, not swallowed.
- [ ] Calculator's "Zero" / "Plus" / etc. buttons emit `synonyms: ["0",
      "+", ...]` etc.
- [ ] A short report at `spikes/normalize-results.md` captures size,
      confidence distribution, mapping decisions, and new questions.

## Main risks

- The normalized schema becomes a thin rename of UIA, and we won't
  notice until Phase 9 lights it on fire. (Mitigation: drive design
  from what an agent would want to query, not from what UIA happens to
  expose.)
- We over-design synonyms / descriptions based on two apps. Keep both
  maps small and easy to extend; don't ship a 1000-entry map.
- The pane-flattening pass loses something a future verifier needs.
  Mitigation: keep flattened ids in `raw_ref`.
- Confidence scoring becomes a vibes-based number with no calibration.
  Mitigation: keep the heuristic explicit and documented; revisit when
  Phase 2 (Find) has actual feedback signal.
