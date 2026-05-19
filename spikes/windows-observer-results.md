# Windows Observer Spike — Results

> Template. Fill in as Phase 0 progresses. Do not delete unanswered sections — leave them blank if not yet known and note why.

## Date

YYYY-MM-DD

## Environment

- OS / build:
- Python / language and version:
- UIA library and version:
- Display config (monitors, DPI, scaling):
- Elevated or non-elevated session:

## Apps tested

- [ ] Notepad
- [ ] Calculator
- [ ] (Stretch) other:

## Commands run

```bash
sgcl windows
sgcl active
sgcl inspect --active --depth 1
sgcl inspect --active --depth 3
# others...
```

## What worked

- ...

## What failed

- ...

## Raw observations

Notes, snippets of JSON output, anything worth keeping for posterity. Trim later.

```text

```

## Surprises

Things that were not predicted by the planning docs. These are the most valuable entries — they tend to be where future bugs and design decisions hide.

- ...

## Constraints discovered

Real limits the spike exposed. Add to `docs/open-questions.md` if any of these need decisions.

- ...

## Assumptions killed

Beliefs we held going into Phase 0 that turned out to be wrong. List explicitly.

- ...

## Recommended next step

What Phase 1 (Normalize) should do or not do, based on what this spike showed.

- ...
