envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:54Z

# Keep rename sources in the realized footprint

Component: `plan-marshall:manage-references` · Category: bug · Source: plan-retrospective of `static-verifier-rule-gaps-completion`

## Context

PLAN-54 deleted `subworkflow-stepped-out-spurious.pmwf` (D1, declared `(delete)`) and replaced `step-completion-missing.pmwf` (D3/D6). The squash commit 36a0bcd shows both as git renames (`subworkflow-stepped-out-spurious.pmwf => stepped-out-target.pmwf`, `step-completion-missing.pmwf => step-completion-no-completion.pmwf`). `references.realized_footprint` (95 paths) lists only the destination of each rename, so both removed files are missing from it. Plain deletions (`config-unreachable.pmwf`, `cycle-no-awaited-event.pmwf`) are present.

## Root cause

The footprint capture takes rename destinations only. A source path that the plan really removed disappears from the footprint whenever git's similarity check pairs it with a new file.

## Proposed action

Record both sides of a rename in `capture-footprint` / `compute-footprint`, for example with `--no-renames` or by adding the source of each `R` entry. Then make the retrospective consumers (outline-vs-shipped `include_unrealised`, artifact-consistency `outline_only`, manifest rule M6) count a declared `(delete)` path as realized when it is a rename source.

## Evidence

- aspect: outline-vs-shipped — include_unrealised 5 of 49; 2 of the 5 are these rename sources
- aspect: artifact-consistency / manifest-decisions — the same 2 paths in outline_only, so M6 fails as declared_vs_realized_set_mismatch
- `git show --stat -M 36a0bcd` shows 5 renames under `verify/refused/`; all 5 sources are absent from `realized_footprint`

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-009.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
