envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:07Z

# Candidate lesson: a finalize review round after a fix commit costs 440K to 720K tokens, and three rounds put the plan at twice its budget anchor

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-004 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source: retrospective of the plan (aspects plan efficiency, log analysis, chat history). Figures read from the plan's metrics record and its hand-off rows.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.
Proposed component: `plan-marshall:phase-6-finalize`. Proposed category: improvement.

## Context

The plan is a multi-module feature (12 files, 4 deliverables, 8 tasks). Its recorded token total is 5,106,787, and that is a floor: the finalize phase was still open when it was read. The budget table of the retrospective gives a multi-module feature a warning at 1.5M and an error at 2.5M. Worked time was 1h51m, under the 120-minute warning, so the overrun is in tokens, not in time.

Finalize is the largest phase: 1,853,875 tokens over 11 hand-offs, 36% of the plan. Execute cost 1,707,354 over 6 hand-offs.

## Root cause

Every fix commit re-runs the whole review region, and each re-run is a fresh hand-off that reloads its workflow and skills. Three rounds ran:

- Round 1: create pull request 106K, Sonar 108K, automatic review 168K, triage 342K. About 723K.
- Round 2 (after the Sonar fix): Sonar 95K, automatic review 191K, triage 157K. About 443K.
- Round 3 (after the security fix): Sonar 91K, automatic review 164K, triage 199K. About 453K.

The Sonar hand-off of rounds 2 and 3 found nothing (0 issues, confirmed) and still cost 91K to 95K each. The triage of round 3 handled one informational status comment for 199K.

## Proposed action

Look at what a re-fired step needs when the previous round already settled most of it: a Sonar re-check that reads a confirmed zero, and a triage whose only input is a quality-gate status comment, are candidates for a script path without a hand-off. Whether the retrospective's token anchors, which were calibrated on other repositories, fit a Java multi-module project is a second question the pickup may want to separate from the first.

## Evidence

- aspect plan_efficiency: `total_tokens_per_deliverable=1276696.75`, `max_phase_token_share=0.36`, dominant phase `6-finalize=1853875`; anchor row multi_module + feature, error at 2.5M.
- aspect log_analysis: 11 finalize hand-off rows, 8 `step_complete` and 3 `returned_with_findings`; no spend on failed or retried hand-offs (`error_total_tokens: 0`, `retryable_total_tokens: 0`).
- aspect chat_history_analysis: two loop-backs from finalize to execute (TASK-007 Sonar, TASK-008 CodeRabbit security comment).

Not the same as message 009 (the security point declined then fixed) or 012 (the stale review bot): those describe why rounds happened, this one what a round costs.

Classification is left to the pickup.
