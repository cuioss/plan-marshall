envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:11:47Z

component=pm-plugin-development:plugin-doctor
category=bug

# Break flag loop when refreshed analyzer scope is unknown

Source: PR #1496 inline coderabbitai comment 453c3f on marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_argument_naming.py:1044 (fixed in-run by TASK-6).

Defect: when `_refresh_entry` returned unknown root or subcommand scope, `continue` skipped only the current flag while `allowed` still held the stale set; since `refreshed` blocks a second refresh, a later flag could false-positive from the stale set.

Rule: break the current invocation flag loop when either refreshed scope is unknown; independent invocations continue.

Fix applied in this plan: continue-to-break correction (TASK-6 follow-up commit on this branch).
