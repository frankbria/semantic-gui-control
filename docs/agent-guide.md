# Agent Guide

How to drive `sgcl` without guessing. This covers **strategy**; `sgcl <cmd>
--help` covers flags.

Everything here is verified against the code or a committed capture under
[`spikes/`](../spikes/). Where a claim comes from a measurement, the numbers
are real.

> This describes what the tool does **today**. Some of it is surprising, and
> a few of those surprises are open design questions rather than settled
> behaviour — those are marked.

---

## 1. Use `--text`. `--label` is stricter than it looks.

**`--label` is exact-match and does not reach synonyms.** This is the single
most expensive surprise in the project's own logs
(`spikes/find-read-results.md`), and it reproduces today:

```
--label "="                  -> 0 matches
--text  "="                  -> 1 match:  'Equals' @ 0.90
```

Calculator's button is *named* `"Equals"`. The `"="` lives in its `synonyms`,
and only `--text` searches there.

`--text` tries four surfaces in order and takes the first hit
(`_score_text` in `sgcl/core/matcher.py`):

| Surface | `match_confidence` |
|---|---|
| exact label | 1.00 |
| any synonym | 0.90 |
| description (icon-glyph name) | 0.85 |
| label substring | 0.70 |

So **reach for `--text` first**, and narrow later. `--label` is for when you
already know the exact accessible name and want nothing else.

> **Open:** whether `--label` *should* also check synonyms is Phase 3
> question 1 ([`open-questions.md`](open-questions.md)). This guide describes
> today's behaviour; it does not argue for it.

## 2. Pair `--text` with `--role`.

`--text` alone is broad by design, and on a real tree that shows:

```
--text "0"                   -> 5 matches; the button you meant ranks 3rd
--text "0" --role button     -> 1 match:  'Zero'
```

Measured against the committed Calculator capture
(`spikes/samples/f7-b2-find-zero-by-text.json`). The four non-buttons are the
display panes and status text, all legitimately labelled `"0"`.

One role filter turns an ambiguous result into an unambiguous one. It is the
cheapest thing you can do.

## 3. Notepad's editor is a `document`, not a `text_field`.

`--role text_field` returns **zero** against Notepad. Its editing surface is
UIA's `DocumentControl`, normalized to `document`.

- **`text_field`** — a single- or multi-line input box. Dialog fields,
  address bars, search boxes.
- **`document`** — a rich text surface. Editors, browser page bodies, word
  processors.

Query for both when you mean "somewhere I can type". The full 42-entry role
table is in [`affordance-model.md`](affordance-model.md).

Two related things worth knowing:

- The roles that dominate real output are `pane`, `group`, `static_text` and
  `document` — structural or read-only. An agent that only knows `button` and
  `text_field` will find most of a tree unrecognizable.
- A native type with no mapping normalizes to `role: "unknown"` and carries
  `raw_ref.role_unmapped: true` (`sgcl/adapters/windows_uia/_walker.py`). If
  you get `unknown`, check that flag — it distinguishes "the adapter couldn't
  classify this" from "this control genuinely has no type".

## 4. Two different confidences.

Do not conflate these. They answer different questions.

| Field | Question |
|---|---|
| `match_confidence` | How well did **your query** match this control? |
| `control.confidence` | How well did **the adapter** read this control? |
| `combined_rank` | Their product. The sort key. |

`control.confidence` is four binary signals at 0.25 each: a populated label,
a specific role, at least one inferred action, and a **stable identifier**
([`ADR-0002`](decisions/ADR-0002-adapter-confidence-scoring.md)).

**`0.75` is the common case, not a defect.** It almost always means no
`AutomationId` — `spikes/normalize-results.md` records exactly that. Win32
and other legacy apps routinely omit it. Do not treat 0.75 as "probably the
wrong control".

One known gap: `score_control` counts a private-use icon glyph as a populated
label, so an icon-only control scores as though it were well-labelled. Its
`description` is the thing to read instead.

## 5. Every window-scoped command needs a target, and `--active` is a trap.

`inspect`, `find` and `read` each require **exactly one** of `--active`,
`--window`, `--process`, `--title`, `--pid`. Supplying none or several is a
`missing_selector` / argparse error, not a default.

**`--active` is unreliable from a terminal**: the foreground window is
usually the terminal running `sgcl`, not the application you meant
(`spikes/windows-observer-results.md` Run 1). Prefer `--process` or
`--title`.

Shell surfaces — taskbar, Program Manager — are hidden from `sgcl windows` by
default. `--include-system` shows them
([`ADR-0004`](decisions/ADR-0004-system-surface-filtering-default.md)).

## 6. `ctrl_N` ids die when the command exits.

Ids are assigned by a counter during one walk. They are **valid only within
the invocation that produced them**
(`sgcl/core/adapter_base.py`, [`ADR-0005`](decisions/ADR-0005-per-invocation-control-ids.md)).

Storing an id and reusing it in a later command is the mistake to avoid. It
may error — or, worse, silently resolve to a *different* control, because a
re-walk after the tree changed reassigns the numbering.

**Re-query by selector instead.** FIND returns the whole affordance — label,
role, synonyms, `parents`, and `raw_ref.AutomationId` — precisely so you can
re-find the control without depending on an id. `--target` exists for
chaining inside a single fresh walk and is documented as fragile.

## 7. FIND returns everything. READ demands exactly one.

They differ on purpose:

- **FIND** returns *all* candidates, ranked. Multiple matches are a valid
  answer — the matcher never silently picks one
  (`sgcl/core/matcher.py`). Use `parents` to disambiguate two
  identically-labelled controls.
- **READ** resolves to exactly one control or fails. Zero matches and five
  matches both raise, with `reason: "target_not_resolved"` and a message
  naming the count (`sgcl/core/resolve.py`).

So a READ that errors with "5 controls matched" is telling you to add a
`--role` or an `--inside`, not that anything is broken.

## 8. Read the envelope, not the prose.

Every response carries a `status`:

```json
{"status": "ok", "adapter": "windows_uia", "platform": "windows", "matches": [...]}
{"status": "error", "reason": "ambiguous_window", "message": "...", "candidates": [...]}
```

Branch on `reason`, never on message text. The codes are tabled in
[`command-vocabulary.md`](command-vocabulary.md). `ambiguous_window` includes
the candidate list so you can pick one and retry without a second round trip.

On Windows, prefer `sgcl --output FILE` over shell redirection — PowerShell's
default encoding mangles non-ASCII labels in a pipe. The whole response,
errors included, goes to that file.

---

## The shortest version

```bash
sgcl windows                                          # what is open
sgcl find --process notepad.exe --text "Save" --role button
sgcl read  --process notepad.exe --role document      # not text_field
```

Use `--text`. Add `--role`. Never reuse an id. Branch on `reason`.
