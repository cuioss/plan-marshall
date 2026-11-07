# PLAN-LB-124: The push gate and the Maven guard stop passing or blocking wrongly

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-124-push-gate-and-maven-guard-truth-fixes.md` and is queued as one row file, `queue/PLAN-LB-124.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's ruling of 2026-11-07 (decision 19, option 2: one merged plan for the push-gate rows and the Maven guard).
> It is the fix plan for PLAN-LB-120 (PR 1923, merge `b4430a0a6`; `landings/PLAN-LB-120.md`, Layer 3 L3-1, L3-3 to L3-6 and the
> ten round-2 items under Layer 2 C7) and PLAN-LB-121 (PR 1929, merge `74ddc39a8`; `landings/PLAN-LB-121.md`, L1-2, L1-6, L1-9,
> L1-10, L3-1 to L3-5, L3-7). Finding ids are those reports'. It is eight deliverables, above the six-deliverable guard, on the
> operator's word; the split order is recorded below. Points re-read at `5cd8ccd92` are OBSERVED; the rest are HYPOTHESIS, settled
> first.
>
> Ruling check. Stop rule: a fix plan is warranted only for a major that fails open or falsely blocks a gate in normal use; the minors
> ride along on files being touched. D1 is a fail-open, D2 and D3 are false blocks, D4 is a false block, D5 is a silent pass; D6 to
> D8 are minors on files D1 to D5 touch. No token or measurement work. No Sonar.

## Objective

PLAN-LB-120 made the push gate read a build row's scope and refuse an unreadable row for a whole-tree change. PLAN-LB-121 made a
Maven reactor root run only the tests it builds and turned a summary-less green `test` run into `indeterminate`. Reading the merged
code found that the push gate files a Maven `-pl X` row as an inability before it looks at the scope, so it passes a whole-tree
change; that a whole-tree row with a trailing executor flag is refused with a remedy that loops; that the zero-test guard stops a
legitimate green whose summary cannot be seen; that a standalone POM gets a `-pl` command Maven cannot run from the root; and that an
unreadable POM passes silently.

After this plan scope is judged first wherever it is readable, the executor's own flags are told from the payload's, a run that
collected nothing is told from a run whose summary is hidden, every Maven module gets a command that can run or none, and an
unreadable POM is a named stop.

## Deliverables

1. **The push gate judges a readable scope before the canonical.** *(L3-1 of PLAN-LB-120; major, fail-open)*
   - `_row_refusal` returns `ROW_CANONICAL_UNKNOWN` (`_freshness_crosscheck.py:746-748`) before the scope check (`:751-755`), and
     an all-inability candidate list is `UNDETERMINED` with `build_scope_unreadable` (`:979-989`), which passes. Maven `test` and
     `package` are outside `CANONICAL_ANALYSES` (`_build_examined.py:97-106`), so `test -pl X -am` passes a whole-tree change.
     `_scope_adequate` (`:766-777`) decides it without the vocabulary. `ROW_TESTS_EXECUTED_ZERO` is also checked after the canonical
     (`:756-757`).
   - Decide at outline: scope is judged first for a row whose scope tokens are readable; the canonical-unknown inability stays only
     where scope does not decide. The outline also decides whether the measured-zero check moves with it, and records both.
   - `required_coverage` and `CANONICAL_ANALYSES` are not changed.

   *Done when:* through `cross_check_candidates`, a whole-tree change whose only candidate is `run --command-args test -pl core-api
   -am` is `narrow` with `build_scope_narrow` (red at `5cd8ccd92`), and the same for `package -pl core-api -am` (red); `verify -pl
   core-api -am` stays `narrow` (control); whole-tree `verify` stays `covered` (control); a change inside `core-api` with the
   `test -pl core-api -am` row is not refused (control); a whole-tree `test` row stays `undetermined` (control).

