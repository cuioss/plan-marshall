envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:45:04Z

component=plan-marshall:tools-script-executor
category=anti-pattern
title=14 unique argparse rejections in one run - the edit-time naming guard never observes runtime invocation

# The `ARGUMENT_NAMING` guard checks authoring; the failures happen at call time

## Observation

`script-failure-analysis` over `PLAN-CIS-028`: **20 non-zero-exit script calls, 14 unique
signatures**, all in a run whose own domain is plan-marshall skills.

| subtype | count |
|---------|------:|
| `invented_flag` | 7 |
| `missing_required_flag` | 4 |
| `invented_subcommand` | 2 |
| `script_internal_error` | 1 |

Representative:

- `manage-solution-outline get-deliverable` without `--deliverable-number` — **5 times**
- `manage-references list-add` — verb does not exist (canonical: `add-list`), then
  `add-list` without `--values` on the retry
- `manage-files read --tail 25` / `--tail 40` — flag does not exist, twice
- `manage-findings list --format json` — flag does not exist
- `manage-status metadata --field …` issued at top level, then without `--field`
- `ci --pr-number 1080` at top level (the flag is verb-scoped)
- `build_server preflight --plan-id …` — flag does not exist
- `build-server-client:build_server_client` — 3-part notation with a subcommand in the
  script slot

**This retrospective reproduced the class once more** while writing this message
(`manage-findings qgate list --fields …`), which is the cleanest possible evidence that the
recurrence is not corrected.

## Why the existing guard does not catch it

The `ARGUMENT_NAMING_*` plugin-doctor rule cluster is a **documentation-authoring** guard:
it runs under `quality-gate` over skill source and catches drift between a doc's stated
invocation and the script's declared argparse surface. It is structurally incapable of
observing a call the model composes at runtime from surrounding workflow prose, which is
where all 14 of these originated.

The four canonical recurrence signatures are already written down in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md`. All 14 failures here match
one of them. Documentation of the failure mode is at saturation; the failure rate is not
moving.

## Rule

- **Put the check where the call happens.** `.plan/execute-script.py` already embeds the
  full `SCRIPTS` mapping. A pre-spawn validation shim can reject an unknown
  subcommand/flag *before* the subprocess starts and return the canonical form in a
  structured TOON error — turning a silent `exit_code: 2` that bypasses the script body
  into a corrective the caller can act on in one hop.
- **The current failure is silent-by-shape**: `exit_code: 2` from argparse means the script
  body never ran, so any workflow that does not read the exit code proceeds as if the call
  succeeded. That is the same class as the unchecked-persist family the epics already
  track — a call whose failure is invisible at the call site.
- Prioritise by observed frequency, not by plausibility: `manage-solution-outline
  get-deliverable` alone accounted for 5 of 20 failures, which is a single missing required
  flag repeated. A shim that answers *"you omitted `--deliverable-number`"* removes a
  quarter of the run's script failures.

## Impact

`plan-marshall:tools-script-executor` (the generated executor), the
`ARGUMENT_NAMING_*` plugin-doctor cluster's scope boundary, and every workflow that issues
`manage-*` calls composed from prose.
