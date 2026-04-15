# Archive Plan

Archive the completed plan to `.plan/archived-plans/`.

**CRITICAL**: Archive MUST be the last step in the pipeline because it moves plan files (including status.json), which breaks `manage-status transition` and other manage-* scripts. All plan operations must complete before archive.

Lesson-sourced plans carry their `lesson-{id}.md` file along when the plan directory is archived — no separate mark-applied step is needed.

## Archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status archive \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"
```
