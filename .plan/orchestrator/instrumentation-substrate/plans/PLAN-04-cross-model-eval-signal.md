# PLAN-04: Cross-model evaluation signal

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision relayed by `review-apparatus-001`; row status `parked`).** `plan-marshall-mcp` replaces both the process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted as rows `04.*` to `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/instrumentation-substrate-carry-over.md` as PM-MCP input. **Do NOT emit; un-park only by explicit operator decision.** The body below is kept intact as the evidence chain.

epic: instrumentation-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Produce the first behavioural signal on a runtime this repository does not currently test, so that a
change to the shared instruction corpus has a measurable effect instead of an assumed one. Today
`CLAUDE.md` states that only Claude Code is tested as a runtime, and the existing target tests are
structural — they assert emission, frontmatter mapping, registration lockstep and executor resolution,
none of which is behaviour.

⚠ **Read PLAN-03's recorded decision before scoping this plan.** A refused calibration axis does not
cancel this work; it changes what the work is *for*, from a calibration instrument into a regression
tripwire that catches a corpus edit degrading a runtime nobody watches. The deliverables below hold in
both readings, but the objective sentence in the request must match the decision that was actually
taken.

## Deliverables

1. A run harness that holds the **scoring instrument fixed** while the model under test varies — the
   single design property without which cross-model numbers are not comparable. ⛔ The scorer must not
   be the model being scored, and must not be a sibling of it at the default configuration.
2. A fixture task drawn from this repository's real workflow, with a reference result to score
   against — a concrete artifact tree, not a rubric written in prose.
3. Reported metrics that include **token consumption**, so a corpus edit's cost is a measured
   regression signal rather than an after-the-fact per-run observation. This is what connects the
   epic to the repository's standing token-reduction priority.
4. Results reported as a sample, not a verdict: a single run of a non-deterministic system is one
   observation, and the report must say so in its own output rather than in a footnote.
5. A sizing statement — runtime, token cost, and money per run — published **before** the harness is
   proposed for routine use. Size the lever before staging it.

## Claim Labels

- OBSERVED: `CLAUDE.md` § "Multi-Assistant Support" states "**only Claude Code is tested as a
  runtime**" — read at `CLAUDE.md`. This is the gap this plan closes and the repository states it
  itself.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md Multi-Assistant Support: only Claude Code is tested as a runtime, verbatim at HEAD
- OBSERVED: The existing non-Claude target tests are structural rather than behavioural — the test
  tree carries `test/marketplace/targets` and
  `test/plan-marshall/platform-runtime/test_opencode_runtime.py`, both asserting emission and
  resolution. Corroborated in this session by `architecture search --content --pattern "SessionStart"`,
  which located `test_opencode_runtime.py` among the platform-runtime tests.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: test/marketplace/targets + test_opencode_runtime.py both present, structural only; antigravity structural tests also added since staging, gap wider not narrower
- HYPOTHESIS: A three-role separation — the model executing the workflow, a second model standing in
  for the operator so a question-driven workflow can be batch-run at all, and a third scoring the
  result — is necessary here, because plan-marshall's workflow is question-driven and cannot be
  batch-run without something to answer its questions. Confirm/refute against the actual interaction
  surface at `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` (verify-at-outline).
  ⭐ **Corroborated with a material sizing correction at cleanup 2026-09-22**: the blocking point is
  real, but `phase-2-refine/SKILL.md` Step 11 shows the leaf batches every open clarification into ONE
  `refine_prompt` envelope and the orchestrator re-dispatches **at most once** — so an operator-stand-in
  role is needed for at most one batched round per plan, not per turn. Step 3's "Recipe Shortcut" also
  forces `confidence=100` and skips analysis for recipe-sourced plans — a batch-runnable fixture path
  needing NO operator-stand-in role at all. **Consequence, absorbed into this spec's scope**:
  deliverable 1's harness can be sized smaller than a per-turn interactive stand-in; deliverable 2's
  fixture task selection should prefer (or include) a recipe-sourced path to exercise the zero-role
  case cheaply.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: phase-2-refine/SKILL.md Step 11: batched refine_prompt, at-most-one re-dispatch; Step 3 recipe shortcut skips analysis entirely; sizing correction applied to deliverables 1-2
- HYPOTHESIS: `marshalld`'s existing build-server machinery is **not** the right vehicle for this and a
  separate surface is warranted — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md` (verify-at-outline). ⛔ If
  refuted, reuse rather than build; a second job runner would be duplication.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: manage-build-server/SKILL.md anti-laundering wall + notation_allowlist refuse an off-template eval submit; reuse structurally closed, separate surface confirmed warranted
- Verify-first clause: ⛔ **No result from any external evaluation harness is carried into this plan
  as evidence.** The prior art that informed this spec was inspected for *design*, and not one of its
  results was read. It establishes that such a mechanism is buildable and what shape it takes; it
  establishes nothing about whether any instruction change helps or harms any model. That question is
  still open and this plan is how it gets answered.

## Four flaws in the prior art that must be designed out

Recorded here because designing them out is cheaper than discovering them, and because inheriting them
silently is the failure mode this epic exists to prevent.

1. ⛔ **Self-grading.** In the reference design the scorer and the executor default to the same model
   id. Comparable numbers require the instrument to be independent of the subject; make that a checked
   precondition of a run, not a convention.
2. ⛔ **A trend gate is not a bar.** Comparing the latest run against the previous release passes a slow
   multi-release drift every time. This repository has already recorded that defect shape. Report
   against an absolute reference as well as a delta.
3. ⚠ **Corpus-under-test drift.** A harness that pulls the corpus from a moving branch while the user
   has pinned a release is not measuring what the user runs. Pin the corpus under test explicitly and
   report the pin in the result.
4. ⚠ **Unsized cost.** The reference design carries a four-hour execution timeout and a two-hundred-
   iteration ceiling per run, and nothing in it is sized against this repository's budget. Deliverable
   5 exists because of this.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/eval-cross-model/` — the new evaluation
  component this plan creates. ⭐ Named at component granularity: a `skills/`-wide claim contains the
  whole `plan-marshall` bundle and collided with four live plans on the first disjointness check, none
  of which this plan shares any work with.
- OBSERVED: `test/plan-marshall/eval-cross-model/` — the mirror test directory
- HYPOTHESIS: `doc/developer/` — a developer-facing document describing how to run the harness and read
  its output (verify-at-outline)

⚠ **Read-only, deliberately NOT declared above**: `marketplace/targets/`, read to resolve which
runtimes can be driven. The harness drives a runtime; it does not modify the generator.

## Dependencies and Sequencing

- Depends on: PLAN-03, on its **decision** and not merely on its landing.
- Overlaps with: none declared. PLAN-03 touches `doc/adr/`; this plan touches a new component.
- Adjacent to: `manage-build-server`, whose job-running machinery this plan reads to decide whether to
  reuse it, and does not modify unless the reuse hypothesis confirms.

## Non-Goals

⛔ **No instruction wording is changed by this plan**, and landing it does not authorise a subsequent
sweep. The harness produces evidence; what is done with that evidence is a separate, separately-staged
decision. ⛔ No upstream harness code, configuration schema, or fixture tree is copied — the three-role
separation and the infra-failure partition are *ideas*, and the implementation is this repository's.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-04-cross-model-eval-signal.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
