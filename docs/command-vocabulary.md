# Command Vocabulary

The command vocabulary is intentionally small, stable, and boring. It describes what an agent wants to do, not how a particular OS performs it. If a verb is not plausibly platform-neutral, it does not belong here.

## Standard commands

```
OBSERVE   FIND     READ     FOCUS
TYPE      INVOKE   SELECT   SCROLL
WAIT      VERIFY   ESCAPE   UNDO
```

## Per-command contract

### OBSERVE

- **Purpose:** Capture the current observable state of a window, region, or the whole environment.
- **Input:** Optional `window_id`, `target_id`, or `scope: "active" | "all"`. Optional `depth`.
- **Output:** A normalized affordance graph (see `affordance-model.md`) plus a timestamp and adapter origin.
- **Risk:** `safe`.

### FIND

- **Purpose:** Locate affordances matching a semantic query (role, label, text, state, relationships).
- **Input:** `window_id` (or active), `query` object with fields like `role`, `label`, `label_contains`, `text`, `state`, `near`, `inside`.
- **Output:** Ranked list of matching affordances with `confidence`. Ambiguity returns multiple matches, not one.
- **Risk:** `safe`.

### READ

- **Purpose:** Extract value, state, selection, or visible text from a specific affordance.
- **Input:** `target_id`.
- **Output:** `{ value, state, selection?, visible_text? }`. Adapter-specific if the value type does not fit the standard fields.
- **Risk:** `safe`.

### FOCUS

- **Purpose:** Move keyboard focus to a control without otherwise interacting.
- **Input:** `target_id`.
- **Output:** Verification result showing focus moved.
- **Risk:** `safe`.

### TYPE

- **Purpose:** Enter text into a focusable text-accepting affordance.
- **Input:** `target_id` (or assume current focus), `text`, optional `mode: "append" | "replace"`.
- **Output:** Verification result with the new value (or the diff if value is not readable).
- **Risk:** `reversible`. Becomes `committing` only if it triggers immediate commit (rare).

### INVOKE

- **Purpose:** Trigger the affordance's primary action — typically clicking a button, activating a menu item, toggling a checkbox.
- **Input:** `target_id`.
- **Output:** Verification result. If the affordance's risk is `committing`, the engine refuses unless `approve: true` is set.
- **Risk:** Inherits from the affordance: `safe`, `reversible`, `committing`, or `unknown`.

### SELECT

- **Purpose:** Choose one or more items from a list, combo, tab, tree, or table row.
- **Input:** `target_id`, `value` or `index` or `text`.
- **Output:** Verification result reflecting the new selection.
- **Risk:** `reversible`.

### SCROLL

- **Purpose:** Scroll a scrollable affordance.
- **Input:** `target_id`, `direction: "up" | "down" | "left" | "right" | "to"`, optional `amount` or `to_target_id`.
- **Output:** Verification result. May include new visible content.
- **Risk:** `safe`.

### WAIT

- **Purpose:** Block until a condition is observed or a timeout fires.
- **Input:** `condition` (e.g., `appears`, `disappears`, `value_equals`, `window_change`), `timeout_ms`.
- **Output:** `{ status: "satisfied" | "timeout" | "error", evidence }`.
- **Risk:** `safe`.

### VERIFY

- **Purpose:** Assert a condition against the current state and return evidence.
- **Input:** `expect` (e.g., `text_contains`, `state_equals`, `exists`, `not_exists`, `value_equals`).
- **Output:** `{ status: "success" | "failure" | "uncertain", evidence }`.
- **Risk:** `safe`.

### ESCAPE

- **Purpose:** Try to back out of the current dialog, menu, or focused state. Used during repair.
- **Input:** Optional `levels` (default 1).
- **Output:** Verification of resulting focus and window stack.
- **Risk:** `reversible`. May close dialogs without saving.

### UNDO

- **Purpose:** Issue the application's undo action (Ctrl+Z or platform equivalent) where possible.
- **Input:** None or `target_window_id`.
- **Output:** Verification of state change. May report `uncertain` if the app does not expose undo state.
- **Risk:** `reversible`. Note that some apps treat undo as `committing` (e.g., destructive undo in version control UIs); the risk classifier should override per-context.

## Example CLI usage

```bash
sgcl windows
sgcl active
sgcl inspect --active --depth 3
sgcl find --window <wid> --role button --label-contains Save
sgcl read --target <cid>
sgcl focus --target <cid>
sgcl type --target <cid> --text "Hello world"
sgcl invoke --target <cid>
sgcl hotkey ctrl+s          # shorthand for TYPE/keyboard, not a distinct verb
sgcl wait --for window_change --timeout 5
sgcl verify --expect text_contains:"Saved"
```

`hotkey` is a CLI convenience over keyboard input; the underlying vocabulary does not need a separate `HOTKEY` verb.

## Example JSON request

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

## Example JSON response

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

## Design note: one verb, many backends

`INVOKE button:Save` may execute as:

1. Native accessibility invoke pattern.
2. Focus + Enter/Space.
3. Application-specific keyboard accelerator.
4. Coordinate click using the affordance's `bounds`.
5. Vision-guided fallback (last resort).

The semantic verb does not change. The execution path the engine picked is reported in the response so the agent (and the human) can see what actually happened.
