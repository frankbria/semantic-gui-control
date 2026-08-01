# ADR 0006: The Agent Integration Surface Is the CLI Now and MCP Later

## Status

Accepted. Revisit when Win 10 measures per-invocation cost, or earlier if
Phase 3 forces session state (see triggers).

## Context

The daemon was a stated product goal that the active roadmap silently
dropped. [`level-1-spec.md`](../level-1-spec.md) names the MVP objective as
"a **daemon and CLI**";
[`architecture-overview.md`](../architecture-overview.md) says agents consume
the CLI "(or, later, a daemon API)"; `CLAUDE.md` lists the daemon protocol as
undecided. But it appears in no win in
[`roadmap-blunt-wins.md`](../roadmap-blunt-wins.md). When the blunt-win
roadmap replaced the legacy sequence, the daemon fell off the plan without
anyone deciding to drop it.

Today the only integration path is shelling out to `sgcl` and parsing
stdout. Every invocation starts a Python interpreter, constructs an adapter,
and re-walks the whole window tree
([`ADR-0005`](ADR-0005-per-invocation-control-ids.md)). Win 10 asks whether an
LLM can complete a task through this surface, which is where the cost of that
becomes observable rather than theoretical.

### The tension, and why it is smaller than it looks

The obvious objection is that a daemon means session state, which collides
with ADR-0005 (per-invocation ids, no session state) and pre-empts the Phase 3
snapshot-caching question that
[`handoff-phase-3-planning.md`](../handoff-phase-3-planning.md) says to
"decide deliberately".

That objection applies to a *stateful* daemon. It does not apply to the
protocol choice. **Transport and statefulness are orthogonal.** A thin MCP
server over the existing `Adapter` can be exactly as stateless as the CLI —
each tool call re-walks, exactly as each CLI invocation does. What it removes
is subprocess startup and stdout parsing, not the re-walk.

Separating those two questions is most of this decision.

## Decision

**1. The CLI remains the reference surface and the contract.** It is what
`command-vocabulary.md` specifies, what the tests exercise, and what every
document describes. Any other surface is a binding over it, not a competitor
to it.

**2. When a programmatic surface is built, it is MCP.** Not REST, not
JSON-RPC. The thesis is exposing GUIs to LLM agents, and MCP is the protocol
whose object model — tools with typed schemas, called directly by the model —
matches the command vocabulary one-to-one. REST or JSON-RPC would put a
hand-written binding between every client and a vocabulary that is already
shaped like tool calls. `open-questions.md` had already noted MCP as
"appealing for agent use"; this makes that a choice.

**3. Its first form is stateless** — a thin wrapper over `Adapter`,
preserving ADR-0005. No session cache, no stable ids, no snapshot store.

**4. It is not built before Phase 3 lands.** Phase 3 decides whether
verification needs snapshot caching. Building a stateless server and then
retrofitting state is worse than waiting one phase for the answer.

**5. The stateful daemon is rejected for now.** Not forever — it is the
natural home for snapshot caching and stable ids if Phase 3 concludes it
needs them. But nothing today justifies owning cache invalidation.

This closes the question as a decision rather than an omission, which was the
point. It also declines to build anything, which is the honest scope.

## Consequences

- **Win 10 runs over the CLI.** That is a real constraint on it, and it is
  also the most useful thing about it: Win 10 becomes the measurement that
  tells us whether per-invocation cost is a genuine problem or an assumed
  one. No number exists today.
- Subprocess-per-command remains the agent's cost until then. On the trees
  measured so far (a few hundred controls) nothing suggests it is painful,
  but nothing has measured latency at all.
- `Adapter` is the seam an MCP server would sit on. This decision creates an
  obligation to keep it that way — the CLI must not accumulate logic that a
  second consumer would have to reimplement.
  [`ADR-0001`](ADR-0001-cross-platform-core-windows-first-spike.md)'s
  layering rule already points this direction; extracting read-resolution
  into `sgcl/core/resolve.py` was an instance of it.
- The `status` / `reason` envelope becomes more valuable, not less: it is
  already the shape an MCP tool result wants, so the CLI and a future server
  return the same thing.
- Deferring means Phase 3 may make the choice implicitly. The revisit
  triggers below exist to prevent that; if Phase 3 caches snapshots, this ADR
  is superseded, not quietly ignored.

## Alternatives considered

- **CLI only, permanently.** Simplest and defensible while there is one
  consumer. Rejected as a *permanent* answer because it makes the project's
  own thesis awkward to exercise: "expose GUIs to LLM agents" via
  subprocess-and-parse works, but no agent framework wants it.
- **Stateful daemon now.** Enables snapshot caching and stable ids, which
  Phase 3 might want. Rejected as premature: it is the largest change
  available, it contradicts a decision made three phases ago, and it would be
  made before the evidence that motivates it exists.
- **REST.** Most generic, most tooling. Wrong shape — every client writes a
  binding to turn endpoints back into tool calls.
- **JSON-RPC.** Simplest to implement, and MCP is JSON-RPC underneath. Choosing
  raw JSON-RPC would mean writing the tool-description layer by hand, which is
  the part MCP already standardizes.

## Revisit triggers

- **Phase 3 concludes verification needs snapshot caching.** That is the
  first session state in the project, and it changes point 3 and probably
  point 5. This ADR is superseded at that moment, not amended.
- **Win 10 measures per-invocation cost and finds it material** — the trigger
  this decision is designed around. A measured number replaces the current
  guess in either direction.
- **A second adapter (Win 9)** makes process startup dominate, e.g. a browser
  adapter that must launch or attach to a browser per invocation. That would
  make a warm process valuable for reasons unrelated to ergonomics.
- **An agent framework integration is attempted** and the CLI proves to be
  the blocker rather than the model or the vocabulary.
