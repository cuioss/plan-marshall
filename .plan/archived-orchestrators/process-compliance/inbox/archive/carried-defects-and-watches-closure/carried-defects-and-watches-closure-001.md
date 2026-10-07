envelope_version=1
sender_type=plan
sender_id=carried-defects-and-watches-closure
epic=process-compliance
kind=finding
created=2026-09-23T16:09:53Z

# Process-compliance findings from PLAN-183 execution (carried-defects-and-watches-closure)

## 1. Mailbox probe not_orchestrated on phase transitions
- Observed: `manage-status transition` returned `mailbox.probe: not_orchestrated` with reason `request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)` for all 1-init through 4-plan transitions.
- Our `request create` used `--source description --source-id .plan/orchestrator/test-quality/plans/PLAN-183-carried-defects-and-watches-closure.md --body-file <same>`, matching the canonical `implement {path}` file-pointer shape.
- Suspected cause: detector expects a different source type or exact pointer grammar; manual `orchestrator queue --set-row PLAN-183 --field plan_marshall_plan_id` linkage succeeded, so orchestration is real but mailbox auto-detection misses it.
- Impact: no mailbox delivery auto-wired; test-quality inbox report must be filed explicitly via `orchestrator inbox write --target-plan PLAN-183`.

## 2. Worktree discipline deviation (use_worktree=true but edited main checkout)
- Local plan `carried-defects-and-watches-closure` was created with `--use-worktree` (default true). Phase-5-execute Step 2.5 should materialize `feature/{plan_id}` worktree on first task execution.
- This run executed all D1-D8 inline on the main checkout to avoid colliding with concurrent running PLAN-182 worktree state and the already-dirty `.plan/orchestrator/test-quality/` ledger (epic.md, status.json, inbox, landings).
- All source edits honor the PLAN-183 Write-Boundary; no `.plan/orchestrator/` file was written except via sanctioned `orchestrator queue` / `inbox` verbs and the plan's own local dir. Finalize (worktree move, branch, PR) is deliberately deferred to operator decision.

## 3. Stale leads re-derived at dispatch HEAD (spec-directed)
- D2 line refs (304-316) shifted but the hardcoded `_TWO_PART_GROUPS` mirror was real at HEAD; fixed via `OPERATION_REGISTRY` + registry-driven test.
- D3 path `test/plan-marshall/tools-permission-fix/test_permission_fix.py:1093-1113` absent at HEAD (directory holds 10 other modules, no ArgumentParser rebuild); recorded as vacuous-clean with evidence, no code change.
- D1 nomination figures (467/2/465, budget 429) re-derived as 469/2/467 with budget count 427 at dispatch; the 5 PLAN-177 false-positive shapes read clean (0 residual); the 2 live `subprocess-pythonpath` errors were real findings in `test_build_module_tests_filter.py` and were fixed with inline `env={"PYTHONPATH": ...}` dicts.
- D5 `uv.lock` HYPOTHESIS verified via `.pyprojectx/uv-0.9.16/uv lock --check` (exit 0, 21 packages).

## 4. Task-contract friction (non-blocking)
- `manage-tasks batch-add` rejects `uv.lock` as a step target (`steps must be file paths`); D5 task therefore declares only the fixture file while the lock sync is performed and evidenced as a verification command. Suggest clarifying the step-target grammar for root lockfiles.
- `finalize-step` rejects `--step-number` (accepts `--step`); early call failed with `invalid_invocation` and was retried correctly. No state corrupted.
