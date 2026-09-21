envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:11:40Z

component=plan-marshall:manage-config
category=bug

# Reject non-object marshal.json roots before field access

Source: PR #1496 inline coderabbitai comment d22dbd on marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_interaction_mode.py:57 (fixed in-run by TASK-5).

Defect: `load_config()` returned any valid JSON root; a list or scalar root made `cmd_interaction_mode_get` raise TypeError at `config[field]` and `cmd_interaction_mode_set` raise TypeError at assignment, surfacing as internal_error exit 1 instead of a structured configuration error.

Rule: validate config is a dict after loading, or enforce the invariant in `_config_core.load_config`.

Fix applied in this plan: dict-root validation (TASK-5 follow-up commit on this branch).
