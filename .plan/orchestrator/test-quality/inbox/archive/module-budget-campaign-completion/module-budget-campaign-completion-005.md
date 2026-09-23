envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=candidate-lesson
created=2026-09-23T14:46:27Z

component=plan-marshall:manage-status
category=anti-pattern
title=Scope sensor bands glob fan-out as multi-module even for single-module test carve
plan_id=module-budget-campaign-completion
source_aspects=qgate-scope-estimate
confidence=high

# Scope sensor bands glob fan-out as multi-module even for single-module test carve

## Context

2-refine filed one anti-pattern Q-Gate finding (60416e): references.scope_estimate persisted as surgical while the request body carried a glob/pattern fan-out marker alongside only 4 explicit file paths. The sensor bands any pattern as unbounded multi-module, warning the narrow band suppresses S3/S4 escalation and projects minimal posture. Resolution accepted with execution verification.

## Root cause

The glob fan-out marker belonged to the epic-level campaign corpus (test-quality module-budget sweep over 427 over-budget modules), not this emission's scope. The plan shipped exactly one single-module carve: test_shared_harness.py split into collection units plus 5 split units plus 1 consequential conftest-loader reference update, merged as PR #1593. Scope_estimate=surgical verified correct in practice.

## Proposed action

Scope the fan-out sensor to the emission's affected-file set rather than the request narrative's campaign-corpus mentions, or record a campaign-vs-emission scope distinction at 2-refine so epic-level glob context does not flag a surgical emission.

## Evidence

- finding 60416e (2-refine, qgate, anti-pattern, resolution accepted 2026-09-23T07:18:47Z): scope_estimate=surgical vs glob fan-out marker with 4 explicit paths
- execution: single-module carve landed, PR #1593 merged via queue, module-tests green
- signal: signal_qgate_pending_count=1, resolved-in-run
