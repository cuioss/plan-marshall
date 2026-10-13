envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:52Z

## Candidate lesson: scope-creep warning on new test fixtures (accepted)

Source: Q-Gate finding 267714 (phase 5-execute), a scope-creep warning, accepted in-run.
Plan: static-verifier-rule-gaps-completion (PR #48, merged as 36a0bcd).

Observation: the execute-phase Q-Gate warned about scope creep because test fixture files were changed that the plan had not named one by one. On review the fixtures sat inside the expected surface of the plan, so the warning was accepted and nothing was changed.

Possible follow-ups (for the orchestrator to judge):
- Name fixture directories in a plan's expected surface so new fixtures under them do not raise the warning.
- Or let the scope-creep check treat files under a declared test-fixture directory as inside the surface.

Classification deferred to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-006.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
