# Landing Analysis: PLAN-LB-85 — The runbook lane reads a pull request's open Sonar issues and gates the merge on them

epic: live-blockers
workstream: WS-04
pr: #1839 (`e40f50aa1`, parent `58a2b31eb`, merge queue, base `main`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims
> against ground truth. A claim marked **(re-read)** was read again by the orchestrator in git,
> the CI abstraction or the run's evidence files. A claim marked **(unverified)** rests on the
> landing alone: the harness session store could not be read in this analysis (the read was
> refused by the permission classifier), so every session-tree fact is a lead, not a finding.
> Nothing below was executed except read-side git, `ci` and orchestrator verbs.

## Verdict

**Grade: B− (provisional).** Runbook lane, `deepseek-v4.1-flash/high` (as reported, **unverified**).

The work is real and the report holds up wherever the orchestrator could read the evidence
(the session store excepted). The three
new surfaces exist as described: the plan-less `read_open_issues` verb, the lane's `resolve`
Sonar state plus `sonar-gate`, and the `step.sonar-roundtrip.*` landing facts. Every red log
the landing cites exists and shows the failure it names **(re-read)**. All five review threads
are resolved **(re-read)**, CI is green on the merge head **(re-read)**, and the guard-log
attribution is correct for the first time in this series. Two things hold the grade down: the
Sonar figure this plan exists to measure was never taken on its own PR (`unknown`), and
D3 clause 3 ships as "not met as written" (a preservation claim that cannot fail).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 Plan-less `read_open_issues` verb | shipped-as-specified | `sonar.py` +170 lines, `test_read_open_issues.py` (304 lines) **(re-read: diff)**. Red log `…/test_read_open_issues.py/python-2026-10-22-152054.log` carries 16 matches of `has no attribute 'cmd_read_open_issues'` **(re-read)**. Red-before-green holds by log time (15:20:54 vs the commit at 15:27:56Z). |
| D2 Lane resolves Sonar state, reads, gates the merge | shipped-as-specified, evidence `mutation-after` | `runbook_lane.py` +451, `runbook-lane/SKILL.md` +114, `test_runbook_lane_sonar.py` (341). Mutation log `python-2026-10-22-153436.log` exists and names the gate **(re-read)**; it was run 14 s after the commit, so it is a mutation of the committed fix, not a test-first red. Labelled correctly by the run. |
| D3 Landing carries the measured figure | shipped-modified | Clauses 1 and 2 shipped with `test_runbook_lane_sonar_landing.py` (218). Clause 3 ("`landing-check` reports an unchanged required-key set") is a preservation claim: `_orchestrator_inbox.py` is absent from the 14-file diff **(re-read)**, so it cannot be seen failing. The run reported it honestly as not met and `deliverables_done=3`. The spec clause is the defect, not the run. |
| D4 Spec template asks for the Sonar read and the consumer-visible set | shipped-as-specified, evidence `mutation-after` | `plan-spec.md` +27, `landing-analysis.md` +5, `landing-payload-spec.md` +39, `test_plan_spec_template_contract.py` (81) **(re-read)**. |

Claimed `deliverables_done=3` of 4; the table above agrees.

**Surface.** The spec declared 13 entries; the diff has 14 files (+1756/−38). `landing-check
--declared-paths/--realized-paths` reports `expansion_detected`: **added** `extension-api/
standards/ext-point-triage.md` and `ref-workflow-architecture/standards/findings-pipeline.md`
(both disclosed: the provider contract was stated as two verbs and is now three; one-line
edits); **missing** `plan-orchestrator/workflow/analyze.md`, `workflow-integration-sonar/
scripts/sonar_provider.py` and `test_landing_completeness.py`. The shipped spec is not edited.

## Metrics and Anomalies

- Tokens: `unknown`. The lane writes `unknown` because it measures none; the session store
  could not be queried here, so the figure is **unobserved by this analysis too**.
