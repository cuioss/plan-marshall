envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:23:55Z

# Pre-validate subcommand and flags against the executor SCRIPTS map before spawning

component: plan-marshall:tools-script-executor
category: improvement
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

PLAN-203 recorded **10 argparse rejections across 7 components** in a single plan, and an **11th fired
inside this retrospective itself** (`manage-solution-outline extract-deliverables` for the canonical
`list-deliverables`).

| Component | Wrong shape | Signature |
|---|---|---|
| `manage-references` | `list` | invented_subcommand |
| `manage-references` | `get` without `--field` | missing_required_flag |
| `git-workflow` | `push` | invented_subcommand |
| `git-workflow` | `switch-and-pull` without `--base` | missing_required_flag |
| `git-workflow` | `prune-local-and-remote-ref --branch X` | invented_flag |
| `github_pr` | `fetch_findings --enabled-bots …` | invented_flag |
| `manage-logging` | `read --level ERROR` | invented_flag |
| `tools-integration-ci:ci` | `pr … --plan-id X` | invented_flag |
| `review_completeness` | `check` missing required arg | argparse_other |
| `manage-solution-outline` | `extract-deliverables` | invented_subcommand |

`git-workflow` alone was mis-invoked four times. All four canonical recurrence signatures from
`agent-behavior-rules.md § Never invent script subcommands` fired at least once.

## Root cause

The countermeasure is prose in an always-loaded persona skill, plus an edit-time plugin-doctor rule
cluster. Neither operates at the call site. The failure is a *runtime* call-shape mismatch, and it is
fully decidable from data the executor already holds: `.plan/execute-script.py` embeds the
`SCRIPTS = { ... }` mapping, and each target script's argparse tree is enumerable.

That the eleventh instance occurred inside the retrospective that is auditing the other ten is the
clearest available evidence that more prose will not close this.

## Proposed action

Add a pre-spawn validation pass in `execute-script.py`:

1. Resolve `{notation}` against the embedded `SCRIPTS` map — unknown notation fails immediately.
2. Resolve the first positional against the target's declared subcommand `choices` — on miss, emit the
   valid-choices list and a nearest-match hint **without** spawning the subprocess.
3. Resolve declared flags for the chosen subcommand — reject unknown flags and missing required flags
   at the call site.

This converts 11 subprocess spawns plus 11 ERROR log lines into 11 immediate, well-shaped rejections,
and removes the class of silent `exit_code: 2` failures that bypass the script body entirely.

## Note on scope

`collect-fragments add` already implements exactly this shape for aspect keys — it rejects an
unregistered aspect with the full valid-key list rather than silently dropping the section. The
pattern is proven in-tree; this proposal generalizes it to the executor.

## Evidence

- fragment-script-failure-analysis.toon — 10 findings, 10 unique
- work.log 10:15:17 — the 11th rejection, inside this retrospective run
- `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § recurrence signatures
