envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:05:54Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# Actionable review findings hide in the review BODY outside the diff range — inline comments are not the review population

## Observation

On PR #1065, one CodeRabbit review carried **2 inline actionable comments** and, embedded in
the **review body itself**, **3 further findings flagged as outside the diff range**. All
three of the body-embedded findings were verified real against HEAD:

- a `force_push` misclassification,
- a cleanup-retention `KeyError` risk,
- a doc/resolver mismatch.

They were remediated as TASK-018 (follow-up commit `4ad98b41`). Had the run enumerated only
the inline comments, all three would have shipped — and the finalize signal would have read
as a fully-dispositioned review, because every *inline* comment had a disposition.

## Why this is the epic's theme

This is a population-under-count that manifests as a *complete-looking* disposition report.
The count "2 of 2 inline comments dispositioned" is true and is not the coverage number. The
review's actionable population was 5.

It is the same shape as the standing rule that *a reviewer's list of call sites is a SAMPLE,
not an enumeration* — here the sample boundary is the diff range rather than the reviewer's
attention.

## Corrective rule

**The actionable population of a review is `inline comments ∪ findings embedded in the review
body`.** A review-fetch surface that files only inline comments as findings under-counts by
construction, and the under-count is silent.

Concretely:

1. When fetching review findings, parse the **review body** as well as the inline comment
   thread. CodeRabbit explicitly labels out-of-range findings there; they are not noise.
2. A body-embedded finding names a file and a symptom but carries **no diff anchor**, so it
   must be **verified against HEAD** before disposition — it may already be fixed, or may
   reference a line that moved. Verified-real is the bar, not plausible-sounding.
3. Do not treat "every inline comment has a disposition" as "the review is dispositioned".
   The two are different claims and only the second is the gate's intent.

## Routing note

This finding concerns automated-PR-review reliability and may belong to the sibling
`review-apparatus` epic rather than to `truthful-signals`. The plan performs no
classification — the orchestrator holds the cross-epic context to decide.
