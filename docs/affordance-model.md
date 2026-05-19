# Affordance Model

The normalized affordance is the primary unit of the agent-facing interface. Every adapter must be able to produce affordances in this shape. Adapters may carry extra information on `raw_ref`, but `raw_ref` is not what the agent reasons over.

## Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Stable-within-session identifier for this affordance. Adapter-assigned; opaque to the agent. |
| `platform` | string | yes | `"windows"`, `"macos"`, `"linux"`, `"browser"`, etc. |
| `adapter` | string | yes | Name of the adapter that produced this affordance (e.g., `"windows_uia"`). |
| `role` | string | yes | Normalized role: `"window"`, `"button"`, `"text_field"`, `"checkbox"`, `"radio"`, `"menu"`, `"menu_item"`, `"list"`, `"list_item"`, `"tab"`, `"table"`, `"row"`, `"cell"`, `"dialog"`, `"notification"`, etc. |
| `label` | string \| null | yes | Best inferred human-facing label. May come from accessible name, nearby static text, placeholder, or tooltip. |
| `value` | string \| number \| bool \| null | no | Current readable value, when applicable. |
| `enabled` | bool | yes | Whether the control is interactive. |
| `visible` | bool | yes | Whether the control is currently visible on screen (or in viewport for DOM). |
| `focused` | bool | yes | Whether this control currently holds keyboard focus. |
| `bounds` | object \| null | no | `{ x, y, width, height }` in screen pixels (or page pixels for browser). Used for vision fallback and human debugging. |
| `parent_id` | string \| null | yes | The id of the parent affordance, or `null` for window-level. |
| `children` | string[] | yes | Ids of direct children. May be empty. |
| `actions` | string[] | yes | Supported normalized actions from the command vocabulary (e.g., `["focus", "invoke"]`). |
| `risk` | string | yes | One of `"safe"`, `"reversible"`, `"committing"`, `"unknown"`. See `risk-model.md`. |
| `confidence` | number | yes | 0..1. Adapter's confidence that this affordance was correctly identified, labeled, and classified. |
| `raw_ref` | object \| null | no | Adapter-specific debug payload (e.g., UIA AutomationId, ControlType, DOM selector). Not for agent reasoning. |

### Optional extensions

These appear when the adapter can provide them:

- `placeholder` — placeholder text on input fields.
- `description` — accessible description / help text.
- `state` — adapter-normalized state map (e.g., `{ checked: true, expanded: false }`).
- `selection` — current selection for lists, tables, text fields.
- `keyboard_shortcut` — accelerator, if exposed.
- `screen` / `monitor_id` — for multi-monitor environments.

## Example: button

```json
{
  "id": "ctrl_42",
  "platform": "windows",
  "adapter": "windows_uia",
  "role": "button",
  "label": "Save",
  "value": null,
  "enabled": true,
  "visible": true,
  "focused": false,
  "bounds": { "x": 980, "y": 612, "width": 80, "height": 28 },
  "parent_id": "ctrl_3",
  "children": [],
  "actions": ["focus", "invoke"],
  "risk": "reversible",
  "confidence": 0.94,
  "keyboard_shortcut": "Alt+S",
  "raw_ref": {
    "ControlType": "ButtonControlType",
    "AutomationId": "btnSave",
    "ClassName": "Button"
  }
}
```

## Example: text field

```json
{
  "id": "ctrl_88",
  "platform": "windows",
  "adapter": "windows_uia",
  "role": "text_field",
  "label": "Filename",
  "value": "untitled.txt",
  "enabled": true,
  "visible": true,
  "focused": true,
  "bounds": { "x": 320, "y": 480, "width": 360, "height": 24 },
  "parent_id": "ctrl_3",
  "children": [],
  "actions": ["focus", "type", "read"],
  "risk": "reversible",
  "confidence": 0.91,
  "placeholder": "Enter filename",
  "selection": { "start": 0, "end": 12 },
  "raw_ref": {
    "ControlType": "EditControlType",
    "AutomationId": "txtFilename",
    "ClassName": "Edit"
  }
}
```

## Why raw trees are available but not primary

A raw UIA / AX / AT-SPI tree is huge, full of duplicates, full of structural panels that the user never sees as such, and uses different vocabulary on every platform. If the agent reasons directly over it, three things happen:

1. The agent's prompts balloon and reasoning quality drops.
2. The agent's logic accidentally encodes platform-specific assumptions.
3. The system silently becomes Windows-only, then later "Windows with some Mac mode if we get to it."

The normalized affordance graph forces every adapter to make the same shape of object available. Raw trees remain accessible for debugging via `raw_ref` and via an explicit "dump native tree" command, but they are not the surface the agent plans against.
