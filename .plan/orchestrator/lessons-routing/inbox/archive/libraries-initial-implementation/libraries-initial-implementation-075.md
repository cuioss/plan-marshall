envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=finding
created=2026-11-24T12:08:01Z
revision=1
amended=2026-11-24T12:08:17Z

# Tooling findings of the libraries-initial-implementation epic (git-document-repository), 2026-11-24

Source: the orchestrator of epic `libraries-initial-implementation`, after landing analyses of PLAN-01 to PLAN-23 (23 plans, plugin 0.1.2184). These are
observations about plan-marshall tooling that the epic's ledger records but that are not lessons of the corpus. Each one is a lead for the receiving
epic to verify; the evidence is in that epic's `epic.md` (Open Defects, "Incomplete landings", Watches) and in `landings/PLAN-NN.md`.

1. **`runbook_lane review-gate` cannot read CodeRabbit's review-body section header.** For a merged PR the re-read returned `undecidable_read`
   ("unreadable review-body section: '<picture><img ... amber-16.svg ...> Minor comments: N'") on PLAN-02, PLAN-03, PLAN-05, PLAN-08, PLAN-10, PLAN-12 and
   PLAN-11 (N = 18, 7, 1, 10, 20, ..., 1). Where it was decidable (PLAN-04, PLAN-06, PLAN-19, PLAN-20, PLAN-21, PLAN-23) it returned `handled: 0` because the
   dispositions live in the run's progress file, which is gone after the plan directory is removed, so the `review_body_findings_handled` number can
   never be re-verified at analyze time.
2. **`sonar read_open_issues` is `undecidable` for every merged PR** (`count_status_reason: head_revision_unavailable`, `head_revision: ""`, the
   analysis revision present) on PLAN-08, PLAN-11, PLAN-12, PLAN-20, PLAN-21, PLAN-23 (read in this epic; earlier landings recorded the same reason), so the lane's `sonar_open_new_issues=0` is never re-verified
   by the orchestrator after the merge.
3. **The landing-facts producer leaves required keys `unknown` in every landing of the epic** (`effort`, `unresolved_review_threads`,
   `review_body_findings_total`, `review_body_findings_handled`; `effort` because `refresh-runtime-stamp` reports `model_unknown`): `inbox landing-check` reports
   `complete: false` for 16 of the 17 landed plans (PLAN-09 was the one complete landing). "No finalize step records them" is the lane's own statement.
4. **Landing token and wall figures disagree with the retrospective by a factor of 2.5 to 3.2** (PLAN-10: 19.9M tokens and 662 min against 8.04M and 331 min;
   PLAN-11: 23.3M and 576 min against 7.4M and 183 min). A difference of definition is likely (every dispatched leaf against the phase totals) but nothing says which.
5. **`manage-logging decision --store orchestrator` printed a `status: success` TOON on the first call of one session and printed nothing (exit 0) on
   later calls**, directly and through a subprocess; the entries were written. A caller that checks for `status:` reads the empty output as a failure
   (a drain loop did, and logged, archived nothing, and had to be re-run without the log call). Cause not established.
6. **The committed architecture inventory is stale and the module skill profiles are empty**: `.plan/project-architecture/` still names the removed module
   `git-worktrees`; `git-store`, `git-forms` and `documentation` have an undeclared-empty `skills_by_profile` (implementation, module_testing), which raised the same
   Q-Gate findings in PLAN-08, PLAN-09, PLAN-11 (4ad387, e95926), PLAN-23 (a061c4, 5af2f5) and was accepted as informational every time; the persona resolver
   reported `module_status=unreadable` for the module `documentation`. One architecture refresh settles all of them.
