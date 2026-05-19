# Phase 3: Act + Verify + Risk Spike

Phases 0–2 are sense-only. Phase 3 is where SGCL starts changing the world. Risk and verification land in the same phase as execution because executing without them is exactly the failure mode the project exists to avoid.

## Goal

Execute low-risk normalized actions through the affordance layer, return verification evidence for every action, and enforce a risk policy that refuses to commit blind.

## Learning questions

> Can we perform basic GUI actions through the affordance layer rather than directly through pixels?
>
> Can every action return evidence, not just "I clicked it"?
>
> Can the system avoid becoming a blind automation monkey around Submit, Send, Delete, Purchase, Finalize, Pay, Transfer, Overwrite, Confirm?

## Scope

### Act

Implement these verbs against the first adapter:

- `FOCUS`
- `TYPE`
- `INVOKE`
- `SELECT`
- `SCROLL`
- `hotkey` (CLI convenience over keyboard input)

Each execution must report which backend path was used (native pattern, focus+key, accelerator, coordinate click, fallback). Coordinates are allowed *only* if the adapter exposes them on the affordance — they are never re-derived from the agent's prompt.

### Verify

Every command response carries:

```json
{
  "verification": {
    "before": { ...affordance snapshot... },
    "after":  { ...affordance snapshot... },
    "diff":   { ...field-level changes... },
    "status": "success" | "failure" | "uncertain",
    "evidence": "..."
  }
}
```

- `success`: the diff matches the expected effect (e.g., TYPE changed `value`).
- `failure`: no observable change, or a change inconsistent with the expected effect.
- `uncertain`: the adapter cannot confirm because the affordance cannot be re-read post-action.

`uncertain` is a first-class status, not a synonym for `success`.

### Risk

Implement the risk policy from `docs/risk-model.md`:

- Every affordance has a `risk` class assigned at normalize time.
- Lexical classifier upgrades affordances whose label matches the risky verbs list.
- Context bumps risk: a generic "OK" inside a dialog titled "Delete file?" becomes `committing`.
- `INVOKE` on a `committing` or `unknown` affordance is refused unless `--approve` is passed (CLI) or `approve: true` is set (API).
- Refusals return structured JSON with the reason and required override.

## Out of scope

- Vision / OCR fallback. That is Phase 8 (Repair & Fallback). Phase 3 must succeed on Notepad and Calculator with no pixel paths.
- Cross-adapter parity. Phase 9.
- A full LLM agent loop. Phase 10.

## Acceptance criteria

- [ ] Notepad text entry use case completes end-to-end via FOCUS + TYPE + hotkey, with verification evidence on each step.
- [ ] Calculator "2 + 3 =" use case completes end-to-end via INVOKE, with READ confirming the result.
- [ ] An INVOKE on a label matching the risky-verbs list refuses without `--approve`, and the refusal includes the matched label and the required override.
- [ ] Approval flows succeed when `--approve` is passed and the verifier still returns the expected diff.
- [ ] Each action's response names the backend path that executed (e.g., `"backend": "uia.invoke_pattern"`).
- [ ] `uncertain` is observed at least once in honest testing (some control that does not expose post-action state) and is *not* labeled as success.

## Risk policy for the phase itself

- Use disposable test files. The Save use case (use case C) goes against a scratch directory.
- Do not test risky-verb refusal on a real Send/Delete/Pay button in a real app. Build a tiny test surface (a button literally labeled "Submit" in a throwaway app) for that case, or use Notepad's "Don't Save" prompt as the natural committing example.
- All Phase 3 runs should be done in a session that can be killed without losing real work.

## Main risks

- TYPE works through keyboard synthesis only and reports success even when focus was elsewhere.
- Verification's diff looks identical for "succeeded" and "modal popped up and was dismissed."
- Risk classifier is too noisy and refuses legitimate `reversible` actions, or too permissive and lets committing actions through.
- The first action to actually invoke something destructive is unrecoverable. Plan the failure modes before the first `--approve`.
