# Initial Use Cases

## Use Case A: Text Editor Entry

Goal:

- Open or focus a basic text editor.
- Inspect window.
- Find editable document area.
- Type text.
- Verify text exists.
- Save via hotkey or menu command.

Why this matters:

- Tests window discovery, text input, hotkeys, and verification.

## Use Case B: Calculator Interaction

Goal:

- Focus calculator.
- Find numeric and operator buttons.
- Invoke buttons semantically.
- Read result.

Why this matters:

- Tests button discovery, invoke patterns, and structured interaction.

## Use Case C: Save Dialog

Goal:

- Trigger Save As.
- Detect dialog.
- Find filename field.
- Type filename.
- Find Save button.
- Classify Save as reversible or committing depending context.
- Invoke Save.
- Verify dialog closes or file appears.

Why this matters:

- Tests multi-window/dialog state and semi-risky actions.

## Use Case D: Ambiguous Button Labels

Goal:

- Inspect an app with multiple similar buttons.
- Return ambiguity instead of guessing.
- Use neighboring labels, hierarchy, and role to rank candidates.

Why this matters:

- Tests whether the framework can avoid confident stupidity.
