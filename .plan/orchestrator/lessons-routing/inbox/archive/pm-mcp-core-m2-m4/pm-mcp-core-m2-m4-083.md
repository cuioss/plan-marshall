envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:31Z

# Candidate lesson: scope-creep check cannot persist its finding and miscounts upstream commits

Component: plan-marshall:phase-6-finalize (scope-creep check) / plan-marshall:manage-findings
Category (proposed): bug
Source: plan code-analysis-base, finalize (script-failure cluster)

## Observation

- The scope-creep check exited with `finding_persist_failed`: `manage-findings` rejects the finding type `scope_creep_warning`, so the producer emits a type the store's enum does not accept.
- The check also counted the files of upstream commit d091527 (pm-workflow, merged to main after `plan_creation_sha`) as scope creep. The realized footprint was measured against `plan_creation_sha` instead of the merge base with the current base branch, so any commit that landed on main during the plan's lifetime shows up as creep after a rebase/sync.

## Proposed correction

- Add `scope_creep_warning` to the manage-findings type enum (or have the producer use an existing type); add a contract test that every type a producer emits is accepted by the store.
- Measure the footprint from the merge base of the plan branch with the base branch (as the PR diff does), not from `plan_creation_sha`.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-001.md` from plan code-analysis-base (PLAN-36, #31)
