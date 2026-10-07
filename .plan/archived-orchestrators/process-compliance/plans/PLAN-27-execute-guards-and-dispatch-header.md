# PLAN-27: Phase-5 scope-creep guard and the WORKTREE dispatch header

> ✅ **Staged 2026-09-29 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-27-execute-guards-and-dispatch-header.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Fix two phase-5 contracts that fail in every run:
- The scope-creep guard crashes whenever it fires, and measures against a base that predates the
  worktree.
- The dispatch `WORKTREE:` header is specified absolute in one document and repo-relative in another,
  and one of the two readings is refused as a contract violation.

## Deliverables

1. **The scope-creep guard can report, and measures the plan's own diff.** `scope_creep_check check`:
   - It persists `--type scope_creep_warning`, which the findings store rejects ("Invalid finding type:
     scope_creep_warning. Must be one of ('bug', …, 'pr-comment-overflow')"). Every over-threshold run
     therefore exits `finding_persist_failed`, halting the envelope.
   - It diffs `plan_creation_sha..HEAD`, which predates worktree move-in and any
     `finalize-step-sync-baseline` rebase. Observed `residual_count` values were 470 and 738 against a
     threshold of 5, while the plan's own diff against the merge base was 19 files, all declared.
   - One leaf worked around it with `--threshold 1000`, an unsanctioned override that would also hide
     real creep.

   Register the type (or map it to an existing one), diff against the merge base, and add a test that
   runs the guard after a rebase.
2. **One shape for `WORKTREE:`.** `plan-marshall/workflow/execution.md` puts the absolute
   `manage-status get-worktree-path` value into the phase-5 dispatch header, and phase-6-finalize's
   dispatch templates forward the absolute `status.metadata.worktree_path`. The execution-context
   agent contract says "Repo-relative … NEVER absolute" and refuses it (`contract_violation`,
   `missing_field: "invalid WORKTREE"`), inconsistently: one earlier dispatch with the same value
   passed. State one shape in every producer and the consumer, derived from one definition, and have
   the consumer check it identically on every dispatch.

## Claim Labels

- OBSERVED: guard crash on the unregistered type; `residual_count` 470 and 738 vs 19 merge-base files — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-032.md` and `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-017.md` § 4; recorded earlier as an Open Defect (drain 2026-09-23, `implement-opencode-enforcement-parity-005`), whose premise truthful-signals PLAN-TRUTH-178 (parked) also carries
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: scope_creep_check.py:180 finding_type='scope_creep_warning' absent from vocabulary (tools-file-ops constants.py); :105-113 diffs {plan_creation_sha}..HEAD (:212)
- OBSERVED: `WORKTREE:` absolute vs repo-relative disagreement — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-017.md` § 1 and `inbox/archive/module-budget-campaign-completion/module-budget-campaign-completion-006.md` (finalize templates, refused dispatch quoted)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: execution.md:147-166 puts absolute get-worktree-path value in WORKTREE:; execution-context.md WORKTREE row 'Repo-relative ... NEVER absolute'
- HYPOTHESIS: the repo-relative rule and its check live in `marketplace/bundles/plan-marshall/agents/execution-context.md` — confirm/refute at that file § the `WORKTREE` field row (verify-at-outline)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: rule in execution-context.md WORKTREE row (Step 1 checks presence only, not shape); repeated in execution-context-reader.md

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — type, diff base
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — Step 6.5 persisted shape
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — the finding-type vocabulary is defined here, not in manage-findings (corrected cleanup 2026-09-29)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/` — type validation consumer
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — phase-5 `WORKTREE:` header
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — finalize dispatch templates' `WORKTREE:`
- OBSERVED: `marketplace/bundles/plan-marshall/agents/execution-context.md` — consumer contract
- OBSERVED: `marketplace/bundles/plan-marshall/agents/execution-context-reader.md` — second consumer carrying the same WORKTREE rule (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` — canonical dispatch contract naming WORKTREE (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `test/plan-marshall/phase-5-execute/`
- OBSERVED: `test/plan-marshall/manage-findings/`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-19 (`execution.md`, `test/plan-marshall/phase-5-execute/`), and PLAN-20 / 21 / 24 (`phase-6-finalize/SKILL.md`). Sequence after PLAN-19.
- Reclaimed: the scope-creep defect was also carried by truthful-signals PLAN-TRUTH-178, which is parked (PM-MCP); it is owned here under the "fix, not relay" directive.
- Scope-bloat guard: 2 deliverables.

## Folded inbox material (same act)

- `plan-12-tool-triage-032.md` (finding): deliverable 1
- `plan-12-tool-triage-017.md` items 1, 4 (finding): deliverables 2, 1
- `module-budget-campaign-completion-006` (archived; reclaimed from the PM-MCP carry-over row MB06.1): deliverable 2

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-27-execute-guards-and-dispatch-header.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
