envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:40:58Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=remediate-user-facing-sites

# Correct the documented --measured-diff-size form; the flag is scalar, not optional-valued

## Context

`automatic-review/SKILL.md` documents `--measured-diff-size` with an empty placeholder and states
as a general rule that every list flag on that surface is `nargs='?'`. Neither holds for this flag:
it is a scalar, so argparse rejects the documented empty form outright.

This is a documented invocation that fails on the common path — the worst kind of documentation
defect, because the reader has no reason to distrust it and the failure surfaces as an opaque
argparse exit 2 rather than as a doc error. The plan's own script-execution log records the matching
rejection against `review_completeness check` at 12:50 into the finalize phase.

The general assertion is the more dangerous half. A reader who believes "every list flag here is
`nargs='?'`" will construct empty forms for other flags too, and the rule is stated once and applied
many times.

## Root cause

The SKILL.md invocation block was written from the shape of the neighbouring `--required-bots` /
`--optional-bots` flags (which genuinely are `nargs='?'`) and generalised to a flag that is not one.
Nothing validates the documented forms against the live argparse surface for this script:
`manage-invocation-invalid` derives its accept-set from a `--help` walk, but the flag-level form is
not what it checks.

## Proposed action

Fix the documented `--measured-diff-size` form to require its value, and replace the blanket
"every list flag is `nargs='?'`" sentence with the per-flag truth. Then consider whether the
`--help`-walk validator can be extended to compare documented flag *forms* (value-required vs
optional-valued) against the parser, not just flag names — that is the check that would have caught
this at authoring time.

## Evidence

- aspect: script_failure_analysis — one `argparse_other` rejection against
  `plan-marshall:automatic-review:review_completeness check`, exit code 2, first seen
  `2026-09-08T11:50:00Z`, with the captured usage line showing
  `[--required-bots [REQUIRED_BOTS]] [--optional-bots [OPTIONAL_BOTS]]`.
- aspect: llm_to_script_opportunities — the documented-form defect sits on the finalize loop that
  consumed 59% of plan tokens.
