envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:57:44Z

component=plan-marshall:manage-solution-outline
category=anti-pattern

# One script absorbed nine argparse rejections across five phase re-entries

Source: script-failure cluster, notation
plan-marshall:manage-solution-outline:manage-solution-outline (exit_code=2,
failure_kind=argparse_rejection). The largest cluster of the run.

Three distinct wrong shapes, each repeated after the phase re-entered:

- `extract-deliverables` — an invented verb. Registered:
  exists, get-deliverable, get-field, get-module-context, list-deliverables, read,
  resolve-path, update, validate, write. (5 occurrences)
- `get-deliverable --number N` — canonical flag is `--deliverable-number`.
  (3 occurrences)
- `read` with an undeclared flag — declared: deliverable-number, plan-id, raw, section.
  (1 occurrence)

## Solution

The repetition across re-entries is the signal that matters. The same two wrong shapes
were re-issued at 12:50, 13:34, 14:16, 17:24, 19:05, 20:00 and 21:37 — a phase leaf that
re-enters does not carry forward the correction it already learned, so a paraphrased verb
costs one rejection per envelope rather than one per run.

Two candidate remedies for the epic: make the rejection message's canonical form
prominent enough to be copied (the executor already emits "Use `... list-deliverables`"
and "Use `--deliverable-number`"), and treat a repeated identical rejection ACROSS
envelopes as a documentation defect in whatever workflow text the leaf is reading, not as
an agent slip.

## Impact

Nine wasted round-trips, each exiting before the script body ran.
