envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:19:03Z

component=plan-marshall:manage-execution-manifest
category=bug
bundle=plan-marshall

# "plan footprint is empty" at compose time is true by construction, not a measurement

## Observation

At `2026-07-29T06:49:50Z`, during **phase-4-plan**, `manage-execution-manifest compose` wrote this decision-log line:

> `pre-push-quality-gate omitted — plan footprint is empty — no changed files to build`

One second later, at the same timestamp, it wrote:

> `ceremony_finalize selection — finalize.qgate=always, added pre-push-quality-gate to phase_6.steps`

The plan's footprint was **not** empty in any meaningful sense — four files were about to be modified and were declared in `references.affected_files` at that moment. The footprint was empty because **the worktree did not exist yet**: `phase-1-init` logged at 05:59:23Z that *"materialization [is] deferred to phase-5-execute Step 2.5"*, and phase-5-execute did not begin until 06:54:35Z. Compose runs ~5 minutes before any code can exist.

So the build-decision footprint at compose is empty for **every plan, always**. The prune it drives is a guard whose predicate can never be false.

## Why it matters

The quality gate survived on this plan only because the project sets `lane: minimal` on `default:pre-push-quality-gate`, which `_read_finalize_gates` maps to `always` and `_apply_ceremony_finalize_selection` re-inserts. Under the class default `lane: auto`, nothing re-adds it — the pre-push quality gate would be pruned from every plan on a premise that is a scheduling artifact rather than a fact about the change.

There is a second, subtler edge: the composer is simultaneously consuming **two different footprint oracles**. The six-row matrix and the `_apply_simplify_inactive` / `_apply_security_audit_inactive` pre-filters gate on `affected_files_count`, which was non-zero (4) at that same instant — which is why `finalize-step-simplify` was correctly kept. The build-decision path gated on the live diff, which was zero. One composer, one instant, two contradictory answers to "does this plan change anything", and the decision log reports the second one as a plain fact.

## Corrective rule

The build-decision path must distinguish **"footprint resolved to empty"** from **"footprint not yet materialized"**, and must not prune on the second. Either defer the build/no-build verdict to a point where the worktree exists, or fall back to the declared `references.affected_files` when the live diff is unavailable. At minimum, the emitted decision-log reason must say *why* the footprint is empty, so a reader is not told a scheduling artifact is a property of the change.

## Evidence

- `decision.log` 05:59:23Z (materialization deferred), 06:49:50Z (both compose lines), 06:54:35Z (phase-5 start).
- `_manifest_decide.py` `_decide(affected_files_count=...)` and `_manifest_rules.py` `_apply_code_step_inactive` gate on the declared count; `manage-execution-manifest.py` imports `compute_plan_branch_diff` for the live-diff path.
- `_manifest_rules.py` `_LANE_TO_CEREMONY_VALUE` — only `lane: minimal` maps to `always`; `auto` defers to the pre-filter machinery.
- This plan's `execution.toon`: `pre-push-quality-gate` present with `lane: minimal`.
