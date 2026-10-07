envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:51:59Z

component=plan-marshall:manage-references
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=artifact_consistency,log_analysis,manifest_decisions,routing_decisions,plan_efficiency

# Resolve a plan footprint from the landing commit when no worktree survives

## Context

Five independent consumers in this plan each needed the realized footprint, and all five degraded to unmeasurable on the same missing derivation:

- `manage-execution-manifest compose` logged `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed` (twice, at 4-plan).
- `check-artifact-consistency` returned `inconclusive` for both `affected_files_recall` and `affected_files_exact_match`.
- `check-manifest-consistency` rule M4 skipped with `base: unknown`, `diff_available: false`.
- `check-routing-decisions` had no footprint until this retrospective hand-supplied one.
- `analyze-logs` emitted `ARTIFACT_COVERAGE_UNMEASURABLE`, disabling the `[ARTIFACT]`-emission floor.

None of the five escalated. Each reported its own degradation honestly and independently, so nothing aggregated them into "this plan shipped with zero coverage measurement".

## Root cause

The shared footprint resolver has four tiers and every one of them was unavailable at retrospective time:

1. Live worktree diff — `branch-cleanup` removed the worktree.
2. Realized-footprint capture — never written; `manage-references compute-footprint` was invoked three times during finalize and argparse-rejected all three times (`script-failure-analysis`: `manage-references / compute-footprint / exit 2 / occurrence_count 3`, first at `2026-08-24T09:55:34Z`, while the worktree was still alive).
3. Merge-commit fallback — the plan's configured `pr_merge_strategy` is `squash` and it landed through the merge queue, so `77db1a0d3` has exactly one parent (`9999f4d87`). A squash landing is structurally not a merge commit, so this tier can never fire for this repository's default merge strategy.
4. Legacy `references.modified_files` key — absent.

`compute-footprint` also *requires* `--worktree-path`, so after removal there is no invocation that could succeed even if the caller got the flags right.

## Proposed action

Add a post-landing tier to the shared footprint resolver that derives the footprint from the landing commit already recorded in plan state:

- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail` carries `merged via queue as 77db1a0d3`, and the `facts` sub-object carries `merge_mechanism` / `merge_state`.
- With that sha, `git diff --name-only {sha}^ {sha}` yields the exact 16-file footprint (verified by hand during this retrospective).

Two supporting changes:

- Make the realized-footprint capture fire on a path that cannot be skipped by an argparse rejection, or fail loudly when it is rejected. Three silent exit-2s during finalize left the capture unwritten and nothing noticed.
- Give the resolver a `footprint_source` discriminator on every consumer's output so a reader can tell which tier answered — `check-routing-decisions` already does this (`footprint_source: diff_file`) and the others do not.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,inconclusive,"Plan footprint could not be resolved from any tier ... recall is unmeasurable, not 0%"`
- aspect: manifest_decisions — `branch_cleanup_changes,skip,rule M4 skipped — no diff data available (base=unknown or empty diff)`
- aspect: log_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE: ... This is an unmeasured check, not a clean one.`
- aspect: script_failure_analysis — `anti-pattern,argparse_other,"plan-marshall:manage-references:manage-references",compute-footprint,2,"2026-08-24T09:55:34Z","",3`
- decision.log at 4-plan — `[STATUS] pre_push_quality_gate_inactive — ... plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed`
- `git rev-list --parents -n 1 77db1a0d3` returns one parent, confirming the squash landing defeats the merge-commit tier
