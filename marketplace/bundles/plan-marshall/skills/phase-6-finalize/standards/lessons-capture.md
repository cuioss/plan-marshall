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

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done
```
