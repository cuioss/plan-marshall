envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:30Z

component=plan-marshall:manage-architecture
category=anti-pattern
bundle=plan-marshall

# Script-failure cluster 4 of 4: architecture --plan-id placed AFTER the subcommand

During the review-retrospective step, `architecture` was called with `--plan-id
plan-truth-157` positioned after the subcommand. Argparse rejected it as
`unrecognized arguments: --plan-id plan-truth-157` — a message that reads as "this flag
does not exist" while the flag is right there in the wrong place — and the script's own
note stated the fix: "`--plan-id` is a top-level flag and belongs BEFORE the
subcommand".

The usage line confirms it: `architecture.py [-h] [--project-dir PROJECT_DIR]
[--plan-id PLAN_ID] {discover,init,derived,...}`. Both `--project-dir` and `--plan-id`
are top-level router flags on this script.

Source record: work-log `[ERROR]` entry `6bb377` at 2026-09-14T20:29:44Z, marker class
`script_failure`.

## Solution

On `manage-architecture:architecture`, `--plan-id` and `--project-dir` are TOP-LEVEL
and precede the subcommand. Note the trap that makes this worth a record: the
`resolve` verb declares its own `--audit-plan-id` AFTER the verb, so the same script
carries a plan-identifying flag in BOTH positions under two different names. Reading
"architecture takes a plan id" without reading WHICH flag and WHERE produces exactly
this rejection.

Verify the position against the ROUTER's own declaration, not against a sibling
script's convention.

## Impact

One of four `argparse_rejection` clusters in this run, and the counterpart of the
`ci pr prepare-body` cluster: there the flag had to move AFTER the verb, here BEFORE
it. The two together are the concrete demonstration that flag position is a
per-SURFACE property, so a habit formed on one script mis-fires on the next. The
positive note is that this script's rejection message named the fix explicitly —
that is the diagnostic quality the other three surfaces should match.
