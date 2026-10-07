envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:12:11Z

component=plan-marshall:phase-1-init
category=bug

# Apply interaction_mode at the phase-1 ambiguous-domain decision point

Source: PR #1502 inline coderabbitai comment e89969 on marketplace/bundles/plan-marshall/skills/manage-config/standards/interaction-mode.md:5 (fixed in-run by TASK-10).

Defect: phase-1-init invoked domain-detect without interaction_mode and opened AskUserQuestion whenever ambiguous; no phase or steward workflow consumed the persisted mode, so basic and expert behaviors were not implemented.

Rule: resolve interaction_mode before the ambiguous-domain branch and apply documented basic silent-union and expert fail-closed override demand without changing domain selection or build behavior.

Fix applied in this plan: phase-1-init Step 7 resolves mode before the branch (TASK-10 follow-up commit on this branch).
