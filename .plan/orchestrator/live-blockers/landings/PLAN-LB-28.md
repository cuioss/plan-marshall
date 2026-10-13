# Landing Analysis: PLAN-LB-28 — Maven build results in Java consumer repositories

epic: live-blockers
workstream: WS-02
pr: #1750 (https://github.com/cuioss/plan-marshall/pull/1750)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-28.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-28-java-consumer-repos-007.md` (kind `landing`, `landing-check`
`complete: true`; surface delta `unmeasured`). Checked against:

- `ci pr queue-state --pr-number 1750`: `pr_state: merged`,
  `merge_commit_sha: 2fd164ec96fee0745746ebc5b7ed751213d5b169`, merge-group run `success`.
- The merge as it fast-forwarded into the ledger worktree: 36 files, 2564 insertions, 60
  deletions.
- A read-only review of commit 2fd164ec9 against deliverables 1–4 (5–8 moved to PLAN-LB-34 on
  2026-10-09) by a delegated agent that ran nothing.

Not read by that review: the diffs of `test_maven_pom_parse.py`, `test_build_parse.py`,
`test_build_format.py`; the seven log fixtures and the reactor POMs beyond their README;
whether the new tests fail against the code before the change; the consumer repositories'
POMs.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 — a module that consumes a reactor test artifact gets a working ladder | shipped, with an allowed deviation | `_maven_cmd_discover.py` `_reactor_test_artifacts` / `_parse_own_dependencies`; `_build_commands` emits `package -pl X -am` for a consumer; `_cmd_client_query.py:137-147` passes `metadata.reactor_test_artifacts`. `package`, not `verify`, as the spec allowed. Half the premise refuted and recorded in `maven-impl.md`: Maven 3.9.16 resolves a plain `<type>test-jar</type>` at `test`; only a custom classifier breaks |
| 2 — test counts are summed across every summary block | shipped, small deviation | `_extract_test_summary` sorts per-class, summary and ambiguous lines; per-runner counts in `by_runner` (executed, not totals; omitted on `-T` builds); ambiguous lines give `population=unmeasured` |
| 3 — javac tags are literal | shipped-as-specified | `_build_jvm_patterns.py:58, 62` escape `[deprecation]` / `[unchecked]`; tests with a control |
| 4 — the failure epilogue is not filed as findings | shipped, with residual noise | `_MAVEN_EPILOGUE_PATTERNS`, `_is_passing_test_count`; captured on Maven 3.8.8, 3.9.16, 4.0.0-rc-7. Header lines (`Failures:`, `COMPILATION ERROR :`, `symbol:`, `location:`) are still filed as issues |

Realized surface against the declared one: every declared file was touched. Outside the
declaration: `_build_format.py` (TOON projection of the two new fields),
`extension-api/standards/build-execution.md` (a table of the optional `tests` fields, consistent
with the code), and four test modules. The request excluded `extension-api` edits; the
self-review's contract-drift fix crossed that line and no operator decision was recorded.
`_build_shared.py`, which the re-scope expected to drop out, was needed for `_measured_executed`.

## What the plan achieved against its objective

- **Deliverable 1 reaches a consumer only after discovery is re-run there.** Detection is
  persisted in `metadata.reactor_test_artifacts` at discovery; a consumer's existing
  architecture data lacks it, so TokenSheriff and API-Sheriff keep `test -pl X -am` until
  discovery is re-run after the harness sync. Detection reads only the module's own
  `<dependencies>` — a dependency declared in a parent POM, a profile, or through a property
  is missed and the old command kept.
- **The evidence is fixture-only.** Every log is a synthetic probe capture; none of the
  consumer figures that motivated the plan is in a test, and no test runs Maven.
- **Fail-closed where it matters, with one gap.** No summary line, a quiet log, or per-class
  lines only read as `unmeasured`, not zero. A truncated or killed reactor log that holds only
  some modules' summaries is summed and stamped `measured` — a silent under-count.

## Metrics and Anomalies

- Tokens: 6,931,627 (the retrospective counts 6.09M against a 2.0M budget). Wall 28,055 s.
- Self-review: closed with 3 advisory findings after one loop-back for the JSON-versus-TOON
  drift — the only control that caught it.
- Phase 5: 4 of 7 dispatches ended in a hand-back after a leaf started a build its stamped
  timeout said would fit and the live estimate did not; 1h56m idle of 3h47m.
- All 28 dispatch-boundary rows keyless: fifth landing in a row.
- `sonar-roundtrip`: `internal_error` instead of `unconfigured` in a checkout with no Sonar
  (lesson `2026-10-10-21-001`, filed by the plan itself). The plan also filed
  `2026-10-10-21-002` (an order-dependent build-server test).
- CodeRabbit found a fixture whose test-jar classifier the producer never attached; fixed in-run.
- Sourcery (optional) refused on quota; required bots participated.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1750; `landing`; `plan_marshall_plan_id`
  lb-28-java-consumer-repos
- [x] epic.md queue annotation, Open Defects, drain recorded
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- Re-run architecture discovery in the Maven consumer repositories after the harness sync, or
  deliverable 1 does not take effect there.
- A partial reactor log is summed as measured.
- Epilogue header lines still filed as issues.
