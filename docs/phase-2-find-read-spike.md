# Phase 2: Find + Read Spike

After Phase 1, we have a normalized affordance graph. Phase 2 makes it queryable and readable, without executing anything.

## Goal

Implement semantic FIND and READ against the normalized affordance graph for the first adapter.

## Learning question

Two, actually:

> Can an agent find the thing it means without knowing screen coordinates?
>
> Can the system read enough state to support agent reasoning and verification?

## Scope

### FIND

```bash
sgcl find --window <wid> --role button --label-contains Save
sgcl find --window <wid> --role text_field
sgcl find --window <wid> --near <other_id> --role button
sgcl find --window <wid> --text "untitled.txt"
```

Query fields supported in v0:

- `role`
- `label` (exact)
- `label_contains` (case-insensitive substring)
- `text` (visible text anywhere in/under the affordance)
- `state` (e.g., `enabled`, `focused`, `checked`)
- `near <id>` (parent / sibling proximity)
- `inside <id>` (descendant of)

Result is a ranked list of normalized affordances, each with a `confidence` reflecting both adapter confidence and match quality. Ambiguous matches return multiple candidates with distinguishing context (parent label, dialog title, nearby text), not one.

### READ

```bash
sgcl read --target <id>
```

Returns:

- `value` for text fields, combos, sliders, etc.
- `state` map (e.g., `{ checked: true, expanded: false }`).
- `selection` for selectable lists and text fields.
- `visible_text` aggregated from descendants when the affordance is a labeled group with no explicit value.
- `supported: false` when the adapter cannot read this affordance's value.

## Out of scope

- Any execution (FOCUS, TYPE, INVOKE, SELECT, SCROLL). Phase 3.
- A second adapter. Phase 9.
- Stateful daemons / sessions. The CLI can re-walk the tree per call.

## Acceptance criteria

- [ ] FIND returns ranked candidates for the Notepad and Calculator use cases.
- [ ] Ambiguous queries return all matches with parent / dialog context attached, not one silent guess.
- [ ] READ returns useful state for text fields, checkboxes (if any in our test apps), and Calculator's result display.
- [ ] READ reports `supported: false` honestly when it cannot extract a value.
- [ ] No coordinate-based logic is required to make any of the example queries succeed.
- [ ] A spike note at `spikes/find-read-results.md` documents which queries worked, which were brittle, and which controls refused to expose value.

## Main risks

- Real apps have many controls with the same label. The ranking model is fragile.
- READ surfaces lies — UIA's `Value.Value` can be stale on some controls.
- Visible-text aggregation pulls in unrelated text from nearby panels.
- "Near" / "inside" semantics drift if the affordance graph has structural panels the user never sees as such.
