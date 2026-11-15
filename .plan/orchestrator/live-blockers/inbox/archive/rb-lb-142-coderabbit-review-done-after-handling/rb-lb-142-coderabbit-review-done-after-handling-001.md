envelope_version=1
sender_type=plan
sender_id=rb-lb-142-coderabbit-review-done-after-handling
epic=live-blockers
kind=landing
created=2026-11-11T05:09:16Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-142-coderabbit-review-done-after-handling
epic=live-blockers
pr=#1959
merge_state=open
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:blocked,merge:blocked
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

# LB-142 — one handled CodeRabbit review is the review

PR #1959 is open with all four deliverables implemented, the build gate green on the head, and the
self-review clear. The merge is blocked by the one thing the plan cannot supply: no CodeRabbit review
exists yet. CodeRabbit refused on quota twice (02:35Z and 04:29Z, "Review rate limited"), and the
lane's quota policy forbids merging without the required review. Window 2 of 10 is open; the next
permitted trigger is 2026-11-11T05:59:30Z. Per the policy's own "stop the session" option the run is
parked here; the progress file carries the resume point.

## Deliverables

**D1 — a flagged bot with a qualifying, handled review is complete at any later head.** Met.
A new registry flag `review_complete_after_handling` (CodeRabbit only, fail-closed `false`) is read by
`review_completeness.classify_bot`, which resolves such a bot `participated` / `participated_but_empty`
when the producer also reports a finished review for it, and by `trigger-bot`, which withholds it from
both trigger lists and names it in `review_complete_bots[]`. Pending findings still block through the
triage arm; an unreadable store never completes; an unflagged bot keeps `participated_stale`; a
refusal is never done. Crucial correction found in self-review: a marker-bearing comment that is not
a finished review (unreadable payload, non-`reviewed` kind, no named commit) is evidence but not a
review, so the producer gained `finished_review_bots[]` and every consumer keys on it — without that,
a walkthrough-shaped marker could have completed the quorum on no review.

- order: `mutation-after`; test `test_review_complete_after_handling.py` (automatic-review), plus
  `test_review_completeness_{state,cli,overlays}.py` and `test_clean_review_credit_regression.py`
  moved to the new reading; failing run `84c4c0bb5`, job log
  `8e78f92112da449eb5a4d28611697e3c` (18 failed); passed at `84c4c0bb5`, job log
  `82953c2559cb443e8e7b1bb2563f0f90` (283 passed). Commits `02f39c819` … `8846fcf84`.

**D2 — no path posts or awaits a CodeRabbit trigger once the review is on record.** Met.
`request_fresh_review` — the one post chokepoint — refuses (`review_on_record_done`) for a flagged bot
with a finished review, for the ordinary and escalated commands, before the rate-window guard. A
failed or capped history permits the post (fail-open for the POST decision only). `resolve_recovery_action`
settles under both the elapsed and the `no_unreviewed_commit` conditions, posting nothing. Trigger B,
trigger A and the lane's re-trigger/merge-of-base prose leave a flagged bot out. A pull request with
no review is triggered exactly as before.

- order: `mutation-after`; test `test_review_complete_after_handling_re_review.py`,
  `test_review_policy_defaults.py`, `test_re_review_strategy_resolve.py`,
  `test_refusal_recovery_arming_verdict.py`; same failing run/log; passed at `84c4c0bb5` with the
  build gate runs below. Commits `eddae8055`, `7698e24d5`, `e3fb9ae29`, `8846fcf84`.

**D3 — the merge gates accept a done review without a review of the head.** Met.
`pre_merge_gate._check_participation` forwards `finished_review_bots[]` into the one
`review_completeness` predicate, so the done reading reaches the merge through the same verdict the
FIND step uses; no `review-barrier-gap` authorization is involved or weakened. `runbook_lane.resolve`
emits the flag beside `quota_limited`. The lane's § 6 step 6 and § 7 state the done satisfaction and
its exemption from the re-trigger and standing-authorization conditions.

- order: `mutation-after`; test `test_review_complete_after_handling_gate.py` (drives
  `_participation_verdict` with the REAL classifier), plus `test_runbook_lane.py` row tests; same
  failing run/log; passed at `84c4c0bb5`. Commits `7974ed842`, `8846fcf84`.

**D4 — the prose and the pins say the same thing.** Met.
Every surface document that stated the old re-review/currency behaviour now states the done rule,
scoped to the no-review case where the policy remains. The doc-contract tests pin each document IN the
section that stated the old behaviour, with a mutation control per pinned document (12 documents) and
a sweep over the real retired sentences; the sweep's controls plant each sentence and expect a hit.

- order: `mutation-after`; test `test_review_complete_after_handling_docs.py`; failing run
  `84c4c0bb5`, job log `8e78f921…` (in-batch); passed at `84c4c0bb5`. Commits `9362110ad`,
  `084cbb2af`, `8846fcf84`, `84c4c0bb5`.

Per-head test runs against every pushed head: `84c4c0bb5` (module-tests job log
`b335dc466d6f45aa9bae4d1ce3aee1b3`), `88b6d2695` (`verify` job log
`089dc4795a8b4d73a35d80849df2f291`, 881 s, and CI `verify / verify` SUCCESS).

## Personas and skills

`persona-implementer` for the production changes, `persona-module-tester` for the unit/module tests,
`persona-documenter` for the prose, and `persona-code-reviewer` for all three self-review rounds and
for triaging the review surfaces. The spec named no domain skills (`skills: none named`); no skill was
added for surface drift — every changed file is on the spec's Expected Surface, with `_github_pr.py`
and `github_pr.py` used under the spec's "only if the producer must report which bot holds a
qualifying review" HYPOTHESIS, which the self-review proved it must.

