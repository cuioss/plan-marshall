# Landing Analysis: PLAN-LB-73 — state each rule once, make the stale-executor guard real

epic: live-blockers
workstream: WS-04
pr: #1843 (`3873b6695`, base `main`, merge queue)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> **(re-read)** = re-checked by the orchestrator in git, the CI abstraction, the Sonar read or the run's evidence files.
> **(landing)** = stated by the landing message and not independently reproducible here (test runs are not re-executed).
> **(progress)** = read from `.plan/temp/rb-lb-73-lb-72-completion/progress.md`.
> Token usage is out of scope by the 2026-10-23 ruling and is not analysed.

## Verdict

Runbook lane, `deepseek-v4.1-flash/high`, ~8 h 33 min wall clock (05:30Z start, 14:03Z landing) **(progress)**. All four
deliverables landed; the merged tree carries every mechanism the landing claims, and the PR/merge/Sonar facts all
corroborate. The report is unusually honest about its own conduct: it discloses two shell file operations and one
guard-logged R1 line, reports `complete: false` on `total_tokens` rather than guessing, and names its un-measurable
`executor-skew` surface error instead of papering over it.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 §7 — a clean summary review qualifies; rule stated once; merge-gate question re-reads the surfaces | shipped-as-specified | `runbook-lane/SKILL.md` carries the §7 re-read and the marker-bearing summary-comment rule **(re-read: grep of the merged tree)**; CodeRabbit published the marker-bearing review at 10:47:35Z and 12:00:34Z **(re-read: `ci pr reviews`)** |
| D2 — tests that can fail for the reason they name | shipped-as-specified | `test/plan-marshall/runbook-lane/test_runbook_lane.py` in the merged diff **(re-read: diff)**; red/green evidence cited by log and sha **(landing)** |
| D3 — the lane refuses a stale executor | shipped-as-specified | `executor-skew` subcommand present at `runbook_lane.py:1933` and documented at `SKILL.md:51-57` **(re-read: grep)**; comparison delegates to `plugin_registry` **(landing/progress: `plugin_registry.py:224-246`)** |
| D4 — the build gate and `resolve` state only what is true | shipped-as-specified | `build-routing` at `runbook_lane.py:1936`, `executor_absent_from_worktree` reason at `:1377`, `build_missing_canonicals` at `:1784`, §0a/§8 text in `SKILL.md` **(re-read: grep)** |

Claimed `deliverables_done=4` of 4; the table agrees. The 23 Done-when verdicts are the run's own
(`self-review round 3: 23/23`) **(landing)** and were not re-executed: the prime directive forbids an implementation
build from this verb.

**Surface.** Declared 7 entries; realized 3 (`runbook-lane/SKILL.md`, `runbook-lane/scripts/runbook_lane.py`,
`test/plan-marshall/runbook-lane/test_runbook_lane.py`) **(re-read: `git diff --name-only 3873b6695^1 3873b6695`)**.
`added_count=0` — no in-flight expansion, so no under-declaring spec needs correcting. The four declared-but-untouched
entries (`coderabbit.md`, `plugin_registry.py`, `_build_execute_factory.py`, `git-workflow.py`) are **over-declaration**:
the work reads those modules but changes none of them. The gate predicted no collision and none occurred.

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none, which is the only missing required key. **Not recorded as a defect or
  recurrence**: the 2026-10-23 ruling makes a `total_tokens`-only `complete: false` out of scope. The rest of the key set
  closed exactly as PLAN-LB-78 D3 predicted (`effort=high` and `plugin_version=0.1` are now supplied).
- Duration: 2026-10-23T05:30Z to 14:03Z (≈8 h 33 min) **(progress)**; one server restart at 12:06Z, after which the
  lane text and the progress file were re-read and the killed `verify` re-run **(progress)** — the re-read obligation
  the previous two runs missed was met.
- Anomalies: a learned 556 s `module-tests` bound expired once; the run repeated with `--timeout 1283` and went green.
  One mypy `no-any-return` broke `verify` on the first head and was fixed in `b69e35b3a`.
