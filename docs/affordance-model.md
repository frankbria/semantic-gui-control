# Affordance Model

The normalized affordance is the primary unit of the agent-facing interface. Every adapter must be able to produce affordances in this shape. Adapters may carry extra information on `raw_ref`, but `raw_ref` is not what the agent reasons over.

## Schema

This table is the contract, and it is kept in step with
`Control.to_dict()` in [`sgcl/core/schema.py`](../sgcl/core/schema.py).
Every key below is emitted on every affordance, in this order. Nothing is
emitted that is not listed here.

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `id` | string | shipped | Identifier for this affordance, unique within one invocation. Adapter-assigned and opaque to the agent. **Not stable across invocations** — ids are re-issued on each walk, so an id from a previous `inspect` cannot be handed to a later `read`. |
| `parent_id` | string \| null | shipped | Id of the enclosing affordance; `null` at the root. Makes the graph traversable upward without re-walking. |
| `role` | string | shipped | Normalized role from the vocabulary below. |
| `native_role` | string | shipped | The adapter's own type name (e.g. `"ButtonControl"`). **Non-normative debug data** — see "Deliberate deviations". Agents should branch on `role`. |
| `label` | string \| null | shipped | Best inferred human-facing label. From the accessible name today; nearby static text and placeholders are not yet consulted. |
| `description` | string \| null | shipped | Human-readable gloss where the label alone is unusable — currently icon-font glyphs, rendered as `"icon: ChevronDown"`. `null` otherwise. |
| `synonyms` | string[] | shipped | Alternative labels an agent may query with (Calculator names a button `"Pi"`; `synonyms` carries `"π"`). Empty list when none apply. |
| `enabled` | bool | shipped | Whether the control is interactive. |
| `visible` | bool | shipped | Whether the control is on screen. Derived from the inverse of UIA's `IsOffscreen`. |
| `focused` | bool | shipped | Whether this control holds keyboard focus. |
| `bounds` | object \| null | shipped | `{ x, y, width, height }` in screen pixels. Degenerate `0,0,0,0` rectangles are emitted as-is rather than nulled — offscreen controls routinely report them. |
| `actions` | string[] | shipped | Supported verbs from [`command-vocabulary.md`](command-vocabulary.md), inferred from available patterns (e.g. `["focus", "invoke"]`). |
| `confidence` | number | shipped | 0..1. The **adapter's** confidence that role/label/actions were read correctly. Distinct from a FIND match score — see [`command-vocabulary.md`](command-vocabulary.md). |
| `children` | object[] | shipped | Directly nested child affordances. Objects, not ids — see "Deliberate deviations". Empty list at a leaf. |
| `raw_ref` | object \| null | shipped | Adapter-specific debug payload (UIA `ControlTypeName`, `ClassName`, `AutomationId`, `LocalizedControlType`; `flattened` when panes were collapsed; `role_unmapped` when the native type had no role mapping). Not for agent reasoning. |
| `value` | — | Phase 3 | Current readable value. Today this is returned by `sgcl read` as a separate result, not carried on the affordance. |
| `risk` | — | Phase 3 | One of `"safe"`, `"reversible"`, `"committing"`, `"unknown"`. Specified in [`risk-model.md`](risk-model.md); lands with execution, per the phase rule that Act ships with Risk. |

`platform` and `adapter` are **not** affordance fields. They are emitted
once per response, alongside `status`, because they are constant for a whole
graph and repeating two strings across a 500-control tree is bloat with no
added information:

```json
{ "status": "ok", "adapter": "windows_uia", "platform": "windows", "...": "payload" }
```

Every command's payload is a JSON object for this reason — `sgcl windows`
returns `{"windows": [...]}` and `sgcl active` returns `{"window": {...}}`
rather than a bare array or a bare `null`.

## Role vocabulary

The normalized `role` is what an agent branches on. The Windows UIA adapter
maps 42 native control types onto 41 distinct roles:

