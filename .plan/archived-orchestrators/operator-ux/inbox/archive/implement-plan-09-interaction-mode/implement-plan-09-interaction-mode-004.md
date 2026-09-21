envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:11:54Z

component=plan-marshall:manage-config
category=improvement

# Derive displayed mode list from VALID_INTERACTION_MODES

Source: PR #1502 inline coderabbitai comment e68303 on marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py:633 (fixed in-run by TASK-7).

Defect: help text hardcoded the mode list while validation and persistence derive from `_config_defaults.VALID_INTERACTION_MODES`; a future mode could validate yet advertise an obsolete contract.

Rule: treat a hardcoded list mirroring a set defined elsewhere as a defect unless derived at build or run time; import the authoritative tuple and format the display from it.

Fix applied in this plan: help derives from VALID modes (TASK-7 follow-up commit on this branch).
