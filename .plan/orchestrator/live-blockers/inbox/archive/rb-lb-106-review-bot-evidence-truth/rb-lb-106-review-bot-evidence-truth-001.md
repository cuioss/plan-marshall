envelope_version=1
sender_type=plan
sender_id=rb-lb-106-review-bot-evidence-truth
epic=live-blockers
kind=landing
created=2026-11-05T21:58:35Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-106-review-bot-evidence-truth
epic=live-blockers
pr=#1912
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2025
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (`.plan/temp/guard.log`)

## Deliverables

Spec read from the **ledger worktree**; `spec_source=ledger_worktree`, and `spec_differ=true` — the main
checkout's copy carries four deliverables while the ledger copy carries five. The run followed the
ledger copy (D1–D5).

| # | Verdict | Order | Test | Failing run / evidence | Commit |
|---|---|---|---|---|---|
| D1 | met | test-first | `test_a_new_format_summary_credits_the_head_it_covers`, `…_covering_an_earlier_head_is_stale`, `…_answers_the_re_review_for_its_head` | `5c1e70ab4`, log `python-2026-11-05-072151.log` | `278564f30` |
| D1 | met | none | `test_a_new_format_summary_with_a_non_reviewed_kind_credits_nothing` | negative control | `278564f30` |
| D2 | met | test-first | `test_a_thread_reply_after_the_head_credits_nothing`, `test_a_finished_head_review_outranks_an_older_quota_refusal`, `test_a_review_body_edited_in_place_naming_an_earlier_commit_credits_nothing` | `5c1e70ab4` log `…072151.log`; the edited-in-place fixture `f973dab28` log `python-2026-11-05-072319.log` | `278564f30` |
| D2 | met | n/a | existing currency / refusal / clean-review suites green | targeted 1,570-test sweep; full `verify` | `278564f30` |
| D3 | met | test-first | `test_ingest_keeps_the_tail_of_a_cut_body_and_says_it_was_cut`, `test_over_maxlength_string_keeps_its_tail_and_marks_the_elision`, `test_the_clamp_reports_the_original_length_as_a_structured_field` | `5c1e70ab4`, log `…072151.log` | `1ff6a3f0c` |
| D3 | met | none | `test_ingest_promotes_a_body_under_the_cap_byte_identically_with_no_flag` | green at HEAD | `1ff6a3f0c` |
| D4 | met | none | `test_a_second_review_inline_comments_outside_a_resolved_thread_are_filed` | **green at HEAD** `5c1e70ab4` (log `…072151.log`); the PR records it, and the surviving #512 lead is the documented resolved-thread skip, with nitpicks-in-review-body left as a lead only | `1ff6a3f0c` |
| D5 | met | test-first | `test_a_sourcery_review_body_with_overall_comments_and_the_footer_is_filed`, `test_the_sourcery_doc_states_the_footer_rule_once`, `test_only_sourcery_declares_footer_markers` | `5c1e70ab4`, log `…072151.log` | `1ff6a3f0c` |
| D5 | met | none | `test_a_sourcery_comment_with_no_signal_is_still_dropped_as_noise` | matched negative control | `1ff6a3f0c` |

Per-head test runs against pushed heads: full `verify` green at `dabb78c06` (32,667), `25e84e27d`
(32,670), `c27312d21` (32,743), `7ad69fd66` (32,744), `ea5f80545` (32,787), `b09d230fc` (32,788); CI
`verify` green on every pushed head.

## Personas and skills

- implementation: `persona-implementer`; tests: `persona-module-tester`; every self-review round and
  every PR-comment triage: `persona-code-reviewer`.
- Per deliverable domain skills: `skills: none named` (the spec declares none).

## Hypotheses

- `named_commit_currency` reads only commit tokens — **confirmed** (`_github_pr.py` L383-405 pre-fix).
- The coverage marker is an HTML comment carrying `sourceCommitId`/`coveredCommitId`/`kind` —
  **confirmed** from the runbook lane's fixture and the epic's recorded landings.
- Inline records carried `commit_id: ''` and no placement — **confirmed** (`github_ops.py` L780-797
  pre-fix).
- The provider can report reply and placement — **confirmed** by adding
  `replyTo`/`commit`/`pullRequestReview.commit` (`PullRequestReviewComment`), with thread position as
  the fallback.
- The pre-merge barrier keeps an old refusal blocking — **confirmed** (`pre_merge_gate.py` L718-745
  forwards the sets; `classify_bot` L884-895 ranks current participation above a refusal).
- `raw_input` byte cap is 64 KiB with `[truncated]` — **confirmed** (`_findings_core.py` L151-180).
- The lost Sourcery body is the `review_body` carrying Overall Comments — **confirmed** (whole-body
  `ignore_patterns` match, `github_pr.py` L510 pre-fix).
