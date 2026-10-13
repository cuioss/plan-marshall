envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:51Z

## Candidate lesson: shared count-pin test not listed in deliverable D1

Source: Q-Gate finding 14efda (phase 4-plan), resolved in-run. Sibling findings 7139d0 (D3) and 1e5fd5 (D5) have the same cause.
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Observation: WorkflowValidatorTest pins the number of verifier rules. Deliverable D1 adds a rule, which changes that count, but D1 did not list WorkflowValidatorTest. The task for D1 would not have been green on its own.

Suggested rule: when a deliverable changes a counted set (rules, checks, registry entries), find every test that pins that count and list it in the same deliverable, so each deliverable's tasks pass by themselves.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-003.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
