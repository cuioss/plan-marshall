envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:12:37Z

component=plan-marshall:manage-config
category=improvement

# Derive test parametrizations from VALID_INTERACTION_MODES

Source: PR #1502 review_body coderabbitai comment c17310 pointing at test/plan-marshall/manage-config/test_interaction_mode.py:48 (fixed in-run by TASK-9).

Defect: three parametrize lists hardcoded basic, advanced, expert while `_config_defaults.VALID_INTERACTION_MODES` is authoritative; a new mode could miss validator, resolver, and round-trip coverage.

Rule: keep the explicit contract assertion but derive behavioral cases from the authoritative tuple.

Fix applied in this plan: parametrizations derive from VALID tuple (TASK-9 follow-up commit on this branch).
