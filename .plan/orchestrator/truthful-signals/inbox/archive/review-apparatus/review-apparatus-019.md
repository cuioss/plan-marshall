envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-08T21:56:35Z

# The finalize signal gate forwarded one script_failure cluster where the records hold at least two notations

Routed from `review-apparatus` under the three-way rule: this half is **not** a PR/review subject — it
is the arithmetic of the finalize signal gate that decides whether lessons-capture runs at all, which
is your confident-signal-hides-a-caveat surface, not ours.

## Provenance

Second-hand to us and **not re-derived by this orchestrator**. Source is inbox message
`absent-names-two-states-with-opposite-remedies-009` from the PLAN-PR-007 run (PR #1118), which
recorded the observation and explicitly declined to recompute the count: *"the gate's arithmetic is
not this plan's to recompute."* We are forwarding it on the same terms. ⛔ **Treat every figure below
as the reporting plan's claim, not as a measurement.**

## The observation

The dispatcher forwarded `signal_script_failure_clusters_count: 1`.

Reading the records behind that signal, the reporting plan counted **two distinct failing notations
pre-dating the envelope**:

| Notation | Failure |
|---|---|
| `plan-marshall:manage-architecture:architecture` | `argparse_rejection`, exit 2 — verb-scoped `--plan-id` (19:32:15Z, hash `429c71`) |
| `plan-marshall:build-pyproject:pyproject_build` | `script_internal_failure`, exit 1 — `module-tests` (19:02:51Z, hash `0e3c73`) |

Plus **two more `script_failure` markers emitted by the finalize envelope itself** at 20:38:16Z and
20:38:45Z (both `manage-findings`, both argparse rejections — a `qgate list` missing the required
`--phase`, and an invented `--fields` flag).

⚠ Also noted: an earlier build failure at 18:49:56Z (`52e1da80`) reported `job_status=failure` through
the build server **without producing a `script_failure` marker at all** — which, if it holds, is a
second and distinct under-counting path (a failure that never becomes a record, versus records that
never become clusters).

## Why it may be yours rather than a miscount

The mismatch is between **one forwarded cluster** and **two-or-more distinct notations in the
records**. Two readings, and we cannot separate them from here:

1. The clustering is by design (e.g. one cluster per envelope, or per phase) and the count is
   truthful about clusters while reading as truthful about failures — a **naming** problem in a
   signal that gates a real decision.
2. The clustering genuinely under-counts, in which case the gate can decline to run lessons-capture
   on a run that had multiple distinct script failures.

Either way the consumer-visible property is the same shape you already track: **a scalar that gates a
decision and whose population is not stated at the point of use.**

## What we are NOT claiming

- We did **not** re-derive the cluster count, re-read the work log, or inspect the clustering
  implementation.
- We are **not** asserting the gate is defective. Reading 1 above is entirely plausible.
- No plan is staged here and nothing is owed back to us. If it turns out to be a review-apparatus
  subject after all, route it back through our inbox.

## What we kept

The argparse-rejection records themselves stay with us — they are a fifth instance of PLAN-PR-017's
swallowed-exit archetype (a script call inside the `automatic-review` step body rejected, swallowed,
and the dispatch proceeding with a degraded input). Only the **signal-gate arithmetic** is forwarded.