| Normalized `role` | UIA `ControlTypeName` |
|---|---|
| `app_bar` | `AppBarControl` |
| `button` | `ButtonControl` |
| `calendar` | `CalendarControl` |
| `checkbox` | `CheckBoxControl` |
| `combo` | `ComboBoxControl` |
| `custom` | `CustomControl` |
| `dialog` | `DialogControl` |
| `document` | `DocumentControl` |
| `group` | `GroupControl` |
| `header` | `HeaderControl` |
| `header_item` | `HeaderItemControl` |
| `image` | `ImageControl` |
| `link` | `HyperlinkControl` |
| `list` | `ListControl` |
| `list_item` | `ListItemControl` |
| `menu` | `MenuControl` |
| `menu_bar` | `MenuBarControl` |
| `menu_item` | `MenuItemControl` |
| `pane` | `PaneControl` |
| `progress_bar` | `ProgressBarControl` |
| `radio` | `RadioButtonControl` |
| `row` | `DataItemControl` |
| `scroll_bar` | `ScrollBarControl` |
| `semantic_zoom` | `SemanticZoomControl` |
| `separator` | `SeparatorControl` |
| `slider` | `SliderControl` |
| `spinner` | `SpinnerControl` |
| `split_button` | `SplitButtonControl` |
| `static_text` | `TextControl` |
| `status_bar` | `StatusBarControl` |
| `tab` | `TabControl` |
| `tab_item` | `TabItemControl` |
| `table` | `TableControl`, `DataGridControl` |
| `text_field` | `EditControl` |
| `thumb` | `ThumbControl` |
| `title_bar` | `TitleBarControl` |
| `toolbar` | `ToolBarControl` |
| `tooltip` | `ToolTipControl` |
| `tree` | `TreeControl` |
| `tree_item` | `TreeItemControl` |
| `window` | `WindowControl` |

`table` is the one collision: UIA distinguishes `TableControl` from
`DataGridControl`, and the distinction has not yet earned a separate role.
`native_role` preserves it if you need it.

A native type **not** in this table normalizes to `unknown` — the native
string is never passed through into `role`, because `role` is the field that
has to mean the same thing on every platform. When that happens the
affordance carries `raw_ref["role_unmapped"] = true` and the adapter warns
once per distinct type on stderr, so the gap is visible in the output and in
the logs rather than silently mimicking a real role.

### `document` vs `text_field` — read this one

This is the most expensive role confusion in the project's own evidence
(`spikes/find-read-results.md`, [`open-questions.md`](open-questions.md)).
An agent looking for "the text area" reaches for `text_field` and finds
nothing.

- **`text_field`** is UIA's `EditControl` — a single- or multi-line input
  box. Dialog fields, address bars, search boxes.
- **`document`** is UIA's `DocumentControl` — a rich text surface. **Notepad's
  main editing area is a `document`, not a `text_field`.** So are most
  editors, browsers' page bodies, and word processors.

Query for both when you mean "somewhere I can type". The two are not
merged because they genuinely differ in what patterns they support, and
collapsing them would lose that.

The four roles that dominate real output — `pane`, `group`, `static_text`,
`document` — are structural or read-only. An agent that only knows about
buttons and text fields will find most of a real tree unrecognizable, which
is why the full vocabulary is published here rather than a curated subset.

## Specified but not implemented

These are named in the design and are **not emitted by any adapter today**.
They are listed so a second-adapter author knows they are reserved, not
forgotten. Do not write a consumer that expects them.

- `placeholder` — placeholder text on input fields. No adapter reads it yet;
  `label` falls back to the accessible name instead.
- `state` — adapter-normalized state map (e.g. `{ checked: true, expanded: false }`).
  Toggle and expand state is currently only inferable from `actions`.
- `selection` — current selection for lists, tables, and text fields.
  `sgcl read` returns selection information in its own result shape instead.
- `keyboard_shortcut` — accelerator, where exposed.
- `screen` / `monitor_id` — for multi-monitor environments. `bounds` is in
  virtual-desktop coordinates, so multi-monitor setups are currently
  ambiguous about which display a control is on.

`description` was on this list and has since shipped; it is in the schema
table above.

## Deliberate deviations

Places where the implementation knowingly differs from an earlier version of
this document. Recorded rather than silently reconciled, so the reasoning
survives.

### `children` holds objects, not ids

This document previously specified `children: string[]` — ids into a flat
`{id: affordance}` map, traversable in both directions. The code emits
nested objects, and that is the version being kept.

Nesting is what every consumer already expects, it is what the 20 committed
samples under `spikes/samples/` contain, and the upward link the flat model
existed to provide is now served by `parent_id`. A flat map would be worth
revisiting if a consumer needed random access by id across a whole graph —
`_find_in_tree` and `_build_parent_map` both hand-roll traversal today — but
that is an indexing convenience, buildable in a few lines by any consumer,
not a contract change.

### `native_role` stays, and the Phase 1 exit criterion was wrong

[`phase-1-normalize-spike.md`](phase-1-normalize-spike.md) set an exit
criterion of "no UIA-specific field at the schema level". `native_role`
holds a raw UIA `ControlTypeName`, which is also present in
`raw_ref["ControlTypeName"]` — so by that criterion it should be dropped.

It is kept, and the exit criterion is amended instead. Two reasons:

