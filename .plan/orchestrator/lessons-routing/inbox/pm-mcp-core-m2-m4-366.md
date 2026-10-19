envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:52Z

# Remap or flag task commit ids after the finalize sync-baseline rebase

- Source: plan-retrospective (request-result-alignment, llm-to-script-opportunities, functional-review self-report audit)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:phase-6-finalize
- Category: improvement
- Confidence: high

## Context

finalize-step-sync-baseline rebased the branch onto one upstream commit, which rewrote the task commits 2d688da and 9609b23 to f1aa8e3 and 1abc802. `work/coverage.md` and decision-log entry 604f3e still cite the old ids. Both functional-review rounds reported this as a false self-report (advisory), and nothing in finalize corrected it.

## Root cause

The rebase step rewrites SHAs but publishes no old-to-new mapping, so plan artifacts written in phase 5 that cite task commits go stale silently.

## Proposed action

Have finalize-step-sync-baseline emit an old->new SHA map (for example as step facts or a work artifact) whenever it rewrites commits, and either correct the citing plan artifacts or flag them, so later steps and reviews do not read pre-rebase ids as current.

## Evidence

- functional-review (both rounds): coverage file and decision log cite 2d688da / 9609b23, rewritten to f1aa8e3 / 1abc802
- status.json: finalize-step-sync-baseline "rebased onto origin/main, 1 upstream commit(s)"
- aspect: llm-to-script-opportunities -- post-rebase SHA map candidate
