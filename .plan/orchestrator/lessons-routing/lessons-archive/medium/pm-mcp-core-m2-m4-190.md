envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:50Z

## Candidate lesson: outline deliverable omitted the test file of a new class

Source: Q-Gate finding fe9f2e (phase 3-outline), resolved in-run.
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Observation: deliverable 3 of the solution outline introduced the class QuestionClass but did not list its test file among the affected files. The Q-Gate caught the gap and the outline was corrected before planning.

Suggested rule: when a deliverable adds a production class, the outline lists the matching test file in the same deliverable's affected files.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-001.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
