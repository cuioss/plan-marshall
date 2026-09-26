# PLAN-01: Instruction-conformance harness seam

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision relayed by `review-apparatus-001`; row status `parked`).** `plan-marshall-mcp` replaces both the process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted as rows `01.*` to `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/instrumentation-substrate-carry-over.md` as PM-MCP input. **Do NOT emit; un-park only by explicit operator decision.** The body below is kept intact as the evidence chain.

epic: instrumentation-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Build the minimum runnable seam that turns a documented workflow rule into a testable proposition: a
scenario fixture, a dispatch of that scenario into an isolated agent context, and a verdict saying
whether the rule held — reported with the population it was scored over and with an honest third
state for "could not be scored". Prove it end-to-end on exactly **one** rule. The point of this plan
is the seam, not coverage; PLAN-02 supplies coverage once the format exists.

The rule under test must be one whose violation is mechanically observable from the transcript or the
resulting tool calls — not one whose compliance is a matter of taste — because a verdict that needs a
human to adjudicate it is not a signal this repository can act on.

## Deliverables

1. A scenario fixture format: the rule under test, the situation, the pressure applied, and the
   mechanically-checkable observation that decides the verdict. Stored under the new skill's own
   directory; no new top-level tree.
2. A runner script following `pm-plugin-development:plugin-script-architecture`, returning TOON,
   dispatching one scenario through an `execution-context-{level}` leaf and scoring the result.
3. A three-valued verdict — `held` / `violated` / `indeterminate` — where every count rides with the
   population it was computed over, and an unscoreable run resolves to `indeterminate` and never to
   `held`.
4. One authored scenario, end to end, over a rule chosen by the criterion in the Objective.
5. Unit tests for the runner and the scorer, with the dispatch seam faked; no live agent call in the
   test suite.
6. ⛔ **A stated cost ceiling for a conformance run, fixed at design time.** Folded from inbox
   `next-level-005`. This deliverable is non-negotiable and is the one that may not be deferred: this
   repository has already built a verification layer whose cost was not bounded at design time, and it
   consumed **81% of a 13.9M-token run** (PLAN-TRUTH-089, self-review ×19, all 17 loop-backs exhausted,
   not converged) and **48.5%** of another (PLAN-PR-046, 6.77M tokens). A conformance harness is another
   verification layer. It carries its ceiling by design or it reproduces that outcome at corpus scale.

## Folded findings

Three inbox messages were folded into this spec during the 2026-09-14 drain. Each adds a constraint, not
a file surface.

- **`next-level-001` — an axis vocabulary to cross-check against, not to adopt.** An outside course
  whitepaper offers five eval-scoring axes: task success, tool-use quality, trajectory compliance,
  hallucination, response quality. ⛔ **Not a set to adopt.** Its use is negative-space: if this plan's
  verdict design scores nothing resembling any of them, that deserves a stated reason rather than being
  an oversight. The same message carries a line worth keeping — *"an eval without a clear rubric measures
  nothing"* — which is the vacuous-guard archetype stated as a principle and sits beside ADR-019 rather
  than replacing anything in it.
- **`next-level-005` — the cost ceiling, now deliverable 6 above.**
- **`next-level-007` — three design constraints on the verdict shape, and one unnamed deliverable.**
  An eval is structurally different from a test in three ways that each bind here: it is
  **baseline-relative** (did behaviour regress against a recorded baseline) rather than absolute; it
  fires on a **tolerance band** rather than a threshold flip, because a pass/fail assertion on a
  probabilistic system produces a flapping signal; and it **tolerates ordering variance**, so a
  trajectory check demanding one exact tool-call sequence fails a correct run that reached the same state
  by another order. ⭐⭐ **The decision this forces, and forces early:** our shape is a three-valued
  verdict publishing its population; theirs is a scored judgment inside a tolerance band. They are
  compatible — `held` / `violated` / `indeterminate` over a scored margin rather than over a boolean —
  but **which layer carries the three values must be decided in this plan, not retrofitted later.**
  ⛔ And an LLM-as-judge scoring every run is itself a model call per evaluated unit, which is deliverable
  6's problem restated: a scored-judgment design needs its ceiling specified at design time.

⚠ All three messages are outside documents carrying **no data** for their claims. They are recorded as
independent arrival, vocabulary, and design constraint — never as evidence that this plan should be
built, re-scoped, or re-ordered.

## Claim Labels

- OBSERVED: No adversarial or pressure-scenario testing of instruction prose exists anywhere in the
  inventoried tree — `architecture search --content --pattern "pressure.test|adversarial.scenario|sunk.cost" --ignore-case`
  returned `count: 0` with `unreadable: 0`, `truncated: false`, `elided: 0`, so the coverage is clean
  and the zero is a derived negative rather than an absence of looking. Re-measured at `main`
  `7d82d5d90` (cleanup 2026-09-22): `files_scanned: 3097` (was `5462` at original staging — the
  inventory shrank; the zero holds over the current population, re-derive rather than citing either
  count as current).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: architecture search re-run: count 0, files_scanned 3097 (was 5462), coverage clean, zero holds
- OBSERVED: The repository asserts, without deriving it, that its hard rules "exist because Claude
  regularly violates them despite softer guidance" — read at `CLAUDE.md` § "Workflow Discipline (Hard
  Rules)". This sentence is the proposition this plan makes testable.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md hard-rule opening sentence unmodified at HEAD, quoted verbatim
