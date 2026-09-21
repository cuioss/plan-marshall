envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=landing
created=2026-09-03T19:06:21Z

## What landed

documented-invocations-cannot-succeed-as-written shipped as #1386 (merged), squash-merged through the platform merge queue as 71279cc024fdc256358e81df509a81c5b6770ec1.

```landing-facts
schema=landing-facts/1
plan_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
pr=#1386
merge_state=merged
deliverables_total=4
deliverables_done=4
total_tokens=6377728
total_wall_seconds=100943
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.action=merged
step.branch-cleanup.upstream_commit_count=6
step.create-pr.pr_number=1386
step.record-metrics.total_tokens=6377728
step.record-metrics.total_wall_seconds=100943
```

## Residue

Items this run observed that no step recorded as a fact. Each is filed as a plan finding and routed; none was fixed in this plan, and each records why.

**Routed to this epic (truthful-signals):**

- `d6bf20` — `toon_parser` CSV/TSV round trip loses a tab-bearing value under `table_separator=','`. Verified at source in both directions: `value_needs_quoting` carries no tab term, and `_parse_csv_row` tests for a tab in the RAW row before any quote handling, so quoting alone does not cure it. Provenance established: pre-existing, NOT introduced by this plan — `value_needs_quoting` is a byte-identical extraction of the inline expression already in `_serialize_value`, and `_parse_csv_row` is not in the diff. Surfaced by CodeRabbit as a Major; premise ("the new contract") refuted, defect upheld.
- `f3d2df` — `triage.md` Step 6 asserts the scope-deviation guard "never escalates a PR-touched-file finding", justifying it via signal 1 alone while signal 3 can fire on a PR-touched file. This plan's own finding `c128cb` landed in exactly that cell.
- `50bab4` — `prune-local-and-remote-ref` hard-fails on an already-deleted local branch (deleted moments earlier by `worktree-remove`) and aborts before the remote-ref prune it exists to perform. Its remote half has a tolerant `show-ref` guard; its local half does not. Worst on the merge-queue path, where the stale tracking ref is precisely what needs cleaning.
- `7d3960` — `manage-metrics enrich` takes ONE `--session-id` while `session_ids` is deliberately a list. This plan spanned two sessions; only the last was walked, and nothing in the return says the earlier one was not.
- `7bf19d` — `generate.py`'s docstring and `marketplace/targets/README.md` state "Always invoked through the `./pw` wrapper" and that a bare `python3` cannot import PyYAML. Both are false of this repository's own CI, which invokes the bare form after installing the dependency. The plan's own theme, inverted.

**Routed to review-apparatus (PR/review surface — the PR test wins outright):**

- `9f7923` — `head_sha_verified` is hard-coded `false` on the issue-comment re-review path; `_references_head_sha` is applied only on the review path. pr-agent's declared publish shape IS an issue comment and it is this project's only REQUIRED bot, so every genuine re-review of it classifies as an incremental-review decline. It did not block only because the participation signal outranked the decline observation.
- `65f631` — the pr-agent registry doc states the bot posts no inline comments, only a persistent issue_comment; this run recorded the inverse. Together with `9f7923`, pr-agent's declared and observed publish shapes now disagree in both directions.
- `7dfe44` — Sourcery's refusal reached the pre-merge barrier as `cause=size` (150k diff-char ceiling; remedy split, never awaitable) and the findings store as a weekly account quota (250k/7d, reopening in 5d4h; remedy backoff, awaitable). The registry separates these modes because they route differently. Harmless here only because Sourcery is optional.

**Run-shape observations for the epic, not filed as findings:**

- The `5-execute → 6-finalize` boundary was crossed with the phase's declared verification never having run — the manifest declared 3 `verification_steps` and the execution log holds zero `record-step` rows for `5-execute`. The gap closed only because the loop-back later re-fired `pre-push-quality-gate` against the newer HEAD. Absent the loop-back this ships unverified with nothing reporting it.
- `metrics.toon` still reports `re_entered_phases: []` after a completed `6-finalize → 5-execute → 6-finalize` loop-back with `loop_back_iteration: 1`.
- Cost: 6,377,728 tokens / 40,734,118 billing-weighted against a 2.0M anchor for `multi_module + bug_fix`. `6-finalize` alone accounts for 3,543,944. The largest single contributor is `pre-submission-self-review` — 5 firings, 3 terminating in `error`, ~738k tokens.
- The plugin-registry pin gap re-opened after this run's cache sync (18 entries to repin at `0.1.1588`); repair is operator-only and was not performed.
