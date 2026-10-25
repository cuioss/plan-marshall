# Landing Analysis: PLAN-LB-55 — Gate truth: no push, merge or phase advance on a head or boundary the gates have not seen

epic: live-blockers
workstream: WS-01
pr: #1856 (`215f5095e`, merge queue, base `main`)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction or `guard.log`.
> **(store)** = read from the OpenCode session database, read-only (counts, tool names, command words, paths, times; no
> message text). Nothing was executed. Token usage is out of scope by the 2026-10-23 ruling. The correctness of the new push
> gate, the barrier binding, the phase-boundary guard and the refusal ranking was not re-executed: it rests on the PR's
> tests and green CI. This is the final landing; the interim report of the same run was archived earlier.

## Verdict

**Grade: C+.** Runbook lane, `deepseek-v4.1-flash/high` on all three sessions **(store)** (root plus two self-review
sub-agents, both `completed`), 14 h 17 min wall clock (2026-10-24T08:18Z to 22:35Z).

Half of the spec is delivered and evidenced, and the run says so: D2 and D3 are met in full with mutation or test-first
records, D1's three Done-when clauses are met, and D4's grant verb, doc test and no-demotion option set are met. The
rest is not: an armed auto-merge bound to its head, the participation check inside `pre_merge_gate merge`, and the remaining
D4 clauses (the landing counts five; its own table row and the PR body list six). The landing reports `deliverables_done=2` of 4 and "not met" for the rest, which matches the PR body and the diff.
What holds the grade down is the part the spec was written for and what the report gets wrong about the run: the barrier
half is the half left undone; the report states four restarts where the store shows two; two edits to a tracked file in the
MAIN checkout are undisclosed; a guard refusal in a sub-agent is missing; and the shell read-class counts are understated.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 Push, force-push and merge refuse a head the gates did not see | partial: the three Done-when clauses met, two bullets not | `_push_gate.py` (new), `git-workflow.py` `push` verb, `_cmd_force_push.py`, `pre_merge_gate.py` (+144), three tests `mutation-after` **(re-read: diff)**. Not implemented: an armed auto-merge bound to its head; the required-bot participation check inside `pre_merge_gate merge` |
| D2 Phase boundaries hold without bypasses | shipped-as-specified, `mutation-after` | `_cmd_lifecycle.py` (+252), `_status_query.py`, `test_lb55_phase_boundary_and_marker_gaps.py` (382) covering all five clauses |
| D3 A refusal on the merge candidate outranks an older review | shipped-as-specified, `test-first` | `review_completeness.py`, `github_pr.py` (+99), two failing-at-base logs cited |
| D4 Roster error, barrier posture, grants | partial: 3 of 7 Done-when clauses met | grant verb refuses a non-label answer, doc test finds the review policy, demotion option removed. Not implemented: `step-params get` roster error, stale-bot trigger-before-ask, generated option set, `merge_lock` recovery loop, merged-under-authorization record, mutex re-acquire |

Claimed `deliverables_done=2` of 4; the table agrees on the count and on every "not met". The landing's Residue lists all of
the above.

**Surface.** The spec declared 15 entries (mostly directories); the PR diff has 34 files (+2196/-192) **(re-read)**. Two
declared entries were not touched: `test/plan-marshall/manage-status/test_transition_boundary_guards.py` (new
`test_lb55_*` modules were written instead) and `manage-locks/scripts/merge_lock.py` (consistent with the unmet D4 recovery
loop). The path-level delta beyond the declaration was not measured.

## Findings by the orchestrator

- **Reach.** Everything D1 and D4 add to the barrier lives in the plan-marshall lifecycle's `phase-6-finalize` scripts. The
  runbook lane's skill names neither `pre_merge_gate` nor the barrier **(re-read: the lane directory has no reference)**, so
  the lane's merge rests on its own § 7 text, which these deliverables do not touch. The unimplemented D1 bullet 4 and the
  D4 clauses are therefore the half of the mechanism that a runbook run would not have used even if shipped.
