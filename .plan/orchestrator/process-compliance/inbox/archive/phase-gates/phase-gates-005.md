envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:13:14Z

component=plan-marshall:manage-status
category=bug
created=2026-09-19
bundle=plan-marshall

# Phase-transition artifact gate must require regular files, not mere existence

CodeRabbit finding 878984 (PR #1540, inline on `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:243`, bot_kind coderabbit, resolution fixed) showed `_has_plan_artifact` accepted directories as artifacts: `Path.glob('TASK-*.json')` matches directories and `Path.exists()` is true for directories, so a `tasks/TASK-001.json/` directory or an `execution.toon/` directory satisfied the gate and `cmd_transition` advanced the plan to `5-execute` without the required file.

## Solution

Fixed via TASK-6 (commit b72e26f4c) following the bot's proposed diff: filter task matches with `is_file()` and check `execution.toon` with `is_file()`, plus directory regression cases.

## Impact

Any phase gate that checks for artifact presence with `glob()` + `exists()` is vulnerable to the same directory-masquerade bypass. Prefer `is_file()` at every existence check that guards a transition.

## Evidence

- finding hash_id 878984, type pr-comment, path marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:243, reviewed_commit 1c39da2d988bdde150e1c764530cfbf6b5436c85
- plan phase-gates, PR #1540, epic process-compliance
