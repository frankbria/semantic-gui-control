# Initial Use Cases

These are not user stories. They are minimal scenarios chosen because each one stresses a different part of the affordance pipeline and surfaces a different kind of failure.

## A. Notepad text entry

**Goal.**

- Focus or launch Notepad.
- Inspect the window.
- Find the editable document area.
- Type text.
- Verify the text is present in the editor.
- Save via menu invoke or hotkey.

**Why this matters.** Exercises window discovery, text input, hotkeys, and post-action verification. Notepad is the simplest possible "real" Windows app.

**Expected commands.**

```bash
sgcl windows
sgcl focus --window <notepad_wid>
sgcl inspect --window <notepad_wid>
sgcl find --window <notepad_wid> --role text_field
sgcl type --target <edit_id> --text "Hello SGCL"
sgcl verify --target <edit_id> --expect value_contains:"Hello SGCL"
sgcl hotkey ctrl+s
```

**Success criteria.** Text appears in editor; verifier confirms it; save dialog or save action observed.

## B. Calculator button interaction

**Goal.**

- Focus Calculator.
- Find numeric and operator buttons by label.
- Invoke a sequence (e.g., `2 + 3 =`).
- Read the result display.

**Why this matters.** Exercises button discovery, INVOKE patterns, and reading a non-text-field value.

**Expected commands.**

```bash
sgcl find --window <calc_wid> --role button --label "2"
sgcl invoke --target <btn_2_id>
sgcl find --window <calc_wid> --role button --label "+"
sgcl invoke --target <btn_plus_id>
sgcl find --window <calc_wid> --role button --label "3"
sgcl invoke --target <btn_3_id>
sgcl find --window <calc_wid> --role button --label "="
sgcl invoke --target <btn_eq_id>
sgcl read --target <result_display_id>
```

**Success criteria.** The result display reads "5". Each INVOKE returns a verification result.

## C. Save dialog

**Goal.**

- Trigger Save As.
- Detect that a dialog appeared.
- Find the filename field; type a filename.
- Find the Save button.
- Classify Save as `reversible` or `committing` depending on context (here: file exists already → `committing`).
- Invoke Save with appropriate approval.
- Verify the dialog closes and the file appears on disk.

**Why this matters.** Exercises multi-window / dialog state, context-sensitive risk, and verification beyond the UI (filesystem evidence).

**Expected commands.**

```bash
sgcl hotkey ctrl+shift+s
sgcl wait --for dialog_appears --timeout 5
sgcl find --role text_field --label-contains File
sgcl type --target <filename_field_id> --text "demo.txt"
sgcl find --role button --label Save
sgcl invoke --target <save_btn_id> --approve true
sgcl wait --for dialog_disappears --timeout 5
sgcl verify --expect file_exists:"demo.txt"
```

**Success criteria.** Dialog opened, was detected, was filled in, Save was confirmed as committing, the action was approved, the dialog closed, and the file exists.

## D. Ambiguous button labels

**Goal.**

- Inspect an app with multiple buttons that share or nearly share a label (e.g., multiple "Save" buttons, or "OK" appearing in nested dialogs).
- Return ambiguity instead of guessing.
- Use neighboring labels, hierarchy, and role to rank candidates.

**Why this matters.** Tests whether SGCL can refuse confident stupidity. Real apps have ambiguity. The pipeline must surface it.

**Expected commands.**

```bash
sgcl find --window <wid> --role button --label "OK"
# Expected: more than one match, each with confidence and parent context.
```

**Success criteria.** Returns all matches with distinguishing context (parent dialog title, nearby labels). Does not auto-pick one. INVOKE on a non-specific target is refused with a "disambiguate first" error.

## E. Broken or shallow accessibility tree

**Goal.**

- Point SGCL at an app whose accessibility implementation is incomplete (custom-drawn UI, Electron with missing aria, legacy app with generic `Pane` everywhere).
- Observe a degraded affordance graph.
- Confirm the system reports low confidence and missing labels honestly.
- Use repair / fallback paths: keyboard tab traversal, screenshot + OCR enrichment, coordinate-based interaction.

**Why this matters.** This is where the thesis is tested. If SGCL can only work on perfectly-instrumented apps, the project is not useful. Vision must be available as a spare tire.

**Expected commands.**

```bash
sgcl inspect --active --depth 3
# Affordances return with low confidence, missing labels, generic roles.

sgcl find --label-contains "Submit"
# May fail through accessibility; falls back to OCR/visual labeling.

sgcl invoke --target <best_candidate_id> --fallback ocr
```

**Success criteria.** SGCL does not silently invent semantics it cannot back up. Confidence drops appropriately. Fallback adapters are used explicitly, and the response reports which adapter actually executed.
