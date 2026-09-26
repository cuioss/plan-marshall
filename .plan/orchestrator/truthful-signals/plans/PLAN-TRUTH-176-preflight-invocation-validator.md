# PLAN-TRUTH-176: a pre-flight invocation validator to stop systemic argparse-surface guessing

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.

## Objective

Add a pre-flight verb to `tools-script-executor` that validates a proposed
`{notation} {verb} {flags...}` invocation against the target script's live `--help`
accept-set before it is ever run, replacing the reject-reread-retry cycle that
produced 41 script-call failures (16 distinct argparse rejections across 14 scripts)
on a single PLAN-TRUTH-143 run.

## Deliverables

1. Add a pre-flight validation verb to `tools-script-executor` that takes a proposed
   invocation, resolves the target script's live `--help` accept-set (the same walk
   `manage-invocation-invalid` already performs), and returns either `valid` or the
   nearest canonical form with the specific mismatch named.
2. Publish canonical-invocation blocks for the two highest-repetition verbs from the
   source evidence — `manage-findings qgate` and `manage-solution-outline
   get-deliverable` — which alone accounted for 16 of the 41 rejections on the
   source plan.

## Claim Labels

- OBSERVED: PLAN-TRUTH-143's `script-failure-analysis` aspect found 41 script-call
  failures across 18 unique signatures, 16 of 18 classified `argparse_other` or
  `invented_flag`, spread across 14 distinct scripts; `manage-findings qgate` and
  `manage-solution-outline get-deliverable` each occurred 8 times — read from
  PLAN-TRUTH-143's own retrospective finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 41-failures / 18-signatures / 14-scripts figures come from PLAN-TRUTH-143's script-failure-analysis aspect, whose plan directory no longer exists in this checkout.
- OBSERVED: `manage-invocation-invalid` already derives its accept-set from a live
  `--help` walk — read from prior corpus usage (e.g. `plan-orchestrator/SKILL.md`'s
  own canonical-block enforcement note)
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _analyze_manage_invocation.py's module docstring (lines 27-43) states the recursive --help walk, the four parse anchors, the in-process memo and the content-hash-keyed on-disk cache were lifted into script-shared's argparse_surface - one shared live-help derivation, also consumed by the executor generator.
- Verify-first clause: confirm the exact `tools-script-executor` verb surface and the
  `manage-invocation-invalid` implementation location against HEAD at outline before
  scoping the new verb's integration point.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/recipe-fix-argparse-rejection/**`
- OBSERVED: `test/plan-marshall/tools-script-executor/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none known
- Adjacent to: `pm-plugin-development:recipe-fix-argparse-rejection` (the post-hoc
  remedy this pre-flight verb complements rather than replaces)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-176-preflight-invocation-validator.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
