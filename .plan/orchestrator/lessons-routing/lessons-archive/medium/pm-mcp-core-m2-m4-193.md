envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:51Z

## Candidate lesson: shared count-pin test not listed in deliverable D3

Source: Q-Gate finding 7139d0 (phase 4-plan), resolved in-run. Same cause as 14efda (D1) and 1e5fd5 (D5).
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Observation: deliverable D3 changes the verifier rule set, which WorkflowValidatorTest pins by count, but D3 did not list that test. Its tasks would not have been green on their own.

Suggested rule: same as the D1 finding. A deliverable that changes a counted set lists every test that pins the count.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-004.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