- OBSERVED: A dispatch vehicle with a pinned model and effort already exists and does not need
  inventing — the `execution-context-{level}` agent family. ⛔ **Citation corrected at cleanup
  2026-09-22**: the level-variant contract lives at `marketplace/bundles/plan-marshall/agents/
  execution-context.md` (frontmatter `implements: …/ext-point-dynamic-level-executor`) and
  `platform-runtime/standards/contract.md` § subagent dispatch, not at
  `persona-plan-marshall-agent/SKILL.md`, which mentions the envelope only in passing and documents no
  level variants.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: execution-context.md + platform-runtime/standards/contract.md confirm the vehicle; citation corrected in spec text
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** A dispatched `execution-context-{level}` leaf
  can be given a scenario prompt that does NOT load the rule's own skill, so compliance is attributable
  to the instruction under test rather than to a second copy of it arriving through the persona chain.
  Contradicted at `marketplace/bundles/plan-marshall/agents/execution-context.md` § "Step 2: Load
  Foundational Practices (IMPLICIT)" (`persona-plan-marshall-agent` loads unconditionally, and its own
  `## Hard Rules (never override)` section restates several always-binding rules by name) AND
  independently by first-hand observation: the harness re-supplies the whole of `CLAUDE.md` as system
  context inside a dispatched leaf. **Consequence, absorbed into this spec's scope**: true
  attribution-isolated compliance is achievable only for a rule that is NOT already duplicated in the
  always-loaded base context (`CLAUDE.md` hard rules, `persona-plan-marshall-agent/SKILL.md` § Hard
  Rules, `standards/tool-usage-patterns.md`). Deliverable 4's rule-selection criterion (Objective) is
  narrowed accordingly: for a rule that IS already duplicated there, the harness scores
  **compliance-under-realistic-context** — a still-useful but different signal — and the verdict must
  say which of the two it measured. Outline picks the first scenario's rule and states which case
  applies; the isolation confound is a known, absorbed constraint rather than an open question.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: execution-context.md unconditional persona load + first-hand observation of CLAUDE.md re-supplied in a dispatched leaf; spec re-scoped to attribution-isolated vs realistic-context compliance
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** `manage-findings` can store a conformance
  verdict WITHOUT a schema change. Contradicted at `manage-findings/SKILL.md` § "Finding Types": the
  type vocabulary is a closed 12-value enum and the resolution vocabulary a closed 6-value enum, neither
  carrying `held`/`violated`/`indeterminate` or a population field; the store is also plan-scoped
  (`--plan-id` required, `add` refuses an absent plan directory), so a free-standing conformance run has
  no store to write to. **Consequence, absorbed into this spec's scope**: deliverable 3's verdict is
  reported from the runner's own TOON output only — this spec's stated fallback branch is now the ONLY
  branch, and the findings schema is not touched by this plan under any outcome.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: manage-findings/SKILL.md closed type/resolution enums, no verdict/population field, plan-scoped store; spec's fallback (TOON-only) is now the sole branch, Expected Surface entry removed
- Verify-first clause: the chosen rule must be re-read at HEAD before a scenario is authored against
  it. A scenario written against a rule whose wording has since changed tests nothing, and this is the
  stale-cache-as-evidence archetype in a new place.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/instruction-conformance/` — the new
  component this plan creates. ⭐ Named at component granularity, not at `skills/`, because a
  bundle-wide claim contains every sibling plan's component by containment and would serialize the
  queue behind a plan that adds one directory.
- OBSERVED: `test/pm-plugin-development/instruction-conformance/` — the mirror test directory

⛔ **Removed at cleanup 2026-09-22**: `marketplace/bundles/plan-marshall/skills/manage-findings/` was
declared HYPOTHESIS, contingent on a verdict-storage hypothesis now REFUTED (see Claim Labels) — the
fallback branch (report from the runner's own TOON) is the only branch, so `manage-findings/` is never
touched by this plan.

⚠ **Read-only, deliberately NOT declared above**: `CLAUDE.md` is the source of the rule under test and
is **read, never modified**. Declaring a read-only reference here would serialize every sibling plan
behind a file this plan does not touch, which the section's own authoring rule calls out as
over-declaration.

## Dependencies and Sequencing

- Depends on: none. This is the epic's first row and the seam every other WS-01 deliverable sits on.
- Overlaps with: PLAN-02, which consumes this plan's fixture format and declares the same new
  component. Strictly sequenced; the two are never paired under any parallelization scope.
- Adjacent to: `plugin-doctor`, which lints the component this plan creates but is not modified by it.
  PLAN-05 touches `plugin-doctor` directly — if both are ever in flight, that adjacency becomes a real
  overlap and must be re-checked.

## Non-Goals

⛔ This plan changes **no instruction prose anywhere in the corpus**, whatever its verdict comes out
as. A conformance result is evidence for a later, separately-gated decision; acting on it here would
be a Claude-tuned edit to a fleet-wide corpus with no cross-model signal, which WS-02 exists to
prevent. ⛔ It also imports no upstream fixture format, scenario text, or scoring code — the idea is
adapted, the artifacts are this repository's own.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-01-conformance-harness-seam.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
