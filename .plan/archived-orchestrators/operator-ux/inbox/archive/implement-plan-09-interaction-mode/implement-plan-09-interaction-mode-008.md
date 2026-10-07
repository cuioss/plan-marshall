envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:12:45Z

component=plan-marshall:phase-1-init
category=bug

# Project candidates to domain keys before the basic-mode union

Source: PR #1502 inline coderabbitai comment 757af6 on marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md:781 (fixed in-run by TASK-11).

Defect: basic branch unioned candidate objects carrying domain plus matched_aliases directly, then passed them to set-list which splits text without domain-key validation, persisting object serializations as invalid domain entries.

Rule: union each candidates entry's domain field with additional_candidates, always_on, and glob_matched before the silent projection.

Fix applied in this plan: domain-field projection wording (TASK-11 follow-up commit on this branch).
