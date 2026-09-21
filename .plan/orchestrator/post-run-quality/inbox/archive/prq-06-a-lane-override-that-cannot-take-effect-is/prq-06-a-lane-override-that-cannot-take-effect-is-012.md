envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:45:07Z

component=plan-marshall:manage-execution-manifest
category=bug

# A signature change swept its production callers and missed every test caller, breaking 15 call sites across 3 files

Removing an unused parameter from `_apply_lane_resolution` updated both PRODUCTION call sites and no test call sites. Fifteen tests across three files then failed identically with `TypeError: _apply_lane_resolution() takes 3 positional arguments but 4 were given`.

## Evidence

Three Q-Gate findings, one root cause, all from module-tests job `c1c965e20a644effae2cf46050d2f985`:

- `941d44` — `test_manage_execution_manifest_compose.py`, 11 tests
- `7d260c` — `test_declared_step_contract_regression.py`, 1 test (line 468)
- `94b761` — `test_subtraction_visibility_population.py`, 3 tests

All three resolved to a single fix task (TASK-010), which is the tell that they were never three defects.

## The compounding half

`94b761`'s detail records that `test_subtraction_visibility_population.py` was **in neither deliverable 5's nor deliverable 6's declared write set**, "even though it consumes the changed symbol." It shipped anyway and the retrospective then classified it as scope creep. So the file was invisible to the plan twice: absent from the declared write set at outline time, and absent from the caller sweep at execute time.

## Rule

A signature change's unit of work is **every caller of the symbol**, derived by one sweep over the whole inventory — not the production callers with tests treated as a separate, later concern. `architecture search --content --literal --pattern <symbol>` answers this in one call and does not partition by category unless asked to.

Note the ordering: the 3-outline Q-Gate had ALREADY told this plan (finding `44ee22`) to re-derive its module-testing scope from a changed-symbol consumer sweep rather than asserting it. The outline was corrected; the execute-time edit still swept only production.