- **Restarts** **(store)**: two restart notices (12:48Z, 13:38Z); the lane text was re-read within a minute after each (four
  reads after the first, one 100-line read after the second). **The landing states four restarts.** The store shows no notice
  after 13:38Z in this tree.
- **Main-checkout writes** **(store)**: at 08:34Z to 08:35Z the root edited the tracked test
  `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` twice and created the untracked
  `test_lb55_refusal_outranks_stale_participation.py`, all by main-checkout paths. The landing discloses only the untracked
  draft ("one write"). The main checkout is clean now **(re-read)**; the operator cleared it earlier.
- **Guard attribution** **(re-read, store)**: two refusals in the tree: R2 `rm` of the draft at 08:35:19Z (the landing's) and an
  R1 `git grep … | head` at 10:18:44Z in the second self-review sub-agent. The landing says the refusals it saw are the
  one. It also says restoring `uv.lock` "was guard-refused"; no such line is attributed to the tree in `guard.log`.
- **Shell file operations** **(store)**: the root issued `ls` 2, `grep` 3, `find` 1, `tail` 11 and one `rm`. The landing says
  `ls`, `find` and `grep` were each used once and does not mention `tail`.
- **Operator questions** **(store)**: three `question` calls (08:18Z, 16:37Z, 20:27Z) = the three in the landing.
- **Self-review**: two `subagent` calls, both `completed`, and two child sessions in the store (09:55Z, 10:16Z) = the two
  rounds. The landing records `self-review: budget-exhausted`.
- **Sonar** **(store)**: four `read_open_issues`/`sonar-gate` pairs (12:37Z, 19:28Z, 20:23Z, 22:01Z) and `sonar-facts` at
  22:34Z, taken by the run; the landing carries `open_issue_count=0`. The counts themselves were not read.
- **Reviews** **(re-read)**: CodeRabbit reviewed `0212ce856`, `b4cf24459`, `63cdd2e86`, `3ead15d99`, `b17446e45` and, **two
  minutes after the merge**, the merged head `90dc80a16` (22:11:29Z; merge 22:09:27Z). The landing counts five reviews. The
  late review carries two Minor outside-diff comments and two nitpicks; none is major, none was handled (post-merge,
  accepted under the focus rule). Refused on quota ("Review rate limited"): the triggers at 11:38Z and 19:45Z. Sourcery refused on size (optional). All 22
  review threads are resolved **(re-read)**.
- **Last head unreviewed at merge, third instance.** `5e3d1c299` (the grant-provenance fix in `_cmd_merge_authorization.py`)
  changed logic after the qualifying review of `b17446e45`, and the base merge `90dc80a16` followed; the PR merged on the
  standing authorization without a question. Datapoint for the open ruling: the review that arrived after the merge, over
  `b17446e45..90dc80a16`, raised nothing major.
- **Executor-skew question** (before `resolve`): answered "Proceed as not-skewed"; the executor recorded as `0.1.2004`.
- **Routed builds**: the landing reports one daemon-routed build failing at setup (`pwx` unresolvable from the worktree) and
  every later build `in_process_fallback`, so the per-worktree executor of PLAN-LB-92 did not carry the routed build here
  (the same note appears in the PLAN-LB-53 landing). Recorded as a Watch, not staged.
- **Local whole-suite timeouts**: `test_harness_shape_guards.py` whole-tree scanners exceeded their 300 s cap under load in
  this run and in PLAN-LB-53's; both pass standalone and in CI.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1856; `landing` `landings/PLAN-LB-55.md`; `plan_marshall_plan_id` `lb-55-gate-head-truth`
- [x] epic.md: Queue annotation (the interim entry replaced), model-comparison grade, Open Defect (the unmet gate-truth half), Watch (unreviewed last head, third and fourth instance)
- [x] inbox message `rb-lb-55-gate-head-truth-002` archived; resume anchor and `queue-view.md` regenerated

## Follow-Ups

- The unmet D1/D4 half is recorded as an Open Defect scoped to the lifecycle lane (see Findings, Reach), not staged: staging
  it is the operator's call.
- PLAN-LB-58 was held until this landing and is now free of that hold.
