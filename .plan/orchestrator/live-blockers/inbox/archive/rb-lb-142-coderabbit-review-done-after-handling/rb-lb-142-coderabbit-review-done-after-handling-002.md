envelope_version=1
sender_type=plan
sender_id=rb-lb-142-coderabbit-review-done-after-handling
epic=live-blockers
kind=landing
created=2026-11-11T12:25:31Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-142-coderabbit-review-done-after-handling
epic=live-blockers
pr=#1959
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=17
review_body_findings_handled=17
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (two R2 refusals and one stray R5 refusal in this run's tree; see Rule check)

# LB-142 — one handled CodeRabbit review is the review

Merged as `280e6c4040f1b6120984834a99b76afc137dc697` (PR #1959, merge-group run 43015720042, success).
This plan was its own first test: the merge took place with CodeRabbit's review on an earlier head
and every one of its findings handled — no review of the merge head was requested, and none was
demanded by the gate.

## Deliverables

**D1 — a flagged bot with a qualifying, handled review is complete at any later head.** Met.
The per-bot registry flag `review_complete_after_handling` (CodeRabbit only, fail-closed `false`) is
read by `review_completeness.classify_bot`, which resolves such a bot `participated` /
`participated_but_empty` when the producer ALSO reports it in the new `finished_review_bots[]` — a
formal review record naming a commit, or a summary marker that is readable, `kind: reviewed` and
names a covered commit. The done check runs BEFORE the refusal/decline branches, so a finished
review's bot that refuses a redundant later request is still done; pending findings still block via
the triage arm. `trigger-bot` withholds such a bot from both trigger lists and names it in
`review_complete_bots[]`.

- order: `mutation-after`; failing run `84c4c0bb5`, job log `8e78f92112da449eb5a4d28611697e3c`
  (18 failed); passed at `84c4c0bb5`, job log `82953c2559cb443e8e7b1bb2563f0f90` (283 passed). The
  final code additionally passes the reviewers' own regressions (see Findings). Commit `02f39c819`
  plus `7698e24d5`, `e3fb9ae29`, `8846fcf84`, `84c4c0bb5`, `201f0cbd7`.

**D2 — no path posts or awaits a CodeRabbit trigger once the review is on record.** Met.
`request_fresh_review` refuses (`review_on_record_done`) at the one post chokepoint, for the ordinary
and escalated commands, before the rate-window guard; a failed or capped history permits the post
(fail-open for the POST decision only). `resolve_recovery_action` settles under the elapsed,
`no_unreviewed_commit` AND `undecidable` states — before any cause, window or budget arm, so even a
later structural size refusal does not escalate at a done bot — and only with the positive
`--finished-review` observation. Trigger B and trigger A leave a flagged reviewer out only when its
qualifying review is on record; the lane's re-trigger/merge-of-base prose says the same.

- order: `mutation-after`; same failing run/log; passed at `84c4c0bb5` and re-verified on the final
  head by `verify` (job log `f3d678fd817b4b34aa4b89b2990fa20d`, 914 s). Commits `eddae8055`,
  `7698e24d5`, `e3fb9ae29`, `8846fcf84`, `201f0cbd7`.

**D3 — the merge gates accept a done review without a review of the head.** Met.
`pre_merge_gate._check_participation` forwards `finished_review_bots[]` to the one predicate.
`runbook_lane.resolve` emits the flag beside `quota_limited`, and `review-gate` gained
`--required-reviewer` — a per-reviewer check that a qualifying review actually exists (a formal
review with a commit id, or a commitment-naming marker; refusal-as-review and undeclared shapes
excluded) so the done exemption is never taken on the flag alone. The lane's § 6 step 6 and § 7
state both the satisfaction and its evidence requirement.

- order: `mutation-after`; same failing run/log; passed at `84c4c0bb5`; six new tests pin the
  missing-review refusal and the positive/negative artifacts. Commits `7974ed842`, `e42bf3f1d`,
  `f1670af19`, `201f0cbd7`.

**D4 — the prose and the pins say the same thing.** Met.
Every surface document scoped to the done rule; doc-contract tests pin each document IN the section
that stated the old behaviour, with a mutation control per pinned document (12) and a sweep over the
real retired sentences.

- order: `mutation-after`; same failing run/log; passed at `84c4c0bb5`. Commits `9362110ad`,
  `084cbb2af`, `8846fcf84`, `84c4c0bb5`.

Per-head tests: every pushed head ran the gate (`84c4c0bb5` module-tests log
`b335dc466d6f45aa9bae4d1ce3aee1b3`; `88b6d2695` verify log `089dc4795a8b4d73a35d80849df2f291`;
`5bf58bf81` verify log `d8d8161828864b3da7815416fa72b8dc`; `efb9a9fd3` verify log
`b92f49bbfd434442b4f80bbd7e60fe23`; `e42bf3f1d` full log `b186d6bf709f40cdbba08e197a933863`;
`910e76c76` verify log `7d03164f66164874976e6e2678d8781c`; `f1670af19` verify log
`6b9dfb3ad55d4b7991e8f0df72deb2e5`; `fd747d307` verify log `6d1ceff10bb846f9b6620a4933dd34d8`;
`201f0cbd7` verify log `f3d678fd817b4b34aa4b89b2990fa20d`), and CI was green on each before its
next push.

## Personas and skills

`persona-implementer` (production), `persona-module-tester` (tests), `persona-documenter` (prose),
`persona-code-reviewer` (three self-review rounds and every PR finding). The spec named no domain
skills (`skills: none named`); no skill was added for surface drift, with `github_pr.py` /
`_github_pr.py` used under the spec's "only if the producer must report which bot holds a qualifying
review" HYPOTHESIS, which the self-review proved it must.

## Hypotheses

- "`request_fresh_review` is the only trigger post site" — confirmed (one `post_pr_comment` call).
- "`resolve_recovery_action` re-triggers an explicit-trigger bot with a review on record" —
  confirmed before the change.
- "`classify_bot`'s stale arm is the single place stale participation is reported" — confirmed.
- "`pre_merge_gate` allows only complete participation or an admissible authorization" — confirmed;
  the done reading reaches it through the shared predicate, so no new verdict was minted.
- "A real CodeRabbit summary names a commit" — confirmed; the retired wrapper does not, and is
  therefore not a done-rule review.
- "A stored finding proves the bot reviewed" — REFUTED in self-review: filing has no admissibility
  filter, so the done rule keys on the producer's `finished_review_bots[]`.

## Findings

Self-review round 1 (1 blocker, 6 should-fix, 6 nits): loose doc pins (mutation controls added);
marker must name a commit; capped fetch = unknown; done arm missing under `no_unreviewed_commit`;
stale-set prose; trigger-A skip claim; two definitions of a qualifying review.
Self-review round 2 (1 blocker, 4 should-fix, 3 nits): a non-finished marker could complete the
quorum → `finished_review_bots[]` added and every consumer keyed on it; stored-finding over-reach;
weak sweep; lane step-6 pin; gate depth.
Self-review round 3: no new blocker; `self-review: clear`.

PR review findings (four CodeRabbit reviews; all 17 review-body findings disposed, all threads
replied and resolved):
1. trigger-A prose had no mechanism / no refused bullet → fixed `efb9a9fd3`.
2. a refusal-as-review was counted as a finished review → fixed `efb9a9fd3` (+ two regression tests).
3. canonical `trigger-bot` synopsis omitted the new flag → fixed `efb9a9fd3`.
4. elapsed consult lacked `--pending-findings` → fixed `f1670af19`.
5. lane gate accepted a review body with no commit → fixed `f1670af19`.
6. lane gate rejected a marker beside a refusal, unlike the chokepoint → fixed `f1670af19`.
7. flattened bodies hid markers → fixed `f1670af19` (restore comment boundaries before the parser).
8. done lost to a redundant refusal in `classify_bot` → fixed `f1670af19`.
9. producer emitted finished for a commit-less review body → fixed `201f0cbd7`.
10. `undecidable` + finished sent a reviewed PR to close-and-reopen → fixed `201f0cbd7`.
11. lane gate ignored the bot's declared evidence shapes → fixed `201f0cbd7`.
12. lane test helper dropped dispositions → fixed `201f0cbd7`.
13. marker commit membership (foreign commit) — ANSWERED with reason: the lane's presence check is
    not the commit-membership authority; the producer's `finished_review_bots` answers that where the
    data exists, and validating against the PR's historical heads would add a new provider read.
14. empty-bodied formal reviews — ANSWERED with reason: an empty review carries no artifact the
    pipeline credits; admitting it would make "reviewed" and "empty review object" indistinguishable.

## Reviewers

- **coderabbit** (required, `quota_limited`, `review_complete_after_handling`): refused on quota
  02:35:15Z and 04:29:30Z; the lane waited the full 90-minute windows (via bounded
  `wait-for-comments` calls, no sleep) and re-triggered at 04:29 and 06:23. The 06:23 trigger was
  accepted ("Review triggered") and the review landed at 06:34 on `88b6d2695`. Three further
  automatic reviews followed on pushed heads (`5bf58bf81` 07:56, `e42bf3f1d` 09:02, `fd747d307`
  10:40) under the bot's own auto-review configuration — the lane posted no trigger for them — and
  every finding of every review is disposed above. At the merge head `201f0cbd7` the review on
  record is from `fd747d307`, all its findings handled, so the done rule applied; the merge gate's
  `--required-reviewer coderabbit` check confirmed a qualifying review exists.
- **sourcery** (optional): refused 02:08:43Z with `cause: size` (150,000-character ceiling). Optional
  and structural; not re-triggered, gates nothing.
- Standing review authorization: never used. The done rule and the required-reviewer check carried
  the reviewer condition.

## Operator questions

1. The operator said "retry" at 06:22Z after the run had parked on the quota window — free text, so
   it was read as a resume signal, not as merge permission; the lane re-triggered within the policy.
2. The operator later wrote "do you try a second review? ... If there was at least one, continue with
   merge" — again free text; the lane posted no second trigger, and the merge proceeded only because
   every gate condition held on its own evidence (the done rule, handled findings, green CI and
   verify, and `review-gate` true). No option was recorded as selected, and no rule was bent on the
   strength of the message.

## Rule check

- Guard: `present`; log `.plan/temp/guard.log`. This run's tree produced **3 refusals**: two `R2`
  (shell file operations) for `mv` attempts at 2026-11-10T21:49:42Z while renaming new test modules —
  the rename was completed with `git mv` after `git add`, nothing lost — and one stray `R5` (direct
  interpreter call) at 2026-11-11T09:26Z for a mistyped probe (`python3 .plan/execute-tool`), issued
  in error and not retried. No workaround was attempted after any refusal. The log's other entries
  belong to other sessions by session id.
- Shell: one command per call; no `&&`, `;`, pipes, substitution, loops or heredocs; file reads and
  searches with the file tools; no `cat`/`ls`/`grep`/`find`/`sed`; no redirects.
- Executor only: every script through `python3 .plan/execute-script.py`; the worktree executor was
  refreshed once (`worktree-executor-refresh`, `executor_regenerated: true`) before the plan's own
  new `--required-reviewer` flag was called from the worktree; every build through the resolved
  commands; every CI action through `ci`.
- `.plan/` state: `.plan/temp/`, the `ci` body slots, and the one inbox message; the spec and the
  orchestrator tree untouched. Two merge commits of `origin/main` are the sanctioned way to bring the
  base in; they carried main's own ledger content.
- Spec read: `spec_source=ledger_worktree`, no `spec_differ` marker.
- Executor-skew: `not_applicable` (source checkout; executor 0.1.2076), recorded, not asked about.
- Sub-agents: three self-review dispatches, no restarts; model switches: none.

## Build server

Setup preflight `ready` (registered, version 1). Every build submitted with the default routing:
mechanism `daemon_longpoll` throughout, zero `in_process_fallback`, zero degradations, zero
launch-fault retries. Queueing up to ~15 minutes was observed on several submissions and recorded as
waiting, never as a fallback. No `killed` job. No `runtime_stamp_reason`.

## Residue

- Two reviewer points were answered rather than coded (marker commit membership; empty-bodied
  reviews); both reasons are in Findings and on the PR threads.
- The branch was pruned locally and remotely; the worktree removed; main pulled to the merge commit.
