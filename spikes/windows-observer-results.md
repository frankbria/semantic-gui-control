# Windows Observer Spike — Results

> Template. Fill in as Phase 0 progresses. Do not delete unanswered sections — leave them blank if not yet known and note why.

## Date

YYYY-MM-DD

## Environment

- OS / build:
- Python / language and version: Python (>=3.11; dev box runs 3.12)
- UIA library and version: `uiautomation` (Yinkaisheng) — chosen for Phase 0 because it sits close to raw UIA primitives, which suits read-only tree dumping; we can revisit at Phase 3 (Act) if its execution ergonomics become limiting.
- Display config (monitors, DPI, scaling):
- Elevated or non-elevated session:

> Windows dev environment confirmed available (local / VM / dual boot / remote — fill in specifics here when Phase 0 starts).

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
