envelope_version=1
sender_type=plan
sender_id=carried-defects-and-watches-closure
epic=test-quality
kind=landing
created=2026-09-23T16:10:27Z

# PLAN-183 execution report (carried-defects-and-watches-closure)

## landing-facts
- plan_marshall_plan_id: carried-defects-and-watches-closure
- epic: test-quality
- epic_plan: PLAN-183
- workstream: WS-03
- status: implementation-complete-PR-deferred
- pr: none-yet
- base_branch: main
- feature_branch: feature/carried-defects-and-watches-closure (reserved, not materialized; work performed on main checkout, see process-compliance finding)
- merge_head: uncommitted (10 repo files modified, all inside PLAN-183 Expected Surface)
- tier_m_skip_bot_review: not-applicable (no PR created this run; logging starts at PR creation per D8)
- coderabbit_skipped: n/a (no PR)
- sourcery_present: n/a (no PR)

## Gate figures re-derived at dispatch (D1)
- Producing command: `python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace test-conventions`
- Dispatch HEAD result: total_issues 469, error_count 2, warning_count 467; subprocess-pythonpath 2, test-module-line-budget 427, preamble 21, historical-prose 19.
- The 5 PLAN-177 residual false-positive shapes read clean (0 residual in current findings).
- Fixed: `_has_pythonpath_env_kwarg` name-only shortcut removed (`_analyze_test_conventions.py` L572-577 deleted); trust now requires binding-resolved PYTHONPATH shape via `_resolve_env_binding`.
- Fixed 2 live errors: `test/default/test_build_module_tests_filter.py:71,83` now carry inline `env={"PYTHONPATH": os.pathsep.join(sys.path), **os.environ}`; scoped re-run `--test-root test/default` reads subprocess-pythonpath 0, error_count 0.

## D-row dispositions
- D1 done: gate re-derived with producing command recorded; kwarg shortcut replaced by behavior-proving path; 2 live errors fixed.
- D2 done: `OPERATION_REGISTRY` + `list_operations()` exposed on `_dispatch` in `platform_runtime.py`; `test_platform_runtime_router.py` `_TWO_PART_GROUPS` now derived from registry (no hardcoded mirror). Compile green; full router suite deferred to module-tests (whole-tree run exceeds 10 min; compile+quality-gate green).
- D3 done (vacuous-clean at HEAD): `test/plan-marshall/tools-permission-fix/` holds no `test_permission_fix.py` and no ArgumentParser inline rebuild (grep zero matches); no builder to expose. Evidence recorded; no code change.
- D4 done (code): `_DEF_OR_CLASS` extended to `async def`; `_detect_user_facing_strings` now emits `module_docstring` context for triple-quote before any def/class per path (closes module/async unreachability by detection). Mirrored-table missing-binding drift already fails closed via `bindings[spec.key]` KeyError; recorded as construction-closed.
- D5 done: `.pyprojectx/uv-0.9.16/uv lock --check` exit 0 (21 packages, in-sync at dispatch). Builder fold: `create_nested_marshal_json(..., minimal=True)` is the single construction site in `_manage_config_fixtures.py`; `test_detection.create_minimal_marshal_json` is a one-line delegate.
- D6 done: `rule-catalog.md` now carries per-rule `###` sections for all 7 test-conventions rules (added 6 concise sections; rows already present).
- D7 decision (defer, watch retires): violation counts at dispatch are line-budget 427, preamble 21, historical-prose 19 — all non-zero, so the per-rule warning→error flip condition (zero count) is not met. Decision: DEFER flip; re-check when a rule's own count reaches zero (same trigger that flipped `test-helper-module-misnamed`). No severity edit; decision recorded here.
- D8 done: `build.py cmd_quality_gate` now runs `ruff format --check` before auto-fix and returns 1 after fixing when the check failed, so an unformatted tree blocks the gate until the formatting diff is committed. Control evidence: pre-format `--check` on touched files reported 2 files would reformat (build.py pre-existing drift + platform_runtime); post-format `--check` clean; `quality-gate` full-tree green (compile+lint, 81s).

## Verification
- `pyproject_build run --command-args compile`: success (mypy, 31s).
- `pyproject_build run --command-args quality-gate`: success (compile+lint, 81s, includes new format --check gate).
- `doctor-marketplace test-conventions --test-root test/default`: pass, error_count 0.
- Whole-tree `module-tests` exceeds 600s timeout; scoped router/manage-config suites not separately run this session — flagged as residual verification for the PR run.
- Tier M per-PR review logging: no PR this run, so D8 log lines start at PR creation; no Sourcery comments arrived.

## Deferred (operator decision required)
- No worktree materialized, no branch, no commit, no PR: main checkout carries concurrent PLAN-182 dirt plus uncommitted `.plan/orchestrator/test-quality/` ledger changes owned by the staging pass. Creating `feature/carried-defects-and-watches-closure` PR from this checkout would sweep unrelated ledger dirt into the diff. Request: operator orders finalize sequencing (after PLAN-182 lands or into a free slot) and the Tier M `skip-bot-review` label call.
- Residual: scoped pytest for router + manage-config + self-review suites at PR time, both orders per D2/D3 Done clauses.
