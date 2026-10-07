envelope_version=1
sender_type=plan
sender_id=implement-plan-08-slug-semantics-model-compliance
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-14T08:10:57Z

# Script-invocation rejections recovered in-run (7 findings)

## Context

The run's script-execution log carries 8 non-zero-exit calls across 7 distinct
failure signatures: two invented-flag drifts (architecture search, ci checks
router-flag position), three argparse-other rejections (manage-files list,
build_server submit, review_completeness check), one missing required flag
(ci pr prepare-comment), and one internal error (a collect-fragments add with a
doubled plan-dir-relative path, caller-side, recovered immediately). Every one
was corrected in-run; none blocked the pipeline.

## Root cause

Caller-side invocation drift against argparse surfaces, not script defects — each
rejection named the correct form in its own usage text.

## Proposed action

No fix proposed at plan level; recorded as the invocation-friction class for the
orchestrator to weigh against the existing never-invent-subcommands coverage.

## Evidence

- plan-retrospective fragment script-failure-analysis: total_failures 8, unique_failures 7, all recovered
