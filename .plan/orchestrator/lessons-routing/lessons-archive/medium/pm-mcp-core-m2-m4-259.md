envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:30Z

# Candidate lesson: Attribute quality-gate rewrites and operator-approved widening in scope-creep check

**Component (suggested):** plan-marshall:phase-5-execute
**Category (suggested):** improvement

## Context

In plan-17-project-units-and-invariants the execute-phase scope-creep check filed a `scope_creep_warning`
for 24 files, and on a later loop-back for 31 files ("residual 31 > threshold 5"). The retrospective's
declared-vs-realized comparison counts 37 realized-but-undeclared paths. Nearly all of them came from two
sources the plan knew about: the pre-commit quality gate re-sorting imports in about 25 pm-workflow files
(committed as CLAUDE.md requires), and the operator's execute-time decision to record exact declare/decide
lines, which widened the change into the AST, parser and their tests.

## Root cause

Neither the quality-gate rewrite set nor an operator-approved scope decision is written back into the
plan's declared footprint (references affected_files). So the check re-reports the same accepted files on
every later pass, and the operator has to be asked again.

## Proposed action

Record files rewritten by the quality gate as gate-attributed, and let an operator scope decision append
its files to the declared footprint with that decision as provenance. The scope-creep check would then
report only the unattributed remainder.

## Evidence

- aspect: manifest_decisions: rule M6 `declared_vs_realized_set` fail, 16 outline_only / 37 references_only
- aspect: request_result_alignment: scope creep is the AST decision plus import re-sorts, accepted by the operator
- aspect: chat_history_analysis: scope_creep_warning 24 files (round 0), then 31 files (round 1 re-entry); operator answered "Accept, list in PR"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-008.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