2. **A whole-tree row with a trailing executor flag is read, or refused with a remedy that works.** *(L3-3, L3-8 of PLAN-LB-120;
   major, false block)*
   - `parse_row_scope` makes any unknown flag after `--command-args` unreadable (`_freshness_crosscheck.py:615-627,663-667`), so
     `run --command-args verify --timeout 900` and `verify --format json` (the documented shape, `build-execution.md:399-400,407-408`)
     cannot certify a whole-tree change, and the consumer's generic remedy (`_cmd_pre_commit_verify_freshness.py:511-513`) can loop.
     Flags placed before `--command-args` are read (`:644-652`).
   - Settled by reading: the writer can tell the flags apart. `_append_build_ledger_record` holds `script_args: list[str]` and joins
     it only at the record (`execute-script.py.template:1032,1087`), so the `--command-args` value is one element there. The row
     records that value as its own field (`_ledger_core.build_record`), and `parse_row_scope` reads it when present. Flags inside the
     value (`-Ppre-commit`, `-k foo`) stay unreadable.
   - Old rows and executors not regenerated keep today's reading, so the refusal also names the exact remedy (put the executor flag
     before `--command-args`, or drop it) in the message, and `manage-tasks/SKILL.md` states it once.

   *Done when:* a row recorded with the new field `verify` and `args` `run --command-args verify --timeout 900` certifies a whole-tree
   change (red at `5cd8ccd92`); the writer, given argv `run --command-args "verify plan-marshall" --format json`, records the value
   `verify plan-marshall` (red); a field `module-tests -k foo` stays unreadable (control); an old row without the field gets the named
   remedy, not the generic one (red); `verify` with no flag stays whole-tree (control).

3. **The zero-test guard tells "collected nothing" from "summary not visible", and both gates have a route.** *(L3-1 of PLAN-LB-121;
   major, false block)*
   - `apply_zero_test_guard` turns a summary-less green leading `test` run into `indeterminate` (`_maven_execute.py:430-445`). The
     pre-push gate STOPs on `indeterminate` in branches 4 and 6 (`pre-push-quality-gate.md:493,516`); the per-task gate names only
     pass and fail (`execute-task/SKILL.md:163-173,313`).
   - Reproduction cases: a module whose `src/test/java` holds only helpers (`has_tests=test_files > 0`,
     `_maven_cmd_discover.py:488,498`); `.mvn/maven.config` carrying `-q`/`--quiet`; Surefire `printSummary=false`.
   - Decide at outline and record: read the Surefire/Failsafe report files, or the `Tests run:` line only where it is printed at
     WARN level; stop granting the canonical to a module with no test classes; or keep the stop and give both gates a named route.
   - The per-task gate gets a route for `indeterminate` with a named reason.

   *Done when:* each reproduction case is a fixture red at `5cd8ccd92` and gives the decided answer; `maven-test-no-summary.log`
   (an aggregator that builds nothing) and `maven-zero-tests-executed.log` stay `indeterminate` (controls); a run with a summary stays
   `success` (control); a doc test shows the per-task gate and branches 4 and 6 name the route (red).

4. **A module outside the root's reactor gets a command that runs, or none.** *(L3-2 of PLAN-LB-121; major, false block)*
   - `_build_commands` gives every non-root module `-pl {relative_path} -am` on every canonical (`_maven_cmd_discover.py:1126,
     1132-1139,1146-1153`) without knowing reactor membership, which pass 3 alone knows (`:276-283,318-348`). The test pins
     `examples` to `test -pl examples -am` (`test_discover_modules.py:776`). The affected canonicals are all of verify, install,
     compile, package and test, not only `test`.
   - Decision: a module outside the root's reactor gets canonicals that run in its own directory, or none. If the own-directory form
     uses a flag the push gate does not know (`-f`), D1/D2's reader is extended or the unreadable result is pinned.
   - The pinned test is rewritten with a docstring saying why.

   *Done when:* the standalone-`examples` fixture gives `examples` no `-pl` canonical (red at `5cd8ccd92`); a reactor member keeps
   `test -pl core -am` (control); a root that is no `pom` aggregator is pinned either way with its reason.

