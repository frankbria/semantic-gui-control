# GitHub Issues — Seed Bodies

Copy-paste these into GitHub issues for the first seven blunt wins. Each one follows the `blunt-win` issue template. Titles include the `[blunt-win]` prefix so the label/automation works.

---

## 1. `[blunt-win] Observe — structured JSON view of a live desktop`

**Goal.** Inspect live GUI windows and controls into structured JSON. List windows, identify the active window, dump the active window's control tree.

**Learning question.** Can we expose a real desktop GUI as structured text without screenshots?

**Scope.**

- `sgcl windows`
- `sgcl active`
- `sgcl inspect --active --depth N`
- Initial platform: Windows via UI Automation (`pywinauto`, `uiautomation`, or COM directly).

**Acceptance criteria.**

- [ ] `sgcl windows` returns title, process, pid, bounds, visible, active.
- [ ] `sgcl active` returns the foreground window.
- [ ] `sgcl inspect --active --depth N` returns a hierarchical JSON tree of controls with `id`, `role`, `label`, `enabled`, `visible`, `bounds`, `actions`, `children`.
- [ ] Output is JSON by default.
- [ ] Works against Notepad and Calculator.
- [ ] Spike note exists at `spikes/windows-observer-results.md`.

**Non-goals.** No clicking. No typing. No vision/OCR. No agent planner. No cross-platform implementation.

**Dependencies.** None.

---

## 2. `[blunt-win] Normalize — platform-neutral affordance graph`

**Goal.** Convert raw UIA trees into the normalized affordance model defined in `docs/affordance-model.md`.

**Learning question.** Can we hide UIA/AX/AT-SPI/DOM differences behind a common control/action schema?

**Scope.**

- Define v0 normalized role vocabulary.
- Map UIA `ControlType` → normalized role.
- Compute `actions` from UIA pattern availability.
- Move UIA-specific data to `raw_ref`.
- Assign coarse `confidence`.

**Acceptance criteria.**

- [ ] `docs/affordance-model.md` schema has no UIA-specific fields above `raw_ref`.
- [ ] Notepad and Calculator emit normalized affordance graphs.
- [ ] Normalized output is smaller and more uniform than the raw Phase 0 dump.
- [ ] Confidence is not uniformly 1.0; missing labels degrade it.
- [ ] Spike note at `spikes/normalize-results.md`.

**Non-goals.** No FIND. No execution. No second adapter.

**Dependencies.** Observe.

---

## 3. `[blunt-win] Find — semantic search over affordances`

**Goal.** Locate controls by role, label, text, state, and relationships instead of coordinates.

**Learning question.** Can an agent find the thing it means without knowing screen coordinates?

**Scope.**

- `sgcl find` with query fields: `role`, `label`, `label_contains`, `text`, `state`, `near`, `inside`.
- Ranked candidates with confidence.
- Multiple matches returned for ambiguous queries.

**Acceptance criteria.**

- [ ] FIND returns ranked candidates for Notepad and Calculator scenarios.
- [ ] Ambiguous queries return all matches with disambiguating context (parent label, dialog title, nearby text).
- [ ] No coordinate logic is needed for any of the example queries.
- [ ] Spike note at `spikes/find-read-results.md`.

**Non-goals.** No execution.

**Dependencies.** Normalize.

---

## 4. `[blunt-win] Read — extract state from controls`

**Goal.** Read value, state, selection, and visible text from any affordance that supports it.

**Learning question.** Can the system read enough state to support agent reasoning and verification?

**Scope.**

- `sgcl read --target <id>` returns `{ value, state, selection?, visible_text? }`.
- Returns `supported: false` honestly when no value is available.

**Acceptance criteria.**

- [ ] READ returns useful state for text fields and Calculator's display.
- [ ] READ aggregates visible text for labeled groups when no direct value exists.
- [ ] READ reports `supported: false` rather than guessing.

**Non-goals.** No execution.

**Dependencies.** Normalize, Find.

---

## 5. `[blunt-win] Act — execute low-risk actions`

**Goal.** Execute normalized actions through the affordance layer.

**Learning question.** Can we perform basic GUI actions through the affordance layer rather than directly through pixels?

**Scope.**

- Verbs: `FOCUS`, `TYPE`, `INVOKE`, `SELECT`, `SCROLL`, plus a `hotkey` CLI convenience.
- Response reports which backend path executed (native pattern, keyboard, accelerator, coordinate).

**Acceptance criteria.**

- [ ] Notepad text entry completes end-to-end via FOCUS + TYPE + hotkey.
- [ ] Calculator "2 + 3 =" completes end-to-end via INVOKE.
- [ ] Zero coordinate clicks are required for either flow.
- [ ] Each action's response names the backend that executed it.

**Non-goals.** Vision/OCR fallback. Second adapter. Full agent loop.

**Dependencies.** Read.

---

## 6. `[blunt-win] Verify — evidence for every action`

**Goal.** Every action returns a `verification` payload containing `before`, `after`, `diff`, `status`, and `evidence`.

**Learning question.** Can every action return evidence, not just "I clicked it"?

**Scope.**

- Status values: `success`, `failure`, `uncertain`.
- `uncertain` is first-class, not a synonym for success.

**Acceptance criteria.**

- [ ] Every Act-phase response includes a verification block.
- [ ] At least one honest test produces `uncertain` (a control whose post-action state cannot be re-read), and it is not labeled success.
- [ ] Verification diffs do not require coordinates.

**Non-goals.** Vision/OCR fallback for verification.

**Dependencies.** Act.

---

## 7. `[blunt-win] Risk — refuse to commit blind`

**Goal.** Classify actions by risk class and refuse `committing` and `unknown` actions without explicit approval.

**Learning question.** Can the system avoid becoming a blind automation monkey around Submit, Send, Delete, Purchase, Finalize, Pay, Transfer, Overwrite, Confirm?

**Scope.**

- Every affordance carries a `risk` class (`safe` / `reversible` / `committing` / `unknown`).
- Lexical classifier upgrades risk for affordances whose label matches the risky-verbs list.
- Context bumps risk (e.g., generic OK inside a "Delete file?" dialog → committing).
- INVOKE on committing/unknown affordances refuses unless `--approve` is passed.

**Acceptance criteria.**

- [ ] INVOKE on a "Send" / "Delete" / "Submit" labeled control refuses without `--approve`.
- [ ] Refusal payload is structured and includes the matched label and the required override.
- [ ] `--approve` lets the action proceed and verifier still returns the expected diff.
- [ ] At least one context bump is exercised (generic label upgraded by dialog title).

**Non-goals.** No machine-learned risk classifier yet — lexical + contextual is enough.

**Dependencies.** Verify.
