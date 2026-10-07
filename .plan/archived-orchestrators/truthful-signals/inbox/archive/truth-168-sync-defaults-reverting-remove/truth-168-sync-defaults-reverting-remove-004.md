envelope_version=1
sender_type=plan
sender_id=truth-168-sync-defaults-reverting-remove
epic=truthful-signals
kind=candidate-lesson
created=2026-10-02T15:45:42Z

component=plan-marshall:tools-script-executor
category=anti-pattern
created=2026-10-02

# Never invent manage-* subcommands or flags: quote the argparse declaration verbatim

Five distinct script notations failed in-run with `argparse_rejection` (exit 2) because callers extrapolated plausible-sounding verbs or flags from workflow prose instead of the script's declared parser: `manage-solution-outline read --deliverable` (undeclared flag), `manage-references compute-footprint` without required `--worktree-path`, `manage-status show` (unregistered verb), `check-artifact-consistency run --fragment-file` (undeclared flag), and `orchestrator inbox detect` without required `--source-id`. Each bypassed the script body and corrupted downstream behavior.

## Solution

Quote subcommand and flag names verbatim from the executor mappings or the script's `--help` output. When in doubt, invoke the script with `--help` first. Never extrapolate verbs (`show`, `read-context`) or flags (`--deliverable`, `--fragment-file`, `--id` for `--lesson-id`) from narrative. For `ci` router verbs, place `--plan-id` before the verb only where that script's parser declares it as a top-level flag; never append by rote.

## Impact

Every `python3 .plan/execute-script.py` call. Prevents silent exit-2 failures that bypass script bodies and poison downstream steps.
