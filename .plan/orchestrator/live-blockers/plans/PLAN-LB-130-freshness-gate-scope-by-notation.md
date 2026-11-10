# PLAN-LB-130: The freshness gate reads the positional tokens of a build row by its tool, so a whole-tree npm, Maven or Gradle row is not a narrow scope

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-130-freshness-gate-scope-by-notation.md` and is queued as one row file, `queue/PLAN-LB-130.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-09 as the fix plan for the PLAN-LB-124 major (#1938, `landings/PLAN-LB-124.md` L3-1), with
> its cheap minors L3-4 and L3-5 folded. Designed by a read-only leaf against `main` at `9cd644892`. Ruling check: D1 is a false block
> of the push and freshness gate in normal use for npm, Gradle and Maven-chain consumers (blocking). This repository (pyproject) is not
> affected. **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.**
> Every Done-when below fails at `9cd644892` unless it says "holds at". No Sonar. No token or measurement work.

## Objective

PLAN-LB-124 made `_row_refusal` judge a row's scope before its canonical. `parse_row_scope` takes every non-flag token after the
first as scope, but the npm, Maven and Gradle discoverers emit tool-native goals, not module names: `run test`, `clean install`,
`spotlessCheck check`. Those read as a narrow scope, so a whole-tree change is refuted `build_scope_narrow` where it used to be an
unmapped canonical, an inability that passed. This plan reads positional tokens as module scope only for the tool whose positionals are
modules, and fixes two cheap defects of the same area.

## Deliverables

1. **Positional tokens are module scope only for the tool whose positionals are modules.**
   - `parse_row_scope` (`manage-tasks/scripts/_freshness_crosscheck.py` L639-731, the return at L731) is keyed on the row's own
     `notation`:
     - `plan-marshall:build-pyproject:pyproject_build` keeps today's reading (`<canonical> <module>`);
     - `plan-marshall:build-maven:maven`, `plan-marshall:build-gradle:gradle` and `plan-marshall:build-npm:npm`: every positional token
       is a goal, task or script. canonical = `payload[0]` (aligned with `_build_examined.examined_analyses`, which also reads the
       first token), the remaining positionals are dropped, scope = the flag scope only (`-pl`, `--projects`, `--workspace`). So npm
       `run test` is `('run', ())`, Maven `clean install` is `('clean', ())`, `run test --workspace=pkg-a` is `('run', ('pkg-a',))`;
     - any other notation (absent or unknown): one positional token is unchanged; more than one positional token returns `None`
       (unreadable), because the reader cannot tell a module from a goal.
   - The fail-direction split is kept: a refutation fails closed, an inability passes with its reason. The goal-positional tools do
     not return `None`: `_unreadable_scope_blocks_whole_tree` (L1166-1207) would then refuse every whole-tree npm, Maven and Gradle
     change, the same false red by another route.
   - Optional and cosmetic: the dropped goals are rendered in `row_scopes` so `clean install` does not show as a bare `clean`.

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py`, each
   calling `cross_check_candidates([row], '/nonexistent-project-dir', _required())` with the stub naming the row's notation:
   - npm `run test`, Maven `clean install`, Gradle `spotlessCheck check` and `test jacocoTestReport` (parametrized) give `scope_verdict == UNDETERMINED`, `scope_reason == REASON_SCOPE_UNREADABLE`, `contributing == [0]`, `joint_reason is None` and `row_scopes == ['<canonical>: canonical_outside_vocabulary']` (they give NARROW with `scope_narrower_than_change` at `9cd644892`);
   - `parse_row_scope(_build_entry(notation=_NPM, args=_args_for('run test')))` is `('run', ())` (it is `('run', ('test',))` at `9cd644892`);
   - at gate level, through `_run_gate_over_rows` with `_same_sha_row('run test', notation='plan-marshall:build-npm:npm')` and `required=_py_footprint_requirement(whole_tree=True)`, `status == 'fresh'` with `scope_cross_check: undetermined` (it is `stale` / `build_scope_narrow` at `9cd644892`);
   - an unknown notation with two positional tokens reads `None`.

   These hold at `9cd644892` and must keep holding: npm `run test --workspace=pkg-a` is NARROW for a whole-tree change and for
   `modules={'pkg-b'}`, and UNDETERMINED with `contributing [0]` for `modules={'pkg-a'}`; Maven `clean install -pl core-api -am` is
   NARROW for a whole-tree change; every pyproject case (L482-505, L507-521, L625-664, L899-958 and the union modules). The L920
   case that models an npm row with the pyproject notation (`'run --command-args test --workspace=pkg-a'`) is changed to an `_NPM` row.

2. **The remedy hint fires only for a row an executor flag actually broke.**
   - `row_scope_remedy_hint` (L734-754) returns the legacy hint for every legacy row with payload tokens that does not parse
     (`module-tests -k foo`, `package -am`, `-pl=,`, an empty `--command-args`), telling the operator to move an executor flag that
     does not exist. It returns the legacy hint only when the tail after the payload carries a declared executor `run` flag
     (`--timeout`, `--mode`, `--format`, `--execution-mode`, `--project-dir`, `--plan-id`, plus `--working-dir` / `--env`) and the
     payload with those flags and their values removed parses.

   *Done when:* each of these fails at `9cd644892`: `row_scope_remedy_hint(_build_entry(args='run --command-args module-tests -k foo'))`
   is `None`. And this holds at `9cd644892` and must keep holding: the existing case at L799-821 stays the legacy hint.

3. **The Surefire report credit counts executed tests, not skipped ones.**
   - `_report_collected_tests` (`build-maven/scripts/_maven_execute.py` L441-445) returns the root `tests` attribute, which counts
     skipped tests, while `_reports_show_executed_tests` (L477-526) claims "executed". Executed is `tests - skipped`, clamped at 0, so a
     `TEST-*.xml` with `tests="3" skipped="3"` does not credit a green zero-execution run. L474 and L522-523 (the time bound) are not
     changed.

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/build-maven/test_maven_execute.py`: a temp project with one
   report `<testsuite tests="3" skipped="3" failures="0" errors="0"/>`, an mtime after the computed start and a log file plus duration
   is not credited as executed. And this holds at `9cd644892`: a report with `tests="3" skipped="0"` is credited.

Split guard: three deliverables. D3 is on a different tool (Maven) and splits off first; D1 and D2 share one module.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The gate gets more precise, never more permissive: a refutation fails closed, an inability passes with its reason.
- The fix keys on the row's own `notation`; no tool is guessed from its arguments.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so, and a row shape is one a discoverer emits.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `parse_row_scope` returns `RowScope(canonical=payload[0], scope_tokens=tuple(payload[1:] + scope))` (`marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` L731); `_row_refusal` judges scope at L805-806 before the canonical at L807-809, the measured-zero check last at L812; `_scope_adequate` L822-833; `_INABILITY_REFUSALS` L819; refutations outrank inabilities at L1035-1053
- OBSERVED: the payloads are tool-native (`_build_examined.py` L44-50): npm `install`, `run clean`, `run build`, `run lint`, `run test` with `--workspace=<m>` or `--prefix=<path>` (`_npm_cmd_discover.py` L327-383); Maven `clean install` (`_maven_cmd_discover.py` L1252), `verify -pl X -am`, `test`; Gradle `spotlessCheck check`, `test jacocoTestReport`, single tokens `build` / `test` (`_gradle_cmd_discover.py` L501-522); pyproject `<canonical> <module>`
- OBSERVED: `build test` is not an emitted Gradle shape (verify is the single token `build`); a Gradle submodule row `:mod:test` reads as canonical-unknown with no scope and passes a whole-tree change as an inability (predates the reorder; not changed here)
- OBSERVED: `row_scope_remedy_hint` fires for `module-tests -k foo`, `package -am`, `-pl=,` and an empty `--command-args`; `_report_collected_tests` returns the Surefire root `tests` attribute
- HYPOTHESIS: the rest of `test_freshness_notation_crosscheck.py` (L80-480, L979 on) and the other `test_pre_commit_verify_freshness_*` modules carry no multi-positional row under a non-pyproject or absent notation that the new rule would flip — read them and run them (verify-at-outline, D1)
- Verify-first clause (D1): reproduce the npm `run test` flip as a fixture at `9cd644892` before editing.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `parse_row_scope`, `row_scope_remedy_hint` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` — `_report_collected_tests`, `_reports_show_executed_tests` (D3)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` and `test/plan-marshall/manage-tasks/_freshness_notation_crosscheck_fixtures.py` (D1, D2)
- OBSERVED: `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` — `_same_sha_row` (D1)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_execute.py` (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-124 (shipped, `landings/PLAN-LB-124.md`).
- Overlaps with: none declared (`manage-tasks/scripts/` and `build-maven/scripts/` are touched by no other staged plan); PLAN-LB-131 edits `manage-status/scripts/_cmd_lifecycle.py`, not these files.
- Adjacent to: `_build_examined.py` (read, correct fail direction, not edited); the Maven zero-test guard `selector_miss_reason` and the `--working-dir` flag drop (L624-626), left on the Watch.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-130-freshness-gate-scope-by-notation.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
