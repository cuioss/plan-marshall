envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:06:50Z

component=plan-marshall:tools-script-executor
category=bug
title=Executor resolved a pre-#1370 analyze-logs.py, so the retrospective graded itself with a retired check

# Executor resolved a pre-#1370 analyze-logs.py, so the retrospective graded itself with a retired check

## Context

Plan `a-refusal-is-recorded-as-a-refusal-the-record` ran its finalize retrospective at 2026-08-31T07:54Z, minutes after its own `project:finalize-step-sync-plugin-cache` step completed at 07:46Z. The retrospective's deterministic fact scripts are invoked through `python3 .plan/execute-script.py plan-marshall:plan-retrospective:{script}`. The `analyze-logs.py` that actually executed is an OLDER version than the one at `marketplace/bundles/` in the working tree.

The evidence is positive rather than inferred, and it is checkable from two artifacts that both survive:

- At HEAD, `artifact_emission_population()` sets `change_attribution` on **every** return path (`unavailable` for the no-record and mixed-record branches, `measured` otherwise), and the caller gates `ARTIFACT_EMISSION_PARTIAL` on `attribution_measured` with the message wording `"{N} of {M} change-qualified completed task(s) emitted"`.
- The fragment produced by this run carries **no `change_attribution` key at all**, and its finding reads `"ARTIFACT_EMISSION_PARTIAL: 2 of 17 completed task(s) emitted >= 1 [ARTIFACT] line"` — the pre-fix wording, over the un-qualified completed-task population.

The change-qualification landed in commit `7845a4b9a` (`fix(plan-retrospective,plugin-doctor): make detectors publish measurements, not defaults`, #1370), which `git log` confirms is an ancestor of the current main HEAD.

## Root cause

Not established by this observation, and deliberately not asserted. The observable is that the executor's script-resolution path served a version behind the working tree at a moment when the tree's own deploy-target and sync-plugin-cache steps had just run. The known mechanism with this exact signature is the plugin registry pin being left behind when a sync mints a new cache version, so the resolver keeps selecting the previously pinned one; confirming that for this incident requires reading the registry pin against the executor version, which this retrospective did not do.

## Proposed action

1. Determine which resolution path the executor took for `plan-marshall:plan-retrospective:analyze-logs` in this run and why it was not the working-tree version.
2. Add a version-provenance line to the retrospective's own report — the resolved script path and its version — so a future report states which code produced its facts instead of leaving the reader to infer it from message wording.
3. Treat this as a general hazard, not a plan-retrospective one: any finalize step whose verdict comes from an executor-resolved script can silently grade against retired logic, and the failure is invisible because the output still looks well-formed.

## Impact observed in this run

The retrospective emitted, as a warning against the audited plan, precisely the false positive that #1370 landed to remove — a plan whose completed tasks include verification and no-op tasks was charged for their compliant silence. Because every other fact in the report was produced by scripts resolved the same way, the whole report inherits an unquantified staleness caveat.

## Evidence

- aspect: logging_gap_analysis — "The analyze-logs.py that produced this plan's fragment PREDATES commit 7845a4b9a (#1370)"
- aspect: log_analysis — fragment `artifact_emission` block: `completed_tasks: 17`, `tasks_with_artifacts: 2`, no `change_attribution` key
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` lines 1071-1102 (every branch sets `change_attribution`) and 1857-1873 (`attribution_measured` gate)
- reference: `plan-retrospective/references/logging-gap-analysis.md` — "An unqualified count MUST NOT be substituted — that is the absent-read-as-measured swap this aspect exists to prevent"
