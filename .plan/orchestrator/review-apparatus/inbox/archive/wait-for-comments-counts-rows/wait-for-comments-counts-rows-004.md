envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=finding
created=2026-08-01T17:08:04Z

## Finding — review-retrospective maps `accepted` → `false_positive`, so a clean PR reports PR-Agent as 100% false-positive / 0.0% resolved-as-fixed

**Surfaced by:** PLAN-PR-001 finalize (`finalize-step-review-retrospective`). **Not this plan's defect.**

**Component:** the review-retrospective aggregator (project-local `finalize-step-review-retrospective` + the per-reviewer metrics pass it drives).

### Observation

The aggregator's resolution-bucket mapping sends `resolution: accepted` into the `false_positive` bucket.

On a **clean** PR, PR-Agent's only record is its meta status summary ("## PR Reviewer Guide"), which always closes as `accepted` — it is not actionable, so it is neither fixed nor rejected. The mapping therefore converts the single accepted meta record into a false positive, and the per-reviewer roll-up reports:

- `false_positives_count` = the whole record set
- `pct_resolved_as_fixed` = **0.0%**

i.e. the sole participating reviewer on a clean PR is scored as **100% false-positive**, precisely when it behaved correctly.

### Why this is not self-correcting

The signal is recoverable *only* if the consumer also reads `actionable_count` / `meta_count` and re-derives the ratio over the actionable slice. Any cross-plan roll-up that consumes `false_positives_count` or `pct_resolved_as_fixed` **alone** — the two headline fields — systematically penalises PR-Agent on every clean PR, and the penalty compounds with the number of clean PRs.

The failure is silent: the numbers are well-formed and plausible, so nothing downstream signals that the denominator is wrong.

### Fix shape (not a decision)

Two candidate directions:

- Stop collapsing `accepted` into `false_positive` — `accepted` means "acknowledged, no action required", which is not the same claim as "the reviewer was wrong". Give it its own bucket.
- Or exclude meta comments from the resolution-bucket denominator entirely, so a reviewer whose only record is meta is reported as *no actionable signal* rather than as *all-wrong signal*.

### Interaction with the sibling finding

The sibling `ignore_patterns` finding proposes filtering the Guide comment out at the producer. If that lands first, PR-Agent's clean-PR record becomes **empty** rather than one-accepted — which changes this defect's shape rather than fixing it. Sequence the two deliberately; do not assume either one subsumes the other.

### Epic relevance

`review-apparatus` owns automated-PR-review reliability. A per-reviewer quality metric that inverts a correct review into a maximally-bad score is a direct truthfulness defect in the epic's own measurement layer.
