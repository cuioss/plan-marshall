# PLAN-01: Instruction-conformance harness seam

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
  returned `count: 0` over `files_scanned: 5462` with `unreadable: 0`, `truncated: false`,
  `elided: 0`, so the coverage is clean and the zero is a derived negative rather than an absence of
  looking. Measured in this session at `main` `77cb2e251`.
- OBSERVED: The repository asserts, without deriving it, that its hard rules "exist because Claude
  regularly violates them despite softer guidance" — read at `CLAUDE.md` § "Workflow Discipline (Hard
  Rules)". This sentence is the proposition this plan makes testable.
- OBSERVED: A dispatch vehicle with a pinned model and effort already exists and does not need
  inventing — the `execution-context-{level}` agent family, read at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` and the agent
  definitions it fronts.
- HYPOTHESIS: A dispatched `execution-context-{level}` leaf can be given a scenario prompt that does
  **not** load the rule's own skill, so the leaf's compliance is attributable to the instruction under
  test rather than to a second copy of it arriving through the persona chain — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` § the unconditional
  base-persona load (verify-at-outline). ⛔ If refuted, the whole measurement is confounded and the
  plan must re-scope around a different isolation mechanism before implementing anything.
- HYPOTHESIS: `manage-findings` can store a conformance verdict without a schema change — confirm/
  refute at `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` (verify-at-outline).
  If refuted, report verdicts from the runner's TOON only and do not grow the findings schema in this
  plan.
- Verify-first clause: the chosen rule must be re-read at HEAD before a scenario is authored against
  it. A scenario written against a rule whose wording has since changed tests nothing, and this is the
  stale-cache-as-evidence archetype in a new place.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/instruction-conformance/` — the new
  component this plan creates. ⭐ Named at component granularity, not at `skills/`, because a
  bundle-wide claim contains every sibling plan's component by containment and would serialize the
  queue behind a plan that adds one directory.
- OBSERVED: `test/pm-plugin-development/instruction-conformance/` — the mirror test directory
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/` — touched only if the
  verdict-storage hypothesis above confirms (verify-at-outline)

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
