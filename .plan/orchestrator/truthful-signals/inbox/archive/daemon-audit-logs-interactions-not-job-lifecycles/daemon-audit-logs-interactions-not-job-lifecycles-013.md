envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:32Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
bundle=plan-marshall

# Four argparse rejections in one run, all matching already-documented recurrence signatures

## What was observed

`script-failure-analysis` found 6 non-zero-exit script calls in this run. Four are
argparse rejections, and every one of them matches a signature already written down in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md`
§ "Never invent script subcommands — recurrence signatures":

| When | Call | Signature |
|------|------|-----------|
| 12:34:52 | `manage-solution-outline get-module-context` | argparse_other |
| 13:16:49 | `manage-findings qgate list --plan-id X` (no `--phase`) | signature 4 — missing required `--phase`, verbatim in the standard |
| 13:55:43 | `manage-findings qgate add` with a wrong flag set | signature 4 |
| 15:09:33 | `git-workflow push` | signature 1 — verb-paraphrase; `push` is not in `choices` |
| 15:26:35 | `ci pr ... --plan-id X` | signature 3-adjacent — top-level flag where none is declared |

The `git-workflow push` rejection is the clearest: the executor's error message lists all
15 valid subcommands, none of which is `push`. The step's name is `default:push`, and the
verb was synthesised from the step's name rather than quoted from the argparse surface —
which is precisely the verb-paraphrase mechanism the standard names.

## Why it matters

None of these failed the plan. Each was retried and the step completed, so the run's
terminal signals are all green and the failures survive only in
`logs/script-execution.log`. That is the pattern worth flagging: a documented anti-pattern
recurring four times in one run without producing a single visible symptom is a rule that
is being read but not applied at the call site.

The rule text is not the problem — it is precise, it names these exact signatures, and it
was in context. The gap is that nothing checks a call against the signatures *at the
moment of issuing it*.

## Proposed action

The write-side guard (`ARGUMENT_NAMING_*` plugin-doctor rules) already exists for
authoring. What is missing is a read-side signal: `script-failure-analysis` classifies
these correctly *after the fact* and its findings currently terminate in a retrospective
report nobody gates on.

Concrete, minimal proposal: make an argparse-rejection count > 0 in phases 5-6 a
`warning`-severity item on the finalize output template, so the operator sees "4 script
calls were rejected and retried" alongside the green step list. The classification work is
already done and free — only the surfacing is missing.

## Evidence

- `work/fragment-script-failure-analysis.toon` (this run) — 6 findings, 4 argparse
- `logs/work.log:242` (git-workflow push), `:257` (ci --plan-id)
- `logs/script-execution.log` 12:34:52, 13:16:49, 13:55:43
- `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § recurrence signatures 1, 3, 4
