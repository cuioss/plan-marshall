envelope_version=1
sender_type=plan
sender_id=domain-post-plan-narrow
epic=operator-ux
kind=candidate-lesson
created=2026-09-06T07:28:09Z

# Candidate lesson: the forwarded `signal_script_failure_clusters_count` was 1, but two distinct failing notations are in the log

**Source**: plan `domain-post-plan-narrow` (PLAN-03, epic `operator-ux`)
**Signal source**: the signal-gate count itself, compared against the records it summarises
**Suggested component**: `plan-marshall:phase-6-finalize`
**Suggested category**: `bug`
**Dedup read**: NEW as stated, but structurally the same shape as `2026-09-06-07-001` (reviewer-yield undercount) that the retrospective filed this run — the orchestrator may prefer to fold it there.

## Observation

The dispatcher forwarded `signal_script_failure_clusters_count: 1` to this step. The step's own reading of the work log — which the workflow permits, since the prohibition is on re-deriving the count, not on reading the records behind it — shows **two** distinct failing notations under the documented `[ERROR] … script_failure` marker class:

| Timestamp | Notation | `failure_kind` |
|-----------|----------|----------------|
| `2026-09-05T23:24:31Z` | `plan-marshall:workflow-integration-github:github_pr` | `argparse_rejection` (exit 2) |
| `2026-09-05T23:37:08Z` | `plan-marshall:automatic-review:review_completeness` | `argparse_rejection` (exit 2) |

The cluster definition is "number of distinct failing script notations … union dedup by distinct notation". Two distinct notations dedup to two, not one. The observed window was the most recent 400 of 695 work-log entries, so a wider read can only raise the observed figure, never lower it.

## Why it matters

The count is a **gate**, and this step is the consumer that acts on it. An undercount does not merely misreport: at the boundary it silently converts a non-zero signal into a skip. Here the count was non-zero for other reasons so nothing was lost, but a run whose only signal was a two-notation script-failure cluster reported as one would still fire; a run whose only signal was a cluster reported as **zero** would skip lessons-capture entirely, and the skip would be indistinguishable from a clean run.

That is the same shape as the reviewer-yield undercount recorded this run as `2026-09-06-07-001` — a measurement that is read as a population, is smaller than the population, and drives a gate.

## Candidate corrective

Have the gate publish the population it counted over alongside the count (the notation list, and the entry window scanned), so a consumer can tell an accurate `1` from a truncated `1`. This is the same "a count rides with its denominator" discipline already applied across the `corpus` and `inbox list` surfaces.

## Caveat

This candidate is a discrepancy between a forwarded value and a partial re-read, not a diagnosed defect: the step deliberately did not re-derive the count, so the cause (a marker-class gap, a dedup bug, or a window difference) is unestablished. It is filed so the orchestrator can decide whether to investigate.
