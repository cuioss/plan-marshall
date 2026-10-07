envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:23:38Z

component=plan-marshall:phase-3-outline
category=improvement

# Assessment coverage must span every distinct declared path, read-intent ones included

The outline's assessment sweep filed 11 `CERTAIN_INCLUDE` assessments over a
declared-path set of 12. The uncovered path was
`test/plan-marshall/manage-providers/test_providers_core.py`, declared in
deliverable 3 with **read** intent — and read intent is exactly why it was
skipped: a path nobody plans to modify reads as needing no scope judgement.

It did need one. That deliverable's third success criterion asserted that
`_providers_core.VALID_AUTH_TYPES` and its tests were untouched and still green,
and this file WAS that test. The criterion rested on a file the assessment store
had no record of, so nothing tied the claim to evidence.

## The failure shape

An assessment sweep that iterates the paths it intends to *change* produces a
count that looks complete against the modification set while being short against
the declared set. The gap is invisible at the sweep site — 11 assessments for 11
files-to-edit is a clean-looking number — and only a cardinality check against
the union of declared paths exposes it.

## Solution

Derive the assessment population from the **union of every deliverable's
`Affected files:` entries**, partitioned by intent but never filtered by it, and
compare `len(assessments) == len(distinct_declared_paths)` before reporting
coverage. A read-intent path either carries an assessment recording the evidence
that grounds the criterion depending on it, or it is dropped from `Affected
files:` — the one thing it may not be is declared-and-unassessed.

## Impact

Applies to every outline whose success criteria cite unchanged code as evidence
(regression-scoped work, test-only plans, refactors asserting a behavioural
invariant). The narrower the modification set, the larger the share of declared
paths that are read-intent, so the defect gets more likely as plans get more
surgical.
