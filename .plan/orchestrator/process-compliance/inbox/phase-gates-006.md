envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:13:20Z

component=plan-marshall:tools-script-executor
category=anti-pattern
created=2026-09-19
bundle=plan-marshall

# Callers guessing manage-* verbs and flag placement produce argparse rejections

Across the phase-gates run, six distinct script notations failed with exit_code=2 argparse rejections because callers invented verbs, omitted required flags, or misplaced scoped flags — the exact class the persona hard rule ("Never invent script subcommands") guards against:

- `manage-architecture:architecture`: `unrecognized arguments: --plan-id phase-gates` (top-level flag placement error)
- `manage-status:manage-status`: `show` is not a registered verb
- `manage-execution-manifest:manage-execution-manifest compose`: missing required flags `plan-change-type`, `scope-estimate`
- `manage-references:manage-references compute-footprint`: missing required flag `worktree-path`
- `manage-findings` (missing `--plan-id`) and `tools-integration-ci` (flag placement) and `manage-plan-documents list` (guessed verb surface) per the run's failure markers

## Solution

Quote subcommand and flag names verbatim from `--help` or the executor mapping; run `<script> <verb> --help` before first use of an unfamiliar surface; route on the TOON `error: invalid_invocation` / `argparse_rejection` payload instead of retrying paraphrases.

## Impact

Every guessed invocation burns a dispatch cycle and corrupts downstream behaviour when the exit code is ignored. The `ARGUMENT_NAMING_*` plugin-doctor rules are the edit-time guard; the runtime guard is `--help`-first.

## Evidence

- plan phase-gates work-log `[ERROR] script_failure ... failure_kind=argparse_rejection` lines and script-log `exit_code: 2` entries, 2026-09-19
- signal signal_script_failure_clusters_count=6, epic process-compliance
