# PLAN-10: review-barrier-noise-filter

epic: plan-optimization
workstream: WS-04

> Staged plan spec. Surfaced during PLAN-06 (#929) finalize and filed as lesson `2026-07-18-14-002`;
> the barrier surface was orchestrator-verified 2026-07-18 (the noise pre-filter exists but does not
> cover these two comment classes). Relates to still-open lesson `2026-07-13-21-001` — fold at outline.

## Objective

Stop the phase-6 pre-merge comment-completeness barrier from looping on comments the pipeline itself
produced. When `re_review_on_branch_cleanup=true` and `pre_merge_comment_barrier=fail_into_loopback`,
`branch-cleanup`'s trigger-A re-review posts a `@{bot} review` trigger comment (because the pre-merge
rebase advanced HEAD); the barrier re-fetches PR comments, files that very trigger comment as an
unhandled finding, and loops back to `6-finalize` → trigger-A fires again → another trigger comment →
barrier blocks again, terminating only at `max_iterations` (burning ~2 finalize iterations + a 600s
re-review timeout). Bot rate-limit service-notice replies are ALSO filed as pending findings,
compounding it. Observed twice (PLAN-06 #929; the churn class in `2026-07-13-21-001`).

## Deliverables

### D1 — barrier/fetch_findings must not flag pipeline-authored or service-notice comments

**Verified (orchestrator, 2026-07-18):** `github_pr.py` runs a two-layer producer noise pre-filter
sourced from `standards/comment-patterns.json` (+ `bot_kind_for_author` from `github_re_review`,
`_detect_coderabbit_rate_limited` in `_github_pr.py`), but it does NOT drop (a) self-authored
`@{bot} review` re-review TRIGGER comments, nor (b) bot rate-limit SERVICE-NOTICE replies.

**Fix (confirm exact layer at outline):** extend the `fetch_findings` producer noise pre-filter to
classify and drop both classes so they never become barrier findings — a self-authored re-review
trigger comment (posted by `github_re_review`) is pipeline output, not a reviewer finding; a bot
rate-limit notice is a service message, not a finding. **Acceptance:** with
`re_review_on_branch_cleanup=true` + `fail_into_loopback`, a rebase-triggered re-review does NOT cause
a loopback cycle; genuine unaddressed reviewer findings STILL block the merge (the barrier's real
purpose is preserved). Add a regression test reproducing the trigger-comment + rate-limit-notice
filing and asserting neither reaches the barrier.

> **Outline must confirm:** whether the noise-filter alone breaks the loop, or whether the
> trigger-A-re-review-on-rebase interaction also needs gating (e.g. do not re-post a trigger comment
> when the only delta since the last review was a pipeline rebase). Do not pre-decide — the noise
> filter is the primary approach; the trigger-gating is a fallback to evaluate.

## Expected Surface

- `workflow-integration-github/scripts/github_pr.py` (`fetch_findings` producer pre-filter)
- `workflow-integration-github/standards/comment-patterns.json` (pattern data)
- `workflow-integration-github/scripts/github_re_review.py` (`bot_kind_for_author` / trigger-comment authorship) + `_github_pr.py`
- tests: barrier-noise regression

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none in flight — disjoint from PLAN-07 (manage-config), PLAN-08 (executor),
  PLAN-09 (ci merge-queue enable). Startable concurrently.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-10-review-barrier-noise-filter.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-10.md is recorded}
