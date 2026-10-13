envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:52Z

## Candidate lesson: shared count-pin test not listed in deliverable D5

Source: Q-Gate finding 1e5fd5 (phase 4-plan), resolved in-run. Same cause as 14efda (D1) and 7139d0 (D3).
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Observation: deliverable D5 changes the verifier rule set, which WorkflowValidatorTest pins by count, but D5 did not list that test. Its tasks would not have been green on their own.

Note: the same miss happened three times in one plan (D1, D3, D5). This points to a planning check rather than a one-off mistake: a shared count-pin test is touched by every deliverable that changes the counted set.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-005.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