- Build server: every build ran `in_process` with `executor_absent_from_worktree` — the defect PLAN-LB-92 owns, observed
  live here rather than only by code reading.

## Routing and Merge Behavior

- Review: CodeRabbit, 8 review records, 2 formal findings rounds — 10:47:35Z on `b69e35b3a` (3 findings) and
  12:00:34Z on `39701dea8` (1 finding); all four fixed, replied, resolved **(re-read: `ci pr reviews`; progress)**.
  Re-triggers after `25b3eac30` and `e1b94faf4` were refused on the rate window, which is what the standing
  authorization covers. Sourcery refused on its diff-character quota at every trigger; it is optional and does not gate.
- CI/merge: `verify` green on every head after `b69e35b3a`; merged through the merge queue at
  `3873b66952ccfc20eb2a784d2993165bae77ad64` **(re-read: `ci pr view`, `git merge-base --is-ancestor`)**, with the
  `Co-Authored-By: plan-marshall` trailer present **(re-read)**. No rebase conflict and no re-verify signal: the
  declared surface touched nothing the two in-flight plans own.
- Sonar: `step.sonar-roundtrip.open_issue_count=0`, `open_issue_rules=none` in the landing; re-read against the service
  for PR #1843 gives `count_status: confirmed`, `open_issue_count: 0`, no rules **(re-read)**. Agreement — the first
  runbook landing whose figure the orchestrator could verify, and it holds.
- Guard/conduct: the disclosed line is present in `.plan/temp/guard.log:175` (R1, session `ses_e98677197ffe4V4p6hVBRC3wcS`,
  the self-review child's `git log`) **(re-read)**; no refusal blocked a step, and the two shell file reads it reports
  were not logged because the guard does not cover read-side probes.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-73 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-73 --field pr --value 1843`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-73 --field landing --value landings/PLAN-LB-73.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-73 --field plan_marshall_plan_id --value lb-73-lb-72-completion`
- [x] epic.md narrative reconciled: the §7 qualifying-review defect and the merge-gate re-read defect retired; the
  install-lag Watch refreshed (the installed OpenCode lane now carries the new verbs); the landing's executor-surface
  residue recorded on the executor defect as **reported, then contradicted** (both verbs resolve here)
- [x] `total_tokens` incompleteness **not** recorded as a defect: the 2026-10-23 ruling puts a `total_tokens`-only
  `complete: false` out of scope
- [x] resume anchor updated in `resume_anchor.md` — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] `queue-view.md` regenerated and committed with the row change — `orchestrator regenerate-view`

## Follow-Ups

- **PLAN-LB-92 is unblocked.** The operator ordered it held until this landing because the two share four files; with
  `PLAN-LB-73` terminal, the shared surface is no longer in flight. Emitted below.
- **The executor surface cache still predates `executor-skew` / `build-routing`.** Invoking either through the
  main-checkout executor answers `unknown_verb` until it is regenerated; the lane now classifies exactly that as skew.
  Folded into the existing "main executor does not know `<verb>`" defect, whose remedy is unchanged
  (`marshall-steward`, then `/sync-harnesses`).
- **No new spec staged.** The residue the landing names (flat-install `could_not_check`, accepted low-severity review
  items) is either the spec's own could-not-check arm or below the focus rule.
- **One landing residue claim is contradicted, and it is recorded rather than repeated.** The landing says
  `executor-skew` / `build-routing` are absent from the executor's surface cache and answer `unknown_verb`; both resolve
  their real argument surfaces when re-run at analysis **(re-read)**. Not a defect. The genuine half — a runbook worktree
  carries no executor, hence `executor_absent_from_worktree` on every build — is PLAN-LB-92's subject.
- **The install-lag Watch is satisfied for this cycle by content**, not by an observed sync: the installed OpenCode lane
  carries both verbs #1843 introduced **(re-read)**.