- No other bot declares footer markers — **confirmed**.

## Findings

- Self-review round 1 (12 findings): fixed the GraphQL fragment shared with `IssueComment` (blocker),
  the unparseable-marker fall-through, stale docs/comments, added the marker-name guard and census
  seeds; commit `622f63c0d`.
- Self-review round 2 (7 open): fixed the re-review gate admitting a non-finished coverage marker,
  the inline/thread-reply and footer-strip docs, the marker-surface inventory, and the vacuous `kind`
  guard; commit `e02490a9f`.
- Self-review round 3 (1 open, doc drift): operator asked at the round limit and selected "fix the doc
  drift, then continue"; fixed in `dabb78c06`.
- CodeRabbit PR findings, all fixed and every thread replied + resolved: stale truncation facts,
  `clamps[]` scoping, the URL-item guarantee, marker presence on the bare identifier, the dropped
  placement fields (the one that would have made the inline rule inert), the copied query-field list,
  the nested-vs-direct commit path, the per-field truncation retention, and the cleared-key wording.
  Commits `25e84e27d`, `d9be145ce`, `7ad69fd66`, `284d111f2`, `b09d230fc`.
- No CI findings.

## Reviewers

| Reviewer | Required | Outcome | Head(s) | History |
|---|---|---|---|---|
| coderabbit | yes (`quota_limited`) | reviewed, then quota-refused on later heads | reviewed `dabb78c06` (14:52), `c27312d21` (15:51), `d9be145ce` (17:00), `3084d75df` (18:06), `ea5f80545` (20:24) | triggered 11:41, 13:13, 14:45 (escalated, produced the first review), 15:30, 16:54, 17:32, 18:00, 18:41, 20:17, 20:58; refusals at 11:41, 13:13, 15:30, 17:33, 18:41, 20:58. Standing review authorization used for the final head: qualifying review on `ea5f80545` (`coveredCommitId=ea5f80545`, `kind=reviewed`), every finding handled, re-triggered once after the `b09d230fc` push and refused on quota, all other gates green on `b09d230fc`. |
| sourcery | no (optional) | refused, size ceiling | — | triggered 11:41; refused "larger than the review limit of 150,000 diff characters" (cause=size). Optional, so it does not gate. |

## Operator questions

1. "Self-review reached its 3-round limit with one low-severity documentation-drift item open; how
   should the run proceed?" — options {fix the doc drift then continue, proceed now with it open, stop
   the run}; selected **"Fix the doc drift, then continue"**.
No free-text operator messages.

## Rule check

- Guard refusals in this run's session tree (all corrected immediately, no workaround attempted):
  R1 for a chained `ls … || echo`; R7 twice for writing a file in the main checkout before switching
  to the worktree; sub-agent rounds attempted `cd … && pytest`, bare `pytest` and a `grep -rniE`
  (R1/R4), each refused and not retried as a workaround.
- Shell file operations the run issued that the guard did not refuse, counted here rather than left
  to the log: `tail`/`grep` on build logs (in-process results and daemon job logs) to read the test
  summary, `wc -l` on the guard log, and one `> /tmp/opencode/pr1912-comments.txt` redirect (a shell
  file write outside `.plan/temp/`, abandoned immediately and not used afterwards).
- Builds: every routed build ran through the resolved commands; the daemon was `down` at setup and
  later `ready` — both mechanisms were used, no build was backgrounded, one whole-suite run expired at
  the 1555s bound and the split form was continued with `--timeout 2000` (recorded in the progress
  file). No `killed` job.
- Executor skew: `not_applicable` (source checkout; the executor maps this checkout's own scripts).
- Spec read: `spec_source=ledger_worktree`, `spec_differ=true` (main copy: 4 deliverables; ledger copy:
  5) — recorded rather than read silently.

## Build server

- Setup preflight for the worktree: **down** (`unreachable`); resolve reported `build_server: down`.
- Per-build mechanism: early builds `in_process_fallback` (daemon unreachable); after the daemon
  returned, `daemon_longpoll` for quality-gate and verify runs. Fallbacks: every early build degraded
  with `reason=unreachable`; no `executor_absent_from_worktree` fallback (`executor_in_worktree:
  present`); no launch-fault retry; no `killed` job.
- No `runtime_stamp_reason` was reported at landing time.

## Residue

- The spec's D1 wording "no verdict when the marker is absent or unreadable" is contradicted by the
  shipped (fail-closed) behaviour: a present-but-unreadable marker yields "never credit", not "no
  verdict". The code and the standards docs state the shipped rule; the spec line is worth re-reading
  on landing so a later round does not restore the fall-through.
- Sourcery's size-ceiling refusal is structural and unrelated to this change (the PR is larger than
  its 150,000-character ceiling); it remains optional and ungated.
