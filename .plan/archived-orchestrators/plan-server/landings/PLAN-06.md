# Landing Analysis: PLAN-06 — Route pyproject builds through the daemon

epic: plan-server
workstream: WS-01
pr: #979 — https://github.com/cuioss/plan-marshall/pull/979 (merged 2026-07-22, squash via merge queue, `7c6554d12` on origin/main)

> Landing record. Claims verified against ground truth (merged diff `7c6554d12`, live
> `_build_execute_factory.py` / `_pyproject_execute.py` / `_marshalld_supervisor.py` source,
> PR state via the CI abstraction) — not the paste.

## Deliverable Fidelity vs Spec

The spec listed 3 deliverables; the plan shipped 4 (deliverable 4 added mid-execute,
operator-approved). All verified in-tree.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — route pyproject through the factory routing path, preserving self-heal; forward `plan_id`/`execution_mode`/`env_vars`/`working_dir` | shipped-as-specified | `_build_execute_factory.py` +additive keyword-only `wrap_execute_fn=None`; `in_process_execute = wrap_execute_fn(execute_direct) if wrap_execute_fn else execute_direct`; the routing `cmd_run` in-process leg now calls `in_process_execute`. `_pyproject_execute.py` (153 lines) drops its local `cmd_run`, supplies the `.pyprojectx` self-heal via `wrap_execute_fn`, rides the shared routing path. `pyproject_build.py` (+8) registers `--env`/`--working-dir`. Self-heal preserved on the routed leg too (daemon child re-enters the factory and applies the wrapper). |
| D2 — regression tests (routing / self-heal fallback / plan-less / daemon fail-loud) | shipped-as-specified (+expanded) | New `test_pyproject_routing.py` (+410); `test_pyproject_execute.py` (+112). Whole-tree module-tests 14764 passed, coverage 82.12%. |
| D3 — doc note: pyproject routes like the other adapters | shipped-as-specified | `doc/developer/build-architecture.adoc` (+2), `build-pyproject/SKILL.md`, `extension-api/standards/build-api-reference.md` updated for the routing seam + new flags. |
| D4 — routed-build terminal status truthful | added-unplanned (operator-approved mid-execute) | `_marshalld_supervisor.py` (+86): exit 0 is now NECESSARY-BUT-NOT-SUFFICIENT for `success` — `read_log_verdict` reads the emitted build-TOON verdict and `run_job` downgrades a `success` to `failure` (carrying the TOON `exit_code`) when the verdict does not affirmatively agree. `timeout`/`killed` legs untouched; a log with no parseable TOON keeps the exit-code verdict (non-wrapper commands unaffected). |
| ADDITIVE-SEAM byte-identity guard (maven/npm/gradle) | verified | `wrap_execute_fn=None` → `in_process_execute` IS `execute_direct` (object identity), so the shared `cmd_run` is unchanged for the three other adapters. |

## Metrics and Anomalies

- Tokens: 2.5M
- Duration: 2h24m worked / 4h45m wall
- Anomalies: the mid-execute discovery of the routed-build false-green (D4) is the notable
  event — a pre-existing daemon defect that deliverable 1 was the first to expose this repo's
  own verify gates to. It reproduced live TWICE during the run, once catching a red tree the
  executing agent would otherwise have committed. Not a cost anomaly.

## Routing and Merge Behavior

- Review: 1 CodeRabbit reviewer, 2 comments → BOTH declined; review-retrospective noted high
  signal-to-noise. CI green at `78d01b5`. Merged via the merge queue (squash); rebased onto
  origin/main (2 upstream commits); worktree removed; archived
  `.plan/local/archived-plans/2026-07-22-pyproject-routing-integration`.
- Test-organization defect caught at the merge gate (operator chose to fix, not defer): TASK-006
  created `test_supervisor.py` on the false premise that no supervisor test module existed —
  `test_marshalld_supervisor.py` already existed. Consolidated before merge. Verified: the merged
  tree carries only `test_marshalld_supervisor.py` (+132), no `test_supervisor.py` (the PR body's
  mention of the latter is a stale generated line).
- deploy-target v0.1.1190, 1112 files, 10 bundles synced, executor regenerated at finalize.
- lessons-capture: 1 recorded (`2026-07-22-12-003`, the supervisor false-green), 2 merged, 1 routed;
  lessons-housekeeping removed 1. Closed lesson `2026-07-21-14-001` (worktree-routing) — this plan
  was its fix.
- No cross-epic collision materialized: the predicted PLAN-32 rebase adjacency on
  `script-shared/scripts/build/` did not fire (the additive `wrap_execute_fn` param was a clean
  local extension).

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-06 → shipped, pr `#979`, landing `landings/PLAN-06.md`
- [x] epic.md Ordered Queue row PLAN-06 → shipped
- [x] Open Defect "pyproject-routing-bypass" → RESOLVED (thesis realized; `resolved=routed` live)
- [x] OBSERVED-NEGATIVE / worktree-routing watch → CLOSED (routing proven POSITIVE, not just explained)
- [x] New Watch opened: running daemon executes the PRE-FIX supervisor until restarted (D4 not live yet)
- [x] Cross-epic note: D4 (daemon terminal-status truthfulness) is adjacent to the #909/PLAN-32 thread
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **⚠ OWED (operator): restart marshalld against the merged bundle (v0.1.1190).** The running daemon
  still executes the PRE-FIX supervisor, so a routed build's terminal status can still be false-green
  until the restart. Until then, read JOB LOGS (which carry the truthful build-TOON verdict), not the
  outer build status. `manage-build-server` restart/upgrade against the synced cache. Recorded to
  memory by the plan.
- **Cross-epic (relay adjacency):** D4 fixed the daemon-side terminal-status truthfulness (routed
  `success` must agree with the log verdict). This is the daemon-local sibling of the #909/PLAN-32
  route-agnostic terminal-status-correctness thread — worth folding into the relay to the
  plan-optimization orchestrator so PLAN-32 knows the daemon path already has its own verdict-narrowing.
- **Epic status:** WS-01 staged queue is DRAINED and the epic's core thesis is realized. Closeability
  is an operator decision (surfaced), gated on whether to hold for the daemon-restart confirmation +
  the #909 relay.
