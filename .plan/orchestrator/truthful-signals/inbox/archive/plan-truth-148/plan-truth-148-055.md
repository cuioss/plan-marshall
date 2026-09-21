envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:52Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-status:manage-status

- source_signal: script_failure cluster (1 of 9 distinct notations)
- notation: `plan-marshall:manage-status:manage-status`
- markers: four distinct `[ERROR] ... script_failure` lines across the run

## What happened

Four separate rejections of the same script, in three different shapes:

1. `metadata: error: argument --value: expected one argument` — a value was passed that argparse consumed as a flag boundary.
2. `Use --get for ... metadata — declared: ['append','field','get','plan-id','set','store','value']` — the read verb was invoked without its mode flag.
3. `Use a declared flag for ... read: ['plan-id','store']` — an undeclared flag was appended to `read`.
4. `exit_code=1 failure_kind=script_internal_failure` — a guarded phase-boundary transition refused because the worktree had 1 uncommitted change (this one is correct behaviour, not an invocation defect).

## Candidate rule

`manage-status metadata` is a mode-flagged verb: `--get` or `--set` is required and is not inferable from whether `--value` is present. Three of the four failures are the "invent a plausible flag set" signature. Quote flag names verbatim from `--help` or the executor mapping rather than extrapolating from surrounding workflow prose.
