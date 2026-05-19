# Phase 1: Normalize Spike

After Phase 0, we have a raw-ish JSON dump of UIA trees from Notepad and Calculator. Phase 1 turns that into a normalized affordance graph that does not reek of UIA.

## Goal

Produce a normalized affordance graph from the Phase 0 adapter output that conforms to `docs/affordance-model.md` and contains no UIA-specific fields above `raw_ref`.

## Learning question

> Can we hide UIA / AX / AT-SPI / DOM differences behind a common control/action schema?

## Assumptions to validate (carried over from Phase 0)

Phase 0 should leave us with hard evidence (or contradictions) for the following. Phase 1 cannot proceed honestly until they are checked:

- UIA `ControlType` values can be mapped onto the normalized `role` vocabulary in a way that is not lossy for Notepad and Calculator.
- UIA pattern availability (`InvokePattern`, `ValuePattern`, `TogglePattern`, `SelectionPattern`, etc.) is reliable enough to derive the normalized `actions` list.
- Accessible `Name` is usually populated. When it is not, nearby static text is recoverable as a label.
- `bounds` are reportable in screen coordinates consistently across DPI settings and multi-monitor setups.
- Walking the tree to the depths needed for these apps completes in acceptable time.

If any of these are false, the Phase 1 design changes. Note in the Phase 0 spike report which ones held.

## Scope

- Define the v0 normalized `role` vocabulary explicitly. Start with: `window`, `dialog`, `menu`, `menu_item`, `toolbar`, `button`, `text_field`, `checkbox`, `radio`, `tab`, `list`, `list_item`, `table`, `row`, `cell`, `static_text`, `image`, `group`.
- Implement a mapping function `windows_uia` → normalized affordance.
- Move adapter-specific data into `raw_ref`.
- Compute `actions` from supported UIA patterns.
- Assign a coarse `confidence` (e.g., 1.0 when accessible name + role + patterns are all clean; lower when fields are missing or inferred).
- Emit the normalized graph as JSON.

## Out of scope

- Semantic FIND across the graph (Phase 2).
- READ of complex values (Phase 2).
- Any execution.
- A second adapter. The point of Phase 1 is to design the contract; Phase 9 (Cross-Platform Adapter Contract) is where we *prove* it with a second backend.

## Exit criteria

- [ ] `docs/affordance-model.md` has not gained any UIA-specific field at the schema level. Every UIA-specific bit lives under `raw_ref`.
- [ ] Notepad and Calculator both emit normalized affordance graphs.
- [ ] The Phase 0 raw dump and the Phase 1 normalized output for the same scene can be diffed; the normalized output is smaller and more uniform.
- [ ] Confidence scores are present and not all 1.0. Apps with missing names show lower confidence.
- [ ] A short report at `spikes/normalize-results.md` captures: which UIA roles mapped cleanly, which were lossy, what was thrown away, and any new questions raised for Phase 9.

## Main risks

- The normalized schema becomes a thin rename of UIA, and we will not notice until Phase 9 lights it on fire.
- We over-design the schema based on two apps that happen to be well-instrumented.
- Action inference is wrong (something looks invokable but isn't, or vice versa) and we don't catch it because Phase 1 has no execution.
