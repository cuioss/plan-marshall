# Landing Analysis: PLAN-LB-172 — Consolidated left-over fixes of the PLAN-LB-162 to PLAN-LB-171 landings (PARTIAL, PR OPEN)

epic: live-blockers
workstream: WS-04
pr: #2036 (https://github.com/cuioss/plan-marshall/pull/2036) — OPEN, not merged

> Landing record for one plan that ran and stopped BEFORE its merge. Lives at `landings/PLAN-LB-172.md`.
> Written by the `analyze` verb after verifying the landing message against ground truth: git, the CI
> abstraction and the review gate. The message is a lead, never a fact; every figure below is labelled
> OBSERVED (re-read by the orchestrator) or CARRIED (the lane's own statement, not re-read).
>
> This is not a full ship. The PR is open, so there is no merge commit and the row is NOT marked shipped.
> The row stays `running`; it is reconciled to `shipped` by the landing of PLAN-LB-173, which takes over
> the PR's review handling, and this report is then completed.

## Deliverable Fidelity vs Spec

The spec is `plans/PLAN-LB-172-consolidated-leftover-fixes.md` (ten deliverables). The lane reports five done
and five not started. OBSERVED against git: the PR branch `feature/lb-172-consolidated-leftover-fixes` is six
commits ahead of `main` (`a39aa80d6`, `54fe92366`, `93d55c4b3`, `28e051041`, `6ebc69cf4`, `a8bd2ffac`) and changes
21 files, every one inside the spec's Expected Surface; none of the five unshipped deliverables' files
(`apply-changes` entry points, `_cmd_orchestrator.py`, the criteria files, the manifest files, the build-server
files) is among them, which agrees with the lane's "not started".

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 review-body parser never under-counts | shipped-as-specified, PR open | CARRIED: 12 red at `c22d103fb`, green at `a39aa80d6`. OBSERVED: `runbook_lane.py` and `test_runbook_lane_review_gate.py` are in the PR's file list. |
| 2 Sonar carry-forward binding and decision-verb edges | shipped-as-specified, PR open | CARRIED: 13 red, green at `54fe92366`. OBSERVED: `sonar.py`, `test_runbook_lane_sonar.py`, `test_runbook_lane_sonar_landing.py`, `test_read_open_issues.py` in the file list. |
| 3 runbook-lane document, docstrings, tests | shipped-modified (the classifier is code, not text) | CARRIED: the lane read `.github/workflows/python-verify.yml` and changed the code. OBSERVED: `runbook_lane.py`, `SKILL.md`, `test_runbook_lane.py` in the file list. Direction (code, not text) is the spec's own HYPOTHESIS, answered by the lane; not re-read. |
| 4 PR body slot | shipped-as-specified, PR open | CARRIED: green at `28e051041`. OBSERVED: `ci_base.py`, `test_ci_base_cli.py`, `api-contract.md`, `issue-operations.md`, `pr-operations.md`, `workflow-integration-gitlab/SKILL.md` in the file list; `tools-integration-ci/SKILL.md`, named by the PR body as the rule's single home, is not in it (it either already holds the rule or the body is wrong — unverified lead, see Follow-Ups). |
| 5 analyze and handle-open contracts | shipped-as-specified, PR open | CARRIED: green at `6ebc69cf4`. OBSERVED: `analyze.md`, `handle-open.md`, `landing-payload-spec.md`, `landing-analysis.md`, `triage.md` and both contract tests in the file list. |
| 6 to 10 | not shipped | The lane's statement and the file list agree. Carried to PLAN-LB-173 as its deliverables 2 to 6. |

## Three-Layer Analysis

Not run, by decision. The analysis reads the MERGED code at a merge commit; this PR is unmerged, six review
threads and 23 review-body findings are about to change the very lines a leaf would read, and the lane's own
self-review round never ran. A reading now would be spent on code that is going to move. It is deferred to the
landing of PLAN-LB-173, which merges this PR and whose landing message is the one the three-layer leaf reads.

- **Dispatch:** none — reason: no merge commit exists and the code under review is in flux.
- **Verdict:** layer 1 not shown by reading; layer 2 not shown by reading; layer 3 not shown by reading.

### Layer 1 — Specified

Not read. The spec's premises were staged from the ledger's own Open Defects; the lane's `Hypotheses` section
reports D3(e) REFUTED ("the §7 reach rule is empty for its own example": §7 already covers it) and D2(e) answered
with no code change. These are the lane's own answers; they are not re-read here.

**Layer 1 verdict:** not shown by reading

### Layer 2 — Implemented

Only the file-set trace above was re-read. Whether each deliverable has a test that can fail is the lane's claim
(red runs recorded per deliverable); not re-read.

**Layer 2 verdict:** not shown by reading

### Layer 3 — Correct

Not read. Six unresolved CodeRabbit threads sit in `runbook_lane.py` at lines 207, 1318, 1320, 3665, 3677 and
3700 at head `a8bd2ffac`; their text is third-party content the orchestrator did not ingest, and the follow-up
lane reads and dispositions each.

**Layer 3 not shown by reading:** every defect class; nothing here says the merged code is clean.

**Layer 3 verdict:** not shown by reading

### Conformance to the Project's Own Rules

Not checked (no merged code). One lane-reported item: a single shell file operation (`ls` of the progress
directory) was issued early in the run and recorded by the lane itself (CARRIED).

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none (`total_tokens=unknown`). Recorded as an unobserved fact, never as zero. `landing-check` reports it `missing`, so the landing is `complete: false`.
- Duration: not supplied (`unmeasured` surface delta).
- Anomalies: the run stopped at its working limit with half the spec shipped and the PR open; `self-review: budget-exhausted` (the sub-agent review round was skipped, no verdict claimed); one `verify` run re-attached twice through the daemon's bounded wait before reporting success (CARRIED); harness `opencode`, model `deepseek-v4.1-flash/high`.

## Routing and Merge Behavior

- Review: coderabbit (required) reviewed head `a8bd2ffac`. OBSERVED by `runbook_lane review-gate --pr-number 2036`: `unresolved_review_threads: 6`, `review_body_findings_total: 23`, `review_body_findings_handled: 0`, `merge_allowed: false`, reason `unresolved_review_threads`. The landing's three numbers (6, 23, 0) match the re-read; no false claim. `review_body_findings_handled` is **not re-verified** against the progress file (a 0 is consistent with six threads still open; it is not a difference). Sourcery (optional) is SKIPPED by the provider.
- CI/merge: OBSERVED through the CI abstraction: PR open, `mergeable`, `merge_state: clean`, `review_decision: none`; all required checks pass (`verify / conclusion`, `verify / verify`, `verify / gate`, `generate-check`, `dependency-review`, `CodeRabbit`); `auto-merge` and `Sourcery review` skipped. The merge gate refuses on the threads, correctly.
- Sonar: `sonar_open_new_issues` is `n/a` in the landing; the ledger carries no Sonar figure for this epic (not enabled), so there is nothing to compare.
- Collisions: none observed; the lane's branch is disjoint from every other in-flight branch.

## Reconciliation Actions

- [ ] row `status` → `shipped` — NOT done, by design: the PR is unmerged. Row stays `running`; reconciled by the landing of PLAN-LB-173.
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-172 --field pr --value 2036`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-172 --field landing --value landings/PLAN-LB-172.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-172 --field plan_marshall_plan_id --value rb-lb-172-consolidated-leftover-fixes`
- [x] epic.md narrative reconciled (a Decisions entry; a Watch for the stranded PR #2036; no Open Defect, because `complete: false` on `total_tokens` alone is no defect; the STAGED markers of the five source entries still name PLAN-LB-172 and are read as PLAN-LB-173 deliverables 2 to 6, per the Decisions entry)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated
- [x] message archived (`inbox archive`), decision logged

## Follow-Ups

- PLAN-LB-173 (staged, one plan on the operator's word): deliverable 1 carries PR #2036 to merge (self-review round, disposition of the six threads and 23 findings, merge through the gate); deliverables 2 to 6 are the five unshipped deliverables.
- Unverified lead: the PR body names `tools-integration-ci/SKILL.md` as the single home of the shared-slot rule, yet that file is not in the PR's changed-file list. PLAN-LB-173's lane reads it while handling the PR; if the rule is not there, the body is wrong or the document is missing the rule.
- Owed to the operator after the merge: `/apply-changes` (the plan edits bundle sources).
- The three-layer analysis of the D1-D5 code is owed at the PLAN-LB-173 landing.
