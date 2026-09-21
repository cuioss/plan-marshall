envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:50:47Z

# Publish a VERIFY tag count so logging-gap cannot report an unmeasured zero

component: plan-marshall:plan-retrospective
category: improvement
confidence: high
source_plan: plan-truth-157
source_aspects: logging_gap_analysis, log_analysis

## Context

`logging-gap-analysis.md` asks the aspect to grade an `expected_vs_actual` row per log category, VERIFY
among them. The facts it grades come from `analyze-logs`, which publishes `top_tags` — the five most
frequent tags only. On this plan those were STATUS (88), ARTIFACT (40), STEP (35), DISPATCH (31) and
SKILL (27). VERIFY was not among them, so no VERIFY count exists anywhere in the published facts.

The aspect is therefore asked to fill a row for which no measurement was published. The count is bounded
above by 27 (the fifth-place tag) and is not known to be zero. Writing `observed: 0` would render an
unmeasured category as a clean measurement — indistinguishable, to any reader of the compiled report, from a
genuinely verified absence of VERIFY logging.

This aspect reported `VERIFY: unmeasured` with its reason instead, which is why the compile step returned
`sections_unattributed_zero: []`. The next run has nothing stopping it from writing the zero.

## Root cause

The fact extractor publishes a *ranked* tag view (`top_tags`) while the consuming reference expects a
*keyed* one (a count per named category). A category that falls outside the top five is absent from the
facts, and absence is one keystroke away from being reported as zero.

## Proposed action

Have `analyze-logs` publish an explicit per-category count for every tag the logging-gap reference names —
STATUS, DECISION, ARTIFACT, VERIFY, ERROR — alongside the existing `top_tags` ranking. Each graded row then
has a real denominator, and a category that genuinely did not occur is published as a measured `0` rather
than inferred from its absence from a ranking. Keep `top_tags` as-is: the two views answer different
questions and the ranking is useful on its own.

## Evidence

- aspect: log_analysis — `top_tags[5]` carries STATUS, ARTIFACT, STEP, DISPATCH, SKILL; VERIFY appears in no
  published field
- aspect: logging_gap_analysis — `VERIFY,6,unmeasured` with `verify_tag_reason` naming the extractor's
  top-five publication as the cause, and a `warning`-severity finding that the row carries no verdict at all
- The gap is in the retrospective's own fact schema, not in the audited plan's logging discipline

## Why this is worth a lesson rather than a one-line fix note

The shape — a consumer asked to grade a category the producer may not have published — generates a
plausible-looking zero on every run where the category is quiet. It is the could-not-look-reports-benign
collapse inside the machinery built to detect that collapse elsewhere.
