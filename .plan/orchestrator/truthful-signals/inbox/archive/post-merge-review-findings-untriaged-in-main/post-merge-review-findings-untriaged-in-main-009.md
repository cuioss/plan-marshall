envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=finding
created=2026-07-29T12:10:06Z

# PR #1048's review-evidence guard fails on every synchronize push, blocking the merge queue

category: bug
component: plan-marshall:automatic-review

## What happens

`.github/workflows/pr-agent.yml` (added by #1048, "review every pushed HEAD so
the primary bot's evidence is reliable") ends with a guard step:

```bash
if [[ -z "$REVIEW_OUTPUT" ]]; then
  echo "::error::PR-Agent produced no review for this run. ..."
  exit 1
fi
```

But the pr-agent action itself logs, on the same run:

```
Skipping action: synchronize
```

pr-agent does not review on `synchronize` events, so `REVIEW_OUTPUT` is empty by
construction on every push-triggered run, and the guard fails the job. The
failure is deterministic, not transient — re-running reproduces it.

## Impact

`review / review` goes FAILURE on any PR that pushes a commit after opening.
Observed on PR #1045 at HEAD `2c53f3d66` (run 30449502213, 39s). The PR's own
`verify / conclusion`, `verify / verify`, `CodeRabbit`, `dependency-review`,
`generate-check`, `verify / gate` and `license/cla` were all SUCCESS, yet
`merge_state` stayed `unstable` and the merge queue would not admit the PR.

This blocks the merge queue for every multi-commit PR in the repo, not just this
one.

## The irony worth recording

#1048's stated purpose is to make the primary bot's review evidence *reliable*.
Its guard asserts "a review must exist" while the action's event configuration
guarantees one will not. The guard is unreachable-by-construction in the exact
case it was written for — the same unreachable-guard shape #1042's self-review
detector was built to catch, shipped one PR later.

## Remedy directions (not prescribing)

Either gate the guard on the events pr-agent actually reviews, or configure
pr-agent to review `synchronize`, or make the empty-review case a warning rather
than a job failure so it degrades honestly instead of blocking the queue.
