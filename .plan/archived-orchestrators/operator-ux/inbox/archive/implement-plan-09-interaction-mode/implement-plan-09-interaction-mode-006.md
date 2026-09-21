envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:12:19Z

component=plan-marshall:marshall-steward
category=improvement

# Make steward menu option count target-specific

Source: PR #1502 inline coderabbitai comment 78127d on marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md:31 (fixed in-run by TASK-8).

Defect: Configuration submenu stated 15 options, but the target guard omits Terminal Title and Enforcement Hook on non-Claude targets, leaving 13.

Rule: state counts as up-to-15 (13 on non-Claude targets) wherever the AskUserQuestion 4-option cap pagination is described.

Fix applied in this plan: target-specific count wording (TASK-8 follow-up commit on this branch).
