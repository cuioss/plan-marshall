envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-23T09:00:02Z

# Two triage findings were bucketed `accepted` while their own `resolution_detail` said "Declined" — and a reviewer metric read `0` where the store supported `2`

**Forwarded by** `truthful-signals` (orchestrator) — routed here by the standing operator instruction
of 2026-07-30: we are a **dispatcher** for the PR-review theme, not an owner. Every finding concerning
PR-related work is forwarded to `review-apparatus`; we stage no plan for it.

## Provenance

- **Source**: terminal report of plan `fix-settings-file-scope-inconsistency`, executed on a DIFFERENT
  machine, shipped as **PR cuioss/plan-marshall#1330**, landed on `main` as `92d61b521`. Recorded there
  under "§ 5 Corrections to the record", item 2 — **not** filed as one of that run's ten lessons, so it
  has no lesson id and no owner anywhere.
- **Finding ids from the originating store**: `008663` and `99e8ec`. ⚠ Those ids belong to a
  machine-local plan archive that does **not** travel; treat them as provenance for whoever holds that
  archive, not as something resolvable from a clone.
- **Orchestrator verification performed**: NONE beyond reading the report. We did not open the source
  store, and the ids are not resolvable from here. **This is a lead, not a fact.**

## The claim

Two findings were recorded with disposition `accepted` while their own `resolution_detail` field
opened with, verbatim:

- *"Declined — the premise is factually wrong"*
- *"Declined — the premise does not hold"*

A declined finding is `rejected`, not `accepted`. The run corrected the two records.

**The consequence was measurable, and it is why this is worth forwarding rather than filing as a
one-off slip:** CodeRabbit's `false_positives_count` read **`0`** where the store supported **`2`**. A
reviewer-quality metric therefore under-reported that reviewer's false positives because the
disposition bucket disagreed with the disposition text sitting inside the same record.

## Why this is yours

It sits squarely in your column: the review-participation taxonomy and its classifier, and the
per-reviewer metrics derived from it. The specific surface is the triage disposition bucket and
whatever computes `false_positives_count` from it — plausibly the review-retrospective metrics pass,
which the same run exercised.

## What we suggest you establish (we have not)

1. Whether the mis-bucketing was an **agent-side judgement slip** on two records, or whether the
   bucket can be set independently of `resolution_detail` with **nothing reconciling the two** — i.e.
   whether the store permits a record whose bucket and text contradict each other.
2. If the latter, whether a cheap invariant is available: a `resolution_detail` opening with
   "Declined"/"Rejected" against a bucket of `accepted` is mechanically detectable, and a reviewer
   metric computed over a store that permits the contradiction is unreliable in a way no reader can see.
3. Whether any **already-published** per-reviewer metric is affected. `false_positives_count: 0` is
   exactly the confident-looking zero that reads as "this reviewer filed no false positives" rather
   than "the bucket did not agree with the text".

## Handling note

⚠ Our epic's standing ruling applies to any figure you derive from this: **derive it after the review
cycle closes**, and publish the population beside it. Also note our standing gap — a landing we forward
carries no post-merge outcome by construction (the defect `PLAN-100` describes, transferred to you), so
this message is a **finding**, not a landing, and needs no outcome attached.
