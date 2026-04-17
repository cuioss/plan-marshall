# Archive Plan

Archive the completed plan to `.plan/archived-plans/`.

**CRITICAL**: Archive MUST be the last step in the pipeline because it moves plan files (including status.json), which breaks `manage-status transition` and other manage-* scripts. All plan operations must complete before archive.

Lesson-sourced plans carry their `lesson-{id}.md` file along when the plan directory is archived — no separate mark-applied step is needed.

## Mark Step Complete

Record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST happen BEFORE the archive call below, because archive moves `status.json` out of `.plan/plans/{plan_id}/` and any subsequent `mark-step-done` call would fail to locate the plan.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the archive destination. `{archive_path}` is the canonical archive location `.plan/archived-plans/{date}-{plan_id}` (the same path `manage-status archive` will move the plan directory to in the next call):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step archive-plan --outcome done \
  --display-detail "-> {archive_path}"
```

## Archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status archive \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"
```