5. **An unreadable POM is a named stop.** *(L1-9 of PLAN-LB-121; major, silent pass)*
   - `_parse_pom_xml` turns a parse or read error into `packaging: jar`, `modules: []` (`_maven_cmd_discover.py:636-648`); the root
     loses its canonicals and the gate records DEGRADED and passes.
   - Decide at outline: a named, logged reason in the discovery result and the gate record.

   *Done when:* a malformed root POM yields the named reason in discovery and the gate record (red at `5cd8ccd92`); a well-formed
   POM carries none (control).

6. **The guard's false negatives and the reactor under-grants.** *(L1-6, L3-3 to L3-5, L3-7 of PLAN-LB-121; minor)*
   - The skip marker is a substring of the whole log (`_maven_execute.py:436`); a fully-qualified `g:a:v:test` goal fails
     `_PLUGIN_GOAL_PATTERN` (`:119,359`) and is unguarded; an exit-0 Failsafe `-Dit.test` miss under `verify` is undetected and absent
     from the recorded limit (`build-maven/SKILL.md:86`).
   - The reactor resolution under-grants for `<module>child/pom-alt.xml</module>` and `${prop}` (`_maven_cmd_discover.py:305-315`),
     Maven 4.1 `<subprojects>` (`:690-742` reads `modules` only), and modules under `build`/`target` (`_build_discover.py:30`, shared:
     do not edit; name the under-grant Maven-side). Each is resolved or a named, logged under-grant.
   - `build-maven/SKILL.md` states once that a daemon not reconciled to the new code does not run the guard.

   *Done when:* each false negative and under-grant is a fixture red at `5cd8ccd92`; the SKILL sentences are read.

7. **The refusal hints and the bounded probe.** *(L3-4 to L3-6 of PLAN-LB-120; minor)*
   - The head-binding refusal (`pre_merge_gate.py:586-592`) names `loop-back close --waive-refire` at the candidate head.
   - `_head_dependence_probe()` scans eagerly at `:536` (it calls `_finalize_step_population()` at `:412`) before any record is
     known stale; it runs at the first stale declared record, with a bound.
   - `_fact_map` accepts any key (`:1397-1405`) and `record_merge` passes facts through (`:1513-1518`): the key is checked against
     the step's `records_facts` (`branch-cleanup.md:9-22`); `head_binding_status_read_fault={the fault text}` (`:1662`) is quoted or
     encoded.

   *Done when:* the refusal for an absent step names the waiver (red); a merge with no stale record runs no scan (red); a misspelled
   key is refused (red) and every declared key is accepted (control); a fault text with a quote and a newline is recorded intact.

8. **The documentation items.** *(C7 items 1-10 of PLAN-LB-120; L1-2, L1-10 of both)*
   - `manage-tasks/SKILL.md:616` sits outside the indented table `:605-615`; `:482` puts the joint token in the
     `scope_cross_check_reason` table; `:583-587` omits the unreadable-for-whole-tree route; `:593-596` and
     `_cmd_pre_commit_verify_freshness.py:125-127` say `missing_analyses` is what to run where that route returns it empty (with D2).
   - `test_freshness_notation_crosscheck.py:620-622` banner "Every scope inability passes"; `:635-636` a test name split across a line.
   - `test_lb55_merge_head_binding.py:83-88,291-293` "at HEAD"; `LB-100` in its `_merge` docstring; the test docstrings "Swallowing it
     left…", "A silent None… was an empty admit", "Treating that as a pass let…".
   - `branch-cleanup.md:845` states `override_options[]` unconditionally.
   - History wording: `_freshness_crosscheck.py:178` ("historically"), `pre_merge_gate.py:1489` ("used to"), and the other sites the
     lane finds.
   - `extension_discovery.py:1032-1034` contrasts two synonyms ("no such declaration" / "undeclared").
   - `fixtures/log-test-data/README.md:55` describes the old behaviour; `test_discover_modules.py:742-751` (the rewritten control) is
     labelled a correction.

   *Done when:* a read of each cited line shows it corrected; the PR names the lines read.

