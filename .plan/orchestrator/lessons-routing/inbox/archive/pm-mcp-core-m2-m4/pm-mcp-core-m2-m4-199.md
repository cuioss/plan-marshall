envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:54Z

# Give qgate a cross-phase pending listing

Component: `plan-marshall:manage-findings` · Category: improvement · Source: plan-retrospective of `static-verifier-rule-gaps-completion`

## Context

Two argparse rejections in one plan, both on `manage-findings qgate`. At 20:45:55Z the phase-3-outline re-entry called `qgate query`, which is not a verb (`add, clear, list, resolve, resolve-by-rule, resolve-evidenced`). At 08:21:21Z lessons-capture called `qgate list` without `--phase`, and the parser rejected it because `--phase` is required. Both callers wanted the same thing: every pending Q-Gate finding of the plan, across phases.

## Root cause

`qgate list` scopes to exactly one phase and has no plan-wide form. Callers that need the union across phases make up a verb or leave out the flag.

## Proposed action

Make `--phase` optional on `qgate list`, so that leaving it out lists every phase with a `phase` column. Or add an explicit `--all-phases`. Name the cross-phase form in the canonical-invocation block so callers stop paraphrasing it.

## Evidence

- aspect: script-failure-analysis — argparse_other on manage-findings qgate, 2 occurrences
- work.log 20:45:55Z: "`query` is not a registered verb for ... qgate"
- work.log 08:21:21Z: "Add the required flag(s) to ... qgate list: ['phase']"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-010.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
