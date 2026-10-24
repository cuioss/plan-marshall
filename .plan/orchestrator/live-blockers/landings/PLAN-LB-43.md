# Landing Analysis: PLAN-LB-43 — A dispatched leaf resolves its workflow document in a consumer repository

epic: live-blockers
workstream: WS-04
pr: #1851 (`aa804dccf`, merge queue, base `main`)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction or `guard.log`.
> **(store)** = read from the OpenCode session database, read-only (counts, tool names, command words, paths, times; no
> message text). Nothing was executed. Token usage is out of scope by the 2026-10-23 ruling. The correctness of the new verb,
> the recovery path and the target stamp was not re-executed: it rests on the PR's tests and green CI.

## Verdict

**Grade: B−.** Plan-marshall lane via the runbook lane skill, `deepseek-v4.1-flash/high` throughout **(store)**, 25 h wall
clock (2026-10-23T15:15:18Z to 2026-10-24T16:16:40Z), the longest run of the series.

The product is complete and well evidenced: all five deliverables are met as the landing states them, 31 files (+1898/-264)
merged, CI green, no review thread open **(re-read)**. The process is the best-behaved on restarts so far: the lane text was
re-read after each of three server restarts. What holds the grade down is conduct the landing under-reports: twelve edits to
tracked files, production code included, were made in the MAIN checkout in the first 25 minutes, and the landing discloses only
an untracked test draft; three restarts and one guard refusal are missing from the report; and its "no shell file operations"
statement does not match the store.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 One verb resolves a workflow notation to a verified path | shipped-as-specified | `extension_api.py` verb and `test_extension_api_resolve_workflow.py`; four forms covered (worktree copy, newest version, flat layout, `workflow_not_found` with both probes) |
| D2 Agent Step 4 uses the verb; the standard states the order | shipped-as-specified, test-first | red run cited (6 failed); three generated variants carry Step 4 |
| D3 A broken executor is recovered by a path it can reach | shipped-as-specified, `mutation-after` | `executor_recovery`, `regenerate_failed`, warning precedence, probe environment |
| D4 An OpenCode consumer install reaches a freshness verdict | shipped-as-specified, `mutation-after` | flat install with and without manifest, staleness from the readable pair, `install.sh` publication |
| D5 A foreign-target executor is refused by name | shipped-as-specified, `mutation-after` | `executor_target_mismatch`, stamp in the generator and in `status.metadata` |

Claimed `deliverables_done=5` of 5; the table agrees. D3 and D5 hypotheses were refuted in part (a target stamp already
existed; the plugin-root stamp and the comparison did not), which the landing reports.

**Surface.** The spec declared 17 entries; the PR diff has 31 files **(re-read)**. Beyond the declaration, the landing names
`_cmd_lifecycle.py` and `test_manage_status_create.py` (D5), `machine-global-config-scope-audit.md` (D3), `install.sh` and
`sync.py` (D4) and `test_guard_exact_admissions.py` (D3). The path-level delta was not measured in this analysis.

## Findings by the orchestrator

- **Undisclosed tracked-file edits in the MAIN checkout** **(store)**: at 15:35Z to 15:38Z on 2026-10-23 the root session made
  8 edits to `extension_api.py`, 2 to `extension-api/SKILL.md`, wrote `test_extension_api_resolve_workflow.py` (2 edits) and
  3 further edits to the extension API, all by absolute main-checkout paths. The landing reports "one write to the main
  checkout" (the untracked test draft). The two production files were later correct in the worktree and in the merge; how the
  main copies were reverted is not recorded in the store, and the main checkout is clean now **(re-read)**.
- **Restarts** **(store)**: three restart notices (2026-10-24T12:48Z, 13:38Z, 16:07Z). The landing mentions none. The lane
  text was loaded at 15:15Z, 12:49Z, 13:39Z and 16:08Z, i.e. re-read within a minute after each restart.
- **Guard attribution** **(re-read, store)**: three refusals in the tree (R1 `ls -la` 15:24Z, R2 `rm` 15:38Z, R2 `rm` 17:55Z). The
  landing lists the two R2 lines and omits the R1.
- **Shell file operations** **(store)**: the root issued `grep` 5, `tail` 5 and `ls` 1; the landing says none beyond the refused
  `rm` and `git clean`, with `tail` disclosed.
- **Operator questions** **(store)**: four `question` calls (15:16Z, 15:38Z, 02:40Z, 09:27Z) = the four in the landing.
- **Self-review**: the root made three `subagent` calls, all `completed`, but the store holds one child session for the tree.
  Rounds 2 and 3 could not be matched to sessions.
- **Sonar**: the landing carries `open_issue_count=0`; the three reads were not matched in the store here.
- **CI**: `verify / verify` failed three times on the `test-compile` freshness backstop (see Open Defect), each cleared by a
  re-run. The landing handled the operator's free text "try again" as a CI re-run only, which is correct.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1851; `landing` `landings/PLAN-LB-43.md`; `plan_marshall_plan_id` `lb-43-consumer-leaf-workflow-resolution`
- [x] epic.md: Queue annotation, model-comparison grade, Open Defect (freshness backstop), Watch (stray main-checkout writes)
- [x] resume anchor and `queue-view.md` regenerated

## Follow-Ups

- The freshness backstop is recorded as an Open Defect, not staged; the stray main-checkout writes are a Watch. Neither is
  staged under the focus rule unless the operator says so.
