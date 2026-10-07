# PLAN-31: Orchestrator Execution-Context Dispatch Ruleset

epic: plan-optimization
workstream: WS-10

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-31-orchestrator-dispatch-ruleset.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The orchestrator has **no stated rule** for when to dispatch an `execution-context` agent versus
run inline: an exhaustive grep for `execution-context`, `Task:`, `dispatch`, `subagent`, and
`Agent` across both `marshall-orchestrator/**` and `persona-marshall-orchestrator/**` returns
**zero hits**. Every verb therefore runs wholly inline, not by decision but by silence — the
persona constrains WHAT the orchestrator may do (prime directive, small-ops carve-out) but never
HOW it executes. Two orchestrator task classes plausibly warrant dispatch — deep landing analysis
(`analyze`) and research/planning structuring (`decompose`) — and each has a distinct blocker that
a naive "just dispatch it" rule would get wrong. This plan is **DESIGN-FIRST**: settle the ruleset,
then encode it.

## Deliverables

1. **Encode the dispatch decision rule in the persona standard.** Add one rule block to
   `persona-marshall-orchestrator` (identity-level: it sits with the prime directive and the
   carve-outs, and per the standard's own precedence the standard wins over verb docs). Key it on
   three tests, ALL of which must pass before dispatching: **depth** (is the read burden large
   enough to justify agent overhead?), **fork-freedom** (does the work need `AskUserQuestion`?),
   and **write-freedom** (does it mutate the ledger?). Dispatch only when depth is high and the
   other two are "no". The governing maxim: **dispatch gathers, the orchestrator decides.**
2. **Encode the two hard constraints that make dispatch safe.**
   (a) *Read-only by instruction, not by tool surface* — the Bash-capable `execution-context`
   exposes `Read, Write, Edit, Glob, Grep, Bash, Skill`, so a dispatched analyst CAN write; the
   prohibition must be carried in the dispatch prompt, and the agent returns a structured verdict.
   (b) *All ledger writes stay in the orchestrator context* — the direct-file-access carve-out is
   scoped to the orchestrator's OWN access and the log-everything posture routes decisions through
   `manage-logging`; a subagent writing `landings/PLAN-NN.md` or transitioning the queue would
   bypass both. Add a fall-back-to-inline clause (never a retry loop) for the stream-idle timeouts
   dispatched `execution-context` agents have repeatedly hit in this project.
3. **`analyze`: depth-thresholded dispatch, with the ingestion-boundary interaction resolved.**
   The verb already forks on granularity at Step 2. A Step 4 mid-flight observation stays inline
   (dispatch overhead would exceed the work). A Step 3 full ship MAY dispatch the Step 1
   ground-truth verification when the read burden is large (real diff, PR threads, CI state,
   metrics, archived plan artifacts). Resolve the vehicle mismatch explicitly:
   `execution-context-reader` is the right TRUST vehicle for pasted third-party content (it is the
   reader in the untrusted-ingestion contract) but has **no Bash**, so it cannot run `git show` or
   the CI abstraction and cannot do ground-truth verification at all; the Bash-capable
   `execution-context` can verify but has Write/Edit. Decide and document the composition — the
   likely shape is two-stage (reader extracts a candidate struct from the paste →
   `untrusted-ingestion:validate_struct` → Bash-capable verification), NOT a single dispatch.
4. **`decompose`: split the verb along the fork line.** `AskUserQuestion` is absent from BOTH agent
   surfaces (`execution-context`: Read/Write/Edit/Glob/Grep/Bash/Skill;
   `execution-context-reader`: WebSearch/WebFetch/Read/Grep), which collides head-on with persona
   identity attribute #9 requiring genuine forks to be surfaced via `AskUserQuestion` — and
   `decompose` is where forks are densest. So the verb may NOT be dispatched wholesale. Document
   the seam: DISPATCHABLE = read the source corpus, map candidate deliverables, compute each plan's
   expected surface (the disjointness input `next` consumes), find prior art and collisions.
   INLINE-ONLY = Step 2 workstream cuts, Step 3 split-guard verdicts, Step 4 queue writes, Step 5
   reconciliation, Step 6 logging, and every escalation.
5. **Structured-return obligation.** Require any dispatched agent to return a payload the
   orchestrator consumes as-is; if the orchestrator must re-derive the findings, the delegation was
   net-negative. Name the return shape for each dispatch site added above.

Five deliverables — under the ~6 split-guard presumption, and D1/D2 are one coherent rule block
while D3/D4 are its two applications, so the set ships as one unit.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/standards/orchestration-model.md`
  (primary — the rule block)
- `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/SKILL.md` (identity
  attribute cross-reference, if the rule warrants one)
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/analyze.md` (thin pointer)
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/decompose.md` (thin pointer)
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/SKILL.md` (Enforcement block, if
  the dispatch rule needs a prohibition line)

Documentation/contract-only surface — no script changes expected.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-30** on `marshall-orchestrator/workflow/analyze.md` and
  `workflow/decompose.md` → **ADJACENT**. Sequence PLAN-30 first (smaller, mechanical) and run
  PLAN-31 after, or accept a rebase on those two files.
- Disjoint from PLAN-24 / PLAN-25 / PLAN-26 / PLAN-28 (all live) — none touches the orchestrator
  or persona-orchestrator skill trees.
- **DESIGN-FIRST**: D1's three-test rule and D3's reader-vs-Bash composition are genuine design
  decisions, not transcription. Expect the plan to settle them at outline before implementing, and
  to surface any residual fork to the operator.

## Hand-Off Command

```text
/plan-marshall The marshall-orchestrator skill has no stated rule for when to dispatch an execution-context agent versus run inline — an exhaustive grep for execution-context, Task:, dispatch, subagent, and Agent across marketplace/bundles/plan-marshall/skills/marshall-orchestrator and .../persona-marshall-orchestrator returns zero hits, so every verb runs inline by silence rather than by decision. This is DESIGN-FIRST work: settle the ruleset, then encode it. Add one dispatch decision rule to the persona-marshall-orchestrator standard (orchestration-model.md), keyed on three tests that must ALL pass before dispatching: depth (is the read burden large enough to justify agent overhead), fork-freedom (does the work need AskUserQuestion), and write-freedom (does it mutate the ledger) — dispatch only when depth is high and the other two are no, under the maxim "dispatch gathers, the orchestrator decides". Encode two safety constraints: dispatched agents are read-only BY INSTRUCTION not by tool surface (the Bash-capable execution-context exposes Write and Edit, so the prohibition must ride in the prompt and the agent returns a structured verdict), and ALL ledger writes stay in the orchestrator context because the direct-file-access carve-out is scoped to the orchestrator's own access and log-everything routes decisions through manage-logging — a subagent writing landings/PLAN-NN.md or transitioning the queue would bypass both; include a fall-back-to-inline clause (never a retry loop) for the stream-idle timeouts dispatched agents hit in this project. Then apply the rule to two verbs. For analyze: keep Step 4 mid-flight observations inline, allow Step 3 full-ship ground-truth verification to dispatch when the read burden is large, and resolve the vehicle mismatch explicitly — execution-context-reader is the right trust vehicle for pasted third-party content but has NO Bash so it cannot run git show or the CI abstraction and cannot verify ground truth at all, while the Bash-capable execution-context can verify but has Write/Edit; the likely correct shape is two-stage (reader extracts a candidate struct, untrusted-ingestion:validate_struct validates it, then Bash-capable verification) rather than a single dispatch. For decompose: AskUserQuestion is absent from BOTH agent tool surfaces, which collides with persona identity attribute #9 requiring genuine forks to be surfaced via AskUserQuestion, and decompose is where forks are densest — so it may NOT be dispatched wholesale; document the seam where dispatchable work (read the corpus, map candidate deliverables, compute each plan's expected surface for the disjointness check, find prior art and collisions) is separated from inline-only work (workstream cuts, split-guard verdicts, queue writes, reconciliation, logging, escalations). Finally require any dispatched agent to return a payload the orchestrator consumes as-is, naming the return shape per dispatch site, since a delegation whose findings must be re-derived is net-negative. Documentation and contract only — no script changes expected.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-31.md}
