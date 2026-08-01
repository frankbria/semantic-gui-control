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
- **Input:** a window target *plus* either `target_id` or a query selector. The window target is required — control ids are per-invocation (see `sgcl/core/adapter_base.py`), so READ must re-walk a specific window's tree to resolve one. There is no session state to infer the window from.
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
sgcl read --window <wid> --target <cid>
sgcl read --window <wid> --text "=" --role button   # or resolve by query
sgcl focus --target <cid>
sgcl type --target <cid> --text "Hello world"
sgcl invoke --target <cid>
sgcl hotkey ctrl+s          # shorthand for TYPE/keyboard, not a distinct verb
sgcl wait --for window_change --timeout 5
sgcl verify --expect text_contains:"Saved"
```

`hotkey` is a CLI convenience over keyboard input; the underlying vocabulary does not need a separate `HOTKEY` verb.

Every window-scoped subcommand — `inspect`, `find`, `read` — requires exactly one of `--active`, `--window`, `--process`, `--title`, `--pid`. `--active` is unreliable from a terminal, because the foreground window is usually the terminal itself; prefer `--process` or `--title`.

> Verbs below `read` in the block above (`focus`, `type`, `invoke`, `hotkey`, `wait`, `verify`) are **Phase 3 and not implemented**. They are specified here, not shipped.

## Response envelope

Every response is a JSON object carrying a `status`. An agent branches on that
one key rather than parsing prose.

**Success** — `status: "ok"`, plus the adapter origin and the command's payload:

```json
{ "status": "ok", "adapter": "windows_uia", "platform": "windows",
  "matches": [ ... ] }
```

**Failure** — `status: "error"`, a stable machine-readable `reason`, a human
`message`, and whatever context helps the agent recover. Exit code is non-zero.

Success and failure envelopes travel the same channel: **stdout**, or the file
named by `--output` when that flag is set. There is only ever one place to look
for the response. `--output` exists to bypass a host shell's stdout encoding
(see [`windows-claude-setup.md`](windows-claude-setup.md)); routing errors
around it would reintroduce exactly the corruption the flag avoids. Diagnostic
noise — adapter warnings, tracebacks — stays on stderr and is never part of the
envelope.

```json
{ "status": "error", "reason": "ambiguous_window",
  "message": "2 windows matched the given criteria",
  "candidates": [ { "id": "hwnd_111", "title": "Untitled - Notepad" },
                  { "id": "hwnd_333", "title": "notes - Notepad" } ] }
```

### Reason codes

| `reason` | Meaning |
|---|---|
| `window_not_found` | No window matched the targeting flags. |
| `ambiguous_window` | More than one window matched; `candidates` lists them. |
| `target_not_resolved` | The control could not be resolved to exactly one affordance — no match, several matches, or an unknown `--target` id. |
| `invalid_argument` | A flag value was out of range, or an id was malformed. |
| `target_and_selectors` | `--target` was combined with query selectors. |
| `missing_selector` | READ was given neither `--target` nor a selector. |

`status: "refused"` is reserved for Phase 3 risk refusals — see
[`risk-model.md`](risk-model.md). It is a distinct state from `error`: the
command was understood and deliberately not performed.

Argparse's own parse-time failures (unknown flag, missing required group) keep
argparse's prose output. Those happen before the JSON contract applies, and its
messages are better than anything a reason code would convey.

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