Split guard: eight deliverables, above the six-deliverable guard on the operator's word. D1 to D5 are the core. Split off first if
the PR grows, in this order: D8, then D7, then D6. A split runs in sequence: D1, D2 and D8 share `_freshness_crosscheck.py`; D3 to D6
share the Maven discovery and execute modules.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **The gate gets more precise, never more permissive.** Every relaxation (D2's field, D3's route) ships with a control showing a
  genuinely narrow row or a run that collected nothing still blocks.
- **Keep the split fail-direction.** A refutation fails closed; an inability passes with its reason, except the whole-tree
  unreadable refusal. `required_coverage` and `CANONICAL_ANALYSES` are not changed.
- **No shared build file.** Do not edit `_build_execute_factory.py`, `_build_server_protocol.py`, `_build_shared.py`,
  `_build_result.py`, `_build_cli.py` or `_build_discover.py`; a change that needs one is recorded as owed to a follow-up of
  PLAN-LB-115.
- **Fail closed.** An unreadable log or POM is a named stop, never a pass.
- **No real Maven invocation.** Every Maven test is a log or POM fixture naming the Maven/Surefire version it reproduces; Maven's
  rejection of `-pl` outside the reactor is from knowledge and the fixture shows the emitted command only.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so; a rewritten control is
  labelled a correction; counts come from an enumeration.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: `_row_refusal` checks parse, canonical, analyses, scope, zero tests in that order —
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` L743-758; inabilities are
  `_INABILITY_REFUSALS` (L763) and give `UNDETERMINED` (L979-989); the whole-tree unreadable refusal re-reads only `parse_row_scope`
  (L1110-1151).
- OBSERVED: Maven `test`/`package` are absent from `CANONICAL_ANALYSES` —
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py` L97-106.
- OBSERVED: the ledger row's `args` is `' '.join(script_args)` over a `list[str]` —
  `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` L1029-1037, L1087;
  `build_record` has no field for the `--command-args` value — `manage-change-ledger/scripts/_ledger_core.py` L137-228. The
  seam row `_append_gate_build_row` carries `worktree_sha=None` (`_build_execute_factory.py` L525-531), so it is never a candidate.
- OBSERVED: the consumer's remedy is generic when `missing_analyses` is empty — `_cmd_pre_commit_verify_freshness.py` L502-513.
- OBSERVED: the guard body and its skip marker — `build-maven/scripts/_maven_execute.py` L382-445; the goal pattern L119, L359.
- OBSERVED: STOP on `indeterminate` — `phase-6-finalize/standards/pre-push-quality-gate.md` L493, L516; the per-task gate names pass
  and fail only — `execute-task/SKILL.md` L163-173, L313.
- OBSERVED: `-pl … -am` for every non-root module, `module-tests` from `has_tests` — `build-maven/scripts/_maven_cmd_discover.py`
  L488, L498, L1126-1153; the unreadable-POM default L636-648; reactor resolution L276-283, L288-348; `modules` only L690-742.
- OBSERVED: the probe scans at construction — `phase-6-finalize/scripts/pre_merge_gate.py` L395-434, L536; the refusal text
  L586-592; `_fact_map` L1397-1405; `record_merge` passes facts through L1513-1518.
- HYPOTHESIS: with `-q`, a green Surefire run prints no `Tests run:` summary (INFO level); with `printSummary=false` likewise — from
  knowledge; the shipped quiet fixture is a failure (`[ERROR] Tests run:`, README L43). Confirm with a captured or documented log
  shape (verify-at-outline). It decides D3's reach.
- HYPOTHESIS: `count_source_files` counts every source file under the test directories, so a helpers-only `src/test/java` sets
  `has_tests` — confirm at `script-shared` `count_source_files` (verify-at-outline).
