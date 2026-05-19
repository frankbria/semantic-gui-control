# Blunt-Win Roadmap

This is not a PRD. It is a sequence of learning milestones. Each one is **coarse**, intentionally.

## The rule

Each blunt win must produce at least one of:

1. **A working capability** — something the system can now do that it could not do before.
2. **A documented constraint** — a real limit we did not know about until we tried.
3. **A killed assumption** — a belief we held going in that turned out to be wrong.

If a win produces none of those, it is not a win. It is busywork.

## The roadmap

| # | Win | Goal | Learning question | Example commands / artifacts | Exit criteria | Dependencies | Main risk |
|---|-----|------|-------------------|------------------------------|---------------|--------------|-----------|
| 1 | **Observe** | Inspect live GUI windows and controls into structured JSON. | Can we expose a real desktop GUI as structured text without screenshots? | `sgcl windows`, `sgcl active`, `sgcl inspect --active --depth 3` | JSON dump of Notepad and Calculator window trees with role, label, enabled, bounds. Spike note in `spikes/`. | None. | UIA returns shallow or unstable trees on some apps. |
| 2 | **Normalize** | Convert raw platform-specific UI trees into a compact normalized affordance model. | Can we hide UIA/AX/AT-SPI/DOM differences behind a common control/action schema? | Affordance JSON conforming to `docs/affordance-model.md`. | Same scenes from Phase 0 render through the normalized schema with no UIA-specific fields leaking. | Observe. | The schema becomes a thin rename of UIA. |
| 3 | **Find** | Locate controls semantically by role, label, text, state, or relationship instead of coordinates. | Can an agent find the thing it means without knowing screen coordinates? | `sgcl find --role button --label-contains Save` | Returns ranked candidates with confidence; ambiguous matches return all, not one. | Normalize. | Real apps have many same-labeled controls; ranking is fuzzy. |
| 4 | **Read** | Extract values and visible state from discovered controls. | Can the system read enough state to support agent reasoning and verification? | `sgcl read --target <id>` returns value, state, selection, visible text. | Read works for text fields, checkboxes, radios, list selection, status text. | Find. | Some controls expose no readable value via accessibility. |
| 5 | **Act** | Execute low-risk normalized actions: focus, type, invoke, hotkey, select, scroll. | Can we perform basic GUI actions through the affordance layer rather than directly through pixels? | `sgcl focus`, `sgcl type`, `sgcl invoke`, `sgcl select`, `sgcl scroll`, `sgcl hotkey` | Notepad text entry and Calculator button presses work end-to-end through the affordance layer with zero coordinate clicks. | Read. | Some controls only respond to coordinate input or synthesized keystrokes. |
| 6 | **Verify** | Compare before/after observations and report whether an action worked. | Can every action return evidence, not just "I clicked it"? | Each command response carries `verification: {before, after, diff, status}`. | Status of every action is `success`, `failure`, or `uncertain`, with the observation diff that justifies it. | Act. | Some state changes are not observable through the available adapter. |
| 7 | **Risk** | Classify actions by risk and block/escalate committing actions. | Can the system avoid becoming a blind automation monkey around Submit, Send, Delete, Purchase, Finalize, Pay, Transfer, Overwrite, Confirm? | Risk class on every affordance; default policy refuses committing actions without explicit approval. | An attempt to `invoke` a button labeled "Send" or "Delete" without approval returns refused-with-reason, not a click. | Verify. | Risk classifier is too noisy or too permissive. |
| 8 | **Repair & Fallback** | Use keyboard probing, escape/undo, screenshots, OCR, and coordinate fallback when semantic automation fails. | Can the system recover from broken or incomplete accessibility trees? | Vision/OCR adapter, escape-stack, undo path, focus-probing routines. | At least one scenario where the semantic adapter fails but the fallback completes the task and reports which layer succeeded. | Act, Verify. | OCR fallback gets seductive and starts being used as the default. |
| 9 | **Cross-Platform Adapter Contract** | Validate that at least one non-Windows backend can produce the same normalized model. | Did we build a real abstraction, or did we merely rename Windows UIA? | A second adapter — Linux AT-SPI, macOS AX, or browser DOM — passes the same observe/find/read contract tests as the Windows UIA adapter. | The contract test suite runs against two adapters with the same expectations and the same JSON shape. | Normalize, Read. | First adapter's schema bleed forces a second-pass refactor. |
| 10 | **Agent Loop** | Let an LLM use the command interface to complete a tiny task through structured state only. | Can an agent use SGCL tools without special pleading or vision-first control? | An LLM completes a Notepad or Calculator task by emitting SGCL commands and reading SGCL responses. | A small recorded end-to-end run with no screenshots in the agent prompt. | Verify, Risk. | The agent needs more context than the structured surface gives; we are pushed back to vision. |

## Sequencing logic

Wins 1 through 4 are sense-only. Wins 5 through 7 introduce execution and safety. Win 8 adds the safety net underneath. Win 9 is the real test of the abstraction. Win 10 is the validation that everything underneath actually composes into an agent-usable surface.

If Win 9 reveals the model is Windows-shaped, the right response is to refactor the schema, not to declare adapter parity by force.