1. It is the field you actually want when a role mapping is wrong, and
   during Phase 0/1 spike work that was constant. Making debugging go
   through `raw_ref` adds friction to the exact task the field serves.
2. Removing it is a required-positional-argument change touching 12 test
   call sites for no behavioral gain.

The cost is honest and bounded: `native_role` is **non-normative**. A
macOS adapter would put an `AXRole` there and a browser adapter a tag name.
Nothing in the core may branch on it, and an agent that does has coupled
itself to one platform. The cross-platform guarantee lives on `role`.

## Worked examples

Both are real nodes from
[`spikes/samples/15-calculator-phase1-clean-d8.json`](../spikes/samples/15-calculator-phase1-clean-d8.json),
captured from Windows Calculator. The committed samples predate `parent_id`,
so that key is filled in here from the node's actual position in the tree;
everything else is verbatim.

### A button carrying a synonym

Calculator names this button `"Pi"`. An agent looking for `"π"` would miss it
on label alone, which is what `synonyms` exists to fix.

```json
{
  "id": "ctrl_51",
  "parent_id": "ctrl_13",
  "role": "button",
  "native_role": "ButtonControl",
  "label": "Pi",
  "description": null,
  "synonyms": ["π"],
  "enabled": true,
  "visible": true,
  "focused": false,
  "bounds": { "x": 1649, "y": 627, "width": 76, "height": 44 },
  "actions": ["focus", "invoke"],
  "confidence": 1.0,
  "children": [
    {
      "id": "ctrl_52",
      "parent_id": "ctrl_51",
      "role": "static_text",
      "native_role": "TextControl",
      "label": "",
      "description": null,
      "synonyms": [],
      "enabled": true,
      "visible": true,
      "focused": false,
      "bounds": { "x": 1677, "y": 640, "width": 18, "height": 18 },
      "actions": ["read"],
      "confidence": 0.75,
      "children": [],
      "raw_ref": {
        "ControlTypeName": "TextControl",
        "ClassName": "TextBlock",
        "LocalizedControlType": "text"
      }
    }
  ],
  "raw_ref": {
    "ControlTypeName": "ButtonControl",
    "ClassName": "Button",
    "AutomationId": "piButton",
    "LocalizedControlType": "button"
  }
}
```

The nested `ctrl_52` is not decoration — it is what a real tree looks like.
A button that renders its face as a child `static_text` is the WinUI norm,
and it is why `children` holding objects rather than ids matters in practice:
the agent sees the whole button in one payload. Its `confidence` of 0.75
reflects a missing `AutomationId`, the one signal of four it lacks.

### A static text whose label is an icon glyph

The label is `U+E70D`, a private-use codepoint from Segoe MDL2 Assets. It
is a chevron in that font and unrenderable garbage everywhere else.
`description` carries the glyph's name so the affordance is describable at
all.

```json
{
  "id": "ctrl_43",
  "parent_id": "ctrl_40",
  "role": "static_text",
  "native_role": "TextControl",
  "label": "",
  "description": "icon: ChevronDown",
  "synonyms": [],
  "enabled": true,
  "visible": true,
  "focused": false,
  "bounds": { "x": 1712, "y": 596, "width": 15, "height": 15 },
  "actions": ["read"],
  "confidence": 0.75,
  "children": [],
  "raw_ref": {
    "ControlTypeName": "TextControl",
    "ClassName": "TextBlock",
    "LocalizedControlType": "text"
  }
}
```

The `label` above holds the literal codepoint, which most editors render as
a box or nothing at all. This is precisely what `--output` exists to
protect — see [`command-vocabulary.md`](command-vocabulary.md).

The `0.75` is worth reading carefully: it is docked for the missing
`AutomationId`, **not** for the useless label.
[`score_control`](../sgcl/core/confidence.py) counts a label as populated
when it is non-empty, and a private-use glyph is non-empty — so an
icon-only control scores as though it were well-labeled. `description` is
the mitigation. The scoring gap is real and currently unfixed.

Note what is absent from both: no `value`, no `risk`, no `platform`, no
`adapter`. The first two are Phase 3; the last two are response-level.

## Why raw trees are available but not primary

A raw UIA / AX / AT-SPI tree is huge, full of duplicates, full of structural panels that the user never sees as such, and uses different vocabulary on every platform. If the agent reasons directly over it, three things happen:

1. The agent's prompts balloon and reasoning quality drops.
2. The agent's logic accidentally encodes platform-specific assumptions.
3. The system silently becomes Windows-only, then later "Windows with some Mac mode if we get to it."

The normalized affordance graph forces every adapter to make the same shape of object available. Raw trees remain accessible for debugging via `raw_ref` and via an explicit "dump native tree" command, but they are not the surface the agent plans against.
