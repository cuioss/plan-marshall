envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T17:37:50Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-11-20
bundle=plan-marshall
title=Write link-check criteria as no new broken link against the base baseline

# Write link-check criteria as no new broken link against the base baseline

## Context

PLAN-V2-158 froze success criterion D4.C4 as the literal "BROKEN LINKS 0" for the doc-review trace check. The repository baseline on origin/main already had 3 broken links, in files the plan never touched (two in pm-mcp-core, one in the documentation repository). The functional-review author graded the criterion met on intent ("the branch adds no broken link"), and the verifier declined twice on the literal 0 (rounds 1 and 3). The round only closed by an operator decision in session. Separately, the check run from the nested plan worktree reported BROKEN LINKS 3090, because the sibling-relative links into ../plan-marshall-documentation do not resolve from .plan/local/worktrees/<plan>/. A conclusive count needed a manual run from the main checkout (fix task 14).

## Root cause

The outline copied an absolute count from the project's merge checklist into a frozen criterion, without checking the baseline. No criterion form expresses "adds no broken link compared with the base".

## Proposed action

When a success criterion cites a whole-repository check count (BROKEN LINKS, warnings, and the like), the outline should read the base's current value first. If it is not zero, the criterion should say "no new <X> compared with origin/main". The run location should also be stated whenever the check uses sibling-relative paths.

## Evidence

- aspect: chat_history_analysis — operator decision "Close as accepted" on D4.C4; verifier reasons "shows BROKEN LINKS 3, not the criterion's literal 0"
- status.metadata.functional_review_override_heads — two operator-override heads (749b0051, d5f1d6ac)
- aspect: llm_to_script_opportunities — branch-vs-baseline links comparison done by hand in fix task 14