- Duration: not in the facts. Authored commits span 17:27 to 00:50 local, merge queue after.
- `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only. `effort` and
  `plugin_version` are now supplied, so PLAN-LB-78 D3's fix reached this run through the
  post-sync lane text. The remaining miss is the known collision (the lane's § 8 prescribes
  `total_tokens=unknown`, the check rejects `unknown` at every required key); PLAN-LB-86 D2
  owns it. A recurrence, not a new defect.
- `plugin_version=0.1` is wrong against `executor_version=0.1.1986`. `platform_runtime
  runtime-info`, run by the orchestrator under Claude here, also returns `bundle_version:
  "0.1"` beside `executor_version: 0.1.1986` **(re-read)**, so the lane copied what its stamp
  source reported. Lead: the stamp source truncates the bundle version. Not confirmed under
  OpenCode.
- The `model` fact is a single scalar `deepseek-v4.1-flash/high`; whether it held for every
  session is **unverified**.
- Anomalies: `verify` at `bd6568a26` hit its 1776 s bound locally and ran in the split form
  (disclosed). CI's `verify / verify` was 1641 s on the merge-head run, the landing says 1612 s
  (immaterial).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `bd6568a26` (19:32Z, 4 findings),
  `07b101f4a` (20:41Z, 1 outside-diff) and `5a58a69e0` (22:12Z, 1 nitpick) **(re-read)**.
  Triggers 19:25, 20:36, 22:07 accepted; 21:26 and 22:51 refused "Review limit reached"
  **(re-read)**. All 5 review threads resolved; the 18 "unresolved" rows `pr comments`
  returns are review bodies and issue comments, not threads **(re-read)**. Sourcery refused
  (quota), optional.
- The final head `f605ab49c` is CodeRabbit-unreviewed. Its change is one test file (a range
  assertion made exact), the nitpick CodeRabbit itself raised and rated Low merge risk. This is
  the standing authorization applied to a test-only fix, **not** the LB-77 pattern (new logic
  after the qualifying review); it does not bear on the open semantic-fix ruling.
- CI/merge: `verify / verify` green on `f605ab49c` (run 39867816990), generate-check green,
  merged through the merge queue without a question **(re-read)**.
- Collisions: none at launch (it ran beside LB-86 and LB-88 on disjoint surfaces). After
  landing, its realized footprint moves the lane text and `sonar.py` that PLAN-LB-73, 89, 69
  and 58 declare; see the annotation in `epic.md`.

## Report Contradictions

None found against the evidence the orchestrator could read:

1. Guard log: the four refusal lines the landing claims (`16:08:08` R1, `16:35:56` R5,
   `17:05:49` R1, `17:32:22` R1) are in `guard.log`, each on a command that names the
   `lb-85-lane-sonar-issues` worktree, and the four other lines in the window
   (`15:15:06`, `17:10:37`, `17:49:48`, `19:39:35`) name the LB-86 and LB-88 worktrees
   **(re-read)**. The "two mine, two from sub-agents" split follows the session ids.
2. Every sha the landing cites resolves, and the merge sha matches the PR **(re-read)**. Commit
   trailers were not checked.
3. **Unverified:** the main-checkout edit that was reverted, the `ls`/`tail`/`wc` counts, the
   lane text loaded and whether it was re-read after any restart, restarts and killed
   sub-agents, and the tree's session count. All need the session store.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-85 --status shipped`
- [x] row `pr` stamped — `--set-row PLAN-LB-85 --field pr --value 1839`
- [x] row `landing` stamped — `--set-row PLAN-LB-85 --field landing --value landings/PLAN-LB-85.md`
- [x] row `plan_marshall_plan_id` stamped — `--value lb-85-lane-sonar-issues` (the sender `rb-lb-85-lane-sonar-issues` without its `rb-` prefix)
- [x] epic.md: PLAN-LB-85 annotation rewritten; Open Defects added (Sonar figure `unknown`, bootstrap gap, `plugin_version` stamp); model-comparison Watch extended
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- **Sonar read of the merged tree** (owed, operator): regenerate the executor, then run the
  read against `main`. Until then no landing carries a measured figure.
- **Executor bootstrap gap** → PLAN-LB-89 (it already declares `generate_executor.py`): a plan
  whose lane text calls a verb it adds cannot run it, and the guard refuses the only route.
- **`plugin_version` stamp** → verify under OpenCode, then PLAN-LB-84 (it declares
  `runtime_info.py`).
- **Verbs the lane text now requires** (`sonar-gate`, `sonar-facts`, the § 6 read step) bind
  every runbook run started after the next harness sync; LB-86 and LB-88 started before it.
- **Fix-forward from this landing:** none staged. D3 clause 3 is a spec error, not a code defect.
