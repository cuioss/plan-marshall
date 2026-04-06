# Archive Plan

Archive the completed plan to `.plan/archived-plans/`.

**CRITICAL**: Archive MUST be the last step in the pipeline because it moves plan files (including status.json), which breaks `manage-status transition` and other manage-* scripts. All plan operations must complete before archive.

## Mark Lesson Applied (conditional)

**IMPORTANT**: Mark lesson applied BEFORE archive, because archive moves plan files and makes `request read` fail.

Read the request source:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section source
```

**IF `source == "lesson"`**: Read `source_id` and mark applied:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section source_id
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --id {source_id} --applied true
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Lesson {source_id} marked as applied"
```

Archive the lesson file so it no longer remains in `.plan/lessons-learned/`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons archive \
  --id {source_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Lesson {source_id} archived"
```

**ELSE**: Skip — plan did not originate from a lesson.

## Archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status archive \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"
```