- HYPOTHESIS: Maven rejects `-pl` naming a project outside the reactor — from knowledge (verify-at-outline; no real run).
- HYPOTHESIS: nothing downstream of `record-merge` (`mark-step-done`) checks a fact key against `records_facts` — confirm at
  `manage-status` § mark-step-done (verify-at-outline).
- HYPOTHESIS: moving the scope check first changes no verdict PLAN-LB-121 relies on (its root canonicals carry no scope) — confirm
  against its tests (verify-at-outline).
- Verify-first clause (D1, D2, D4, D5): reproduce each shape as a fixture at `5cd8ccd92` before editing; one that does not reproduce
  is reported and its Done-when narrowed in the PR.
- Verify-first clause (D3): record the outline's decision with the evidence for each reproduction case before changing the guard.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — check order, field reader, comments (D1, D2, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — the remedy, the docstring (D2, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — the remedy sentence, the tables (D2, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — the row writer (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` — `build_record` (D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` — Maven shapes, field, remedy (D1, D2, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` — the guard (D3, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` — canonicals, POM parse, reactor (D3, D4, D5, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — the limit, the daemon sentence (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — branches 4 and 6, the DEGRADED record (D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — the `indeterminate` route (D3)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_execute.py` — guard fixtures (D3, D6)
- OBSERVED: `test/plan-marshall/build-maven/test_discover_modules.py` — L776 and the control (D4, D5, D6, D8)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_pom_parse.py` — the unreadable POM (D5)
- OBSERVED: `test/plan-marshall/build-maven/fixtures/log-test-data/README.md` — new fixtures, L55 (D3, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — refusal, probe, facts (D7, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — L845, L1662 (D7, D8)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` — probe, keys, refusal (D7)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb55_merge_head_binding.py` — docstrings (D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — docstring only (D8)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` — only if it documents the row shape (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-execution.md` — only if flag placement is documented there (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-change-ledger/test_manage_change_ledger.py` — the field (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/test_generate_executor.py` — the writer test, if it lives there (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py` — the consumer message (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_finalize_maven_reactor_root_test_canonical.py` — the gate route (D3, D5; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merges of PLAN-LB-120 (`b4430a0a6`) and PLAN-LB-121 (`74ddc39a8`), both on the base branch.
- **PLAN-LB-115 (running):** edits `_build_execute_factory.py` and the routed legs that carry the Maven `indeterminate` reasons
  (`test_run_executed_nothing`, `test_log_unreadable`). No shared file by the lists: this plan edits none of its seven files. D3
  must not edit a shared build file; a need is owed to a PLAN-LB-115 follow-up. If D3 adds a reason, its routed carry is owed there.
  Directory overlap only: `test/plan-marshall/script-shared/` (this plan edits no file there).
- **PLAN-LB-123 (running):** edits `manage-tasks/scripts/_tasks_query.py`, `manage-tasks/scripts/manage-tasks.py` (hypothesis) and
  the directory `test/plan-marshall/manage-tasks/`. This plan edits neither script; it edits
  `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` and possibly `test_pre_commit_verify_freshness.py`. No
  shared file is named; the overlap is directory-level. It reads `execute-task/SKILL.md`, which D3 edits.
- **Parked PLAN-LB-75:** declares the directory `test/plan-marshall/phase-6-finalize/` and no file in it; this plan edits
  `test_pre_merge_gate.py`, `test_lb55_merge_head_binding.py` and possibly `test_finalize_maven_reactor_root_test_canonical.py`
  there. Re-ground PLAN-LB-75 before it is un-parked. **Parked PLAN-LB-46** shares `branch-cleanup.md`.
- **Adjacent to** (left untouched): `required_coverage`, `CANONICAL_ANALYSES`, the waiver writer, `_append_gate_build_row`.
- **Owed outside this plan, operator-run:** a harness sync; an executor regeneration in every project (D2 changes the executor
  template); a daemon reconcile so the routed child runs D3 and D6.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-124-push-gate-and-maven-guard-truth-fixes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
