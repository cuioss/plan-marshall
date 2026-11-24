envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:42Z

component=plan-marshall:tools-script-executor
category=anti-pattern
title=script calls rejected before the script body: a flag or verb invented from a neighbouring script, a misplaced --plan-id, or an underscore notation
source_lesson=2026-11-24-07-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# script calls rejected before the script body: a flag or verb invented from a neighbouring script, a misplaced --plan-id, or an underscore notation

Four more members of the invented-invocation family (compare 2026-11-23-14-007 manage-findings, 2026-11-18-07-002 qgate query, 2026-11-19-06-001 --number). Each failed with exit 1 or 2 before the script ran; each was cured by the verb's own `--help` or the canonical-invocation block.

- `architecture.py --plan-id P search ...` (plan-11, 2026-11-23T20:09:41Z, phase 5-execute): `--plan-id` was placed before the verb as a router-level flag; `architecture` does not take it there (argparse_rejection, exit 2). The flag belongs to the verb, not to the router.
- `manage-tasks read --task-number 5 --field depends_on` (plan-20, 2026-11-23T17:51:21Z and 17:51:26Z): declared flags are `plan-id` and `task-number`; `read` has no field selector, read `depends_on` from the returned TOON.
- `manage-status mark-step-done --worktree-path ...` (plan-20, 2026-11-24T06:40:03Z): not declared; the call is `mark-step-done --plan-id P --phase 6-finalize --step S --outcome O [--force] [--display-detail D]`, because under the cwd-pinned model the worktree path is never forwarded to manage-status.
- `plan-marshall:manage-status:manage_status` (plan-20, 2026-11-23T19:48:09Z, twice, exit 1): the Python module-style name was written in place of the script name; the executor rejects it before any argparse runs ("The third part appears to be a subcommand, not a script name"), so it shows up as neither argparse_rejection nor argparse_other. The notation is `plan-marshall:manage-status:manage-status`.

## Candidate rule

Before a call to a script the caller has not used in this session, read its canonical-invocation block or `--help`; do not carry a flag over from the neighbouring script or the router convention. Either the executor accepts the underscore form as an alias of the hyphenated script name, or the persona's "never invent script subcommands" signatures add the underscore notation as its own case.

Source: inbox plan-11-store-anchoring-signed-007 (first bullet) and plan-20-leftover-fixes-2-009, -011, -018.
