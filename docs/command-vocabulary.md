# Command Vocabulary

## Principle

The command vocabulary should be small, stable, boring, and platform-neutral.

It should describe what the agent wants to do, not how a specific operating system performs it.

## Minimum Viable Commands

```text
OBSERVE
FIND
READ
FOCUS
TYPE
INVOKE
SELECT
SCROLL
WAIT
VERIFY
ESCAPE
UNDO
```

## Example CLI Commands

```bash
gui windows
gui active
gui focus --window <window_id>
gui inspect --window <window_id> --depth 3
gui find --window <window_id> --role button --label Save
gui read --target <control_id>
gui focus-control --target <control_id>
gui type --target <control_id> --text "Hello world"
gui invoke --target <control_id>
gui hotkey ctrl+s
gui wait --for window_change --timeout 5
gui verify --expect text_contains:"Saved"
```

## Example JSON Request

```json
{
  "command": "find",
  "window_id": "window_3",
  "query": {
    "role": "button",
    "label_contains": "Save"
  }
}
```

## Example JSON Response

```json
{
  "status": "ok",
  "matches": [
    {
      "id": "control_17",
      "role": "button",
      "label": "Save",
      "enabled": true,
      "visible": true,
      "actions": ["focus", "invoke"],
      "risk": "reversible",
      "confidence": 0.94
    }
  ]
}
```

## Risk Classification

```text
safe: observe, inspect, read, focus, hover
reversible: open menu, select field, type draft text, scroll
committing: submit, send, delete, purchase, overwrite, finalize
unknown: action semantics unclear
```

## Design Note

An action such as `invoke(button: Save)` may map to different execution strategies:

1. Native accessibility invoke.
2. Keyboard shortcut.
3. Focus and Enter/Space.
4. Coordinate click based on bounds.
5. Vision-guided fallback.

The semantic action should remain the same even when the backend changes.
