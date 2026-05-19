# Risk Model

Every executable affordance carries a risk class. The execution engine applies a default policy based on that class, and an agent or user can override per-call.

## Risk classes

### `safe`

Observation, inspection, and movement that does not change application or system state.

Examples:

- Listing windows.
- Inspecting a window's control tree.
- Reading a field's value.
- Moving keyboard focus.
- Hovering.
- Scrolling.

### `reversible`

Changes state in a way that can be undone with no externally-visible consequence.

Examples:

- Typing draft text into an editor that has not been saved.
- Selecting a tab.
- Opening a menu.
- Selecting an item in a list.
- Toggling an unsubmitted checkbox.
- Pressing Cancel.

### `committing`

Performs an externally-visible or destructive action that is hard or impossible to reverse.

Examples:

- Clicking Send, Submit, Pay, Transfer, Purchase, Finalize, Confirm.
- Clicking Delete, Discard, Overwrite.
- Closing an unsaved document with Don't Save.
- Confirming a destructive dialog.
- Posting publicly.

### `unknown`

The control's effect cannot be inferred with reasonable confidence. The label is ambiguous, the role is generic (e.g., a custom `Pane`), or the adapter could not classify it.

Examples:

- A button with no accessible label and only an icon child.
- A control whose label is the literal text "OK" inside a dialog whose purpose is not observable from the affordance graph alone.
- A web `<div role="button">` with no aria-label and unreadable inner text.

## Default policy

| Class | Default policy |
|-------|----------------|
| `safe` | Execute automatically. No prompt. |
| `reversible` | Execute under normal agent control. Logged. |
| `committing` | **Refuse by default.** Require explicit approval — either an `approve: true` flag on the command, an interactive confirmation, or a policy override allowing the specific action in the current session. |
| `unknown` | Refuse to execute. Prefer to OBSERVE / READ / FIND nearby first. If the agent insists, treat as `committing` for safety. |

The engine should return a structured refusal, not a silent no-op:

```json
{
  "status": "refused",
  "reason": "risk_class_committing",
  "affordance_id": "ctrl_42",
  "label": "Send",
  "required": "explicit_approval"
}
```

## Risky labels and verbs

The classifier should mark any affordance whose label matches (case-insensitive, word-boundary) one of the following as at least `committing` until explicitly overridden:

```
Send       Submit      Delete      Purchase
Finalize   Pay         Transfer    Overwrite
Confirm    Discard     Remove      Wipe
Post       Publish     Share       Buy
Charge     Withdraw    Sign        Authorize
```

These verbs are not exhaustive. The classifier should be tunable; users can add app-specific risky labels.

## Per-context overrides

Risk is not purely lexical. The same label means different things in different surfaces:

- "Save" in a draft editor → `reversible`.
- "Save" in a billing form → `committing`.
- "OK" in a confirmation dialog whose title is "Delete file?" → `committing` regardless of the OK label.

The classifier should consider:

1. The affordance's label.
2. The enclosing window title and dialog context.
3. Nearby static text (e.g., warnings).
4. Adapter-provided semantics (UIA `IsRequiredForForm`, ARIA `aria-confirm`, etc., when available).

When in doubt, the system upgrades risk, not downgrades it.

## Verification interaction

Risk and verification are linked. A `committing` action that succeeds without producing a verifiable state change is suspicious — the click may have landed in the wrong place, or the action may have failed silently. The verifier should flag this and the agent should not assume success.