## Hypotheses

- "`request_fresh_review` is the only trigger post site" — confirmed (one `post_pr_comment` call in
  the module).
- "`resolve_recovery_action` re-triggers an explicit-trigger bot with a review on record" —
  confirmed at `github_re_review.py:1037-1050` before the change.
- "`classify_bot`'s stale arm is the single place stale participation is reported" — confirmed
  (`review_completeness.py`, the `stale_participants` branch).
- "`pre_merge_gate._participation_verdict` allows only complete participation or an admissible
  authorization" — confirmed; the done reading reaches it through the shared predicate, so no new
  verdict was minted.
- "A real CodeRabbit summary names a commit" — confirmed (`final_review_risk_coverage` payload names
  `coveredCommitId`/`sourceCommitId`, read through `_github_pr`); the retired wrapper does not, which
  is why it is not a done-rule review.
- "A stored finding proves the bot reviewed" — REFUTED during self-review: filing has no
  admissibility filter, so the done rule keys on the producer's `finished_review_bots[]` instead.

## Findings

Self-review round 1 (1 blocker, 6 should-fix, 6 nits): doc pins too loose → mutation controls added;
marker must name a commit; capped fetch treated as unknown; done arm missing under
`no_unreviewed_commit`; stale-set prose; trigger-A skip claim; two definitions of a qualifying
review. Fixed in `7698e24d5`, `084cbb2af`.
Self-review round 2 (1 blocker, 4 should-fix, 3 nits): a marker-bearing comment that is not a finished
review completed the quorum (the blocker) → the producer now reports `finished_review_bots[]` and all
consumers key on it; stored-finding exclusion over-reached → keyed on the finished report; retired
sweep strengthened; lane § 6 step 6 pinned; gate depth noted. Fixed in `e3fb9ae29`, `4dfe987f9`,
`8846fcf84`, `84c4c0bb5`.
Self-review round 3: verified the above; no new blocker/should-fix; `self-review: clear`.
PR surfaces: no review threads and no review-body findings exist (no review was obtained);
`review-gate` answered `merge_allowed: true`, `unresolved_review_threads=0`,
`review_body_findings_total=0`, `review_body_findings_handled=0` on `88b6d2695`.

## Reviewers

- **coderabbit** (required, `quota_limited`, `review_complete_after_handling`): refused twice —
  02:35:15Z and 04:29:30Z — both `rate_limited` with `cause: quota` ("Review rate limited"); no
  review exists, so the done rule does not apply and the quota policy governs. Windows spent: 2 of 10.
  Next permitted trigger: 2026-11-11T05:59:30Z.
- **sourcery** (optional): refused 02:08:43Z with `cause: size` ("larger than the review limit of
  150,000 diff characters"). Structural, no wait can move it, optional bot so it gates nothing; not
  re-triggered.
- Standing review authorization: not applicable — it requires a qualifying review, and none exists.

## Operator questions

None asked. The quota policy forbids asking before its steps are spent, and this run stopped at the
policy's own "stop the session" option rather than presenting a rule-bending choice.

## Rule check

- Guard: `present`; log `.plan/temp/guard.log`. This run's sessions produced **2 refusals**, both
  mine: rule `R2` (shell file operations) for two `mv` attempts at 2026-11-10T21:49:42Z while renaming
  new test modules; the rename was completed with `git mv` after `git add`, and nothing was lost. The
  guard log also holds one `R1` line at 2026-11-11T02:48Z from a different session
  (`ses_e3bbd011…`), not attributable to this run's session tree.
- Shell: one command per call throughout; no `&&`, `;`, pipes, command substitution, loops or
  heredocs; file reads and searches with the file tools; no `cat`/`ls`/`grep`/`find`/`sed`; no
  redirects.
- Executor only: every script through `python3 .plan/execute-script.py …`; every build through the
  resolved build commands with default routing; every CI action through `plan-marshall:tools-integration-ci:ci`.
- `.plan/` state: only `.plan/temp/` and the three prescribed `ci` body slots written; the spec and
  every file under `.plan/orchestrator/` untouched.
- Spec read: `spec_source=ledger_worktree`, no `spec_differ` marker.
- Executor-skew verdict: `not_applicable` (source checkout; executor 0.1.2076), recorded and not
  asked about.
- Sub-agent restarts: none; three self-review dispatches, each re-read the same diff and reported.
- Model switches: none (one model/variant throughout).

## Build server

Setup preflight: `ready` (registered, version 1). Every build was submitted to the daemon:
mechanism `daemon_longpoll` on all 38 build invocations (36 before the PR plus the local `verify` and
the mutation runs), zero `in_process_fallback`, zero degradations, zero launch-fault retries. Two
`killed`-class dispositions: none. Queueing was observed on several submissions (`queued_seconds` up
to ~700 s) and is recorded as waiting, not as a fallback. No `runtime_stamp_reason` was reported.

## Residue

- The merge awaits CodeRabbit's quota window. Resume from `.plan/temp/rb-lb-142-coderabbit-review-done-after-handling/progress.md`:
  at/after 2026-11-11T05:59:30Z re-trigger `@coderabbitai review`, then run § 6 step 5 and § 7 again.
- Once a review exists, the done rule applies to it: after every finding is handled the PR merges with
  no review of the final head, which is this plan's purpose.
- Sourcery cannot review this diff at its 150,000-character ceiling; it is optional and gates nothing.
- The lane's § 8 note about a merge that never happened: no cleanup was owed or performed.
