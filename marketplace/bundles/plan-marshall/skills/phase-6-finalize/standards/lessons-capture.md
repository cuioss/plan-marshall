# Lessons Capture

Record lessons learned from the implementation. Advisory only — does not block.

See also `standards/lessons-integration.md` for conceptual guidance on when and what to capture.

## Prerequisites

- Config field `6_lessons_capture` is `true`

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-lessons"
```

```
Skill: plan-marshall:manage-lessons
```

**Use exactly this command** to add a lesson (do not invent alternative flags):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{bundle}:{skill}" \
  --category {bug|improvement|anti-pattern} \
  --title "{concise summary}" \
  --detail "{detailed context and resolution}"
```

Required flags: `--component`, `--category`, `--title`, `--detail`. Do NOT use `--summary` (does not exist).
