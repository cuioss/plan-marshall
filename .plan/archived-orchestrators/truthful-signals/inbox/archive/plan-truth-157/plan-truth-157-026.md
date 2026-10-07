envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:23Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# Derive each detector's population independently, and make the non-vacuity guard fire PER MEMBER, not only on total emptiness

CodeRabbit on PR #1494: `spec_body` was filtered from `drafting`, which was itself
filtered from `derived` by `_DRAFTING_DECLARATION_RE`. So a document reached the
monotonic-resource assertion only if the drafting-declaration regex matched it
first. If one verb doc phrases its drafting admission outside that regex's three
alternations, the doc drops out of `drafting` and therefore out of `spec_body` — and
it can then declare a `spec_drafts` return field with NO monotonic-resource
constraint while
`test_every_spec_body_draft_carries_the_monotonic_resource_constraint` still passes.

The second half is the sharper one: the non-vacuity guard only fired when BOTH docs
dropped out, so the single-doc case was silent. A guard that trips on an EMPTY
population cannot see a population that merely shrank.

`_SPEC_BODY_DRAFT_RE` keys on the declared return field, which is independent of the
drafting-declaration phrasing — so the two detectors could be made independent at no
cost.

Source record: pr-comment finding `f2f5fe`, PR #1494, bot `coderabbit`, inline at
`test_orchestrator_dispatch_workflow_pin.py:471`, resolution `fixed` (remediated
in-run by TASK-007).

## Solution

- Filter `spec_body` from `derived` rather than from `drafting`, so the two detectors
  stay independent. Chained population filters couple unrelated detectors: a phrasing
  change to one regex silently narrows the other's coverage.
- Make the non-vacuity assertion population-derived and PER MEMBER — assert the
  expected member count, or assert each expected document is present, not merely that
  the set is non-empty.
- Correct the evidence wording so it names `spec_body` as a subset of the DERIVED
  surface rather than of the drafting set: an `_evidence` string that misnames its own
  population is a false report of what was measured.

## Impact

This restates a standing rule in a sharper form: every set-guarding detector must be
population-derived AND must publish its population size, because a check that returns
0 from a SHRUNKEN population is indistinguishable from one that returns 0 from a
complete population.
