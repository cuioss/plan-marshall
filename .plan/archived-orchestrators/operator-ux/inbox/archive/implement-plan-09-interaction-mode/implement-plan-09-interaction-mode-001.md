envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:11:30Z

component=plan-marshall:manage-config
category=improvement

# Correct resolver-use documentation for interaction_mode get

Source: PR #1496 inline coderabbitai comment 62fbf5 on marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_interaction_mode.py:14 (fixed in-run by TASK-4).

Defect: docs claimed every read routes through `_config_core.resolve_interaction_mode`, but `cmd_interaction_mode_get` applies fallback and validation directly without calling it.

Rule: document required results, not a specific helper call; remove or revise claims that every read uses the resolver.

Fix applied in this plan: revised the resolver-use claim (TASK-4 follow-up commit on this branch).
