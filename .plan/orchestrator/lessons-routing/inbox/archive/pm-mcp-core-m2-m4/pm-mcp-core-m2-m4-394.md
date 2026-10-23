envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:30Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# Drop the undeclared --audit-plan-id from the outline Step 9a call

## Context

Step 9a of the outline workflow documents the domain-skill resolve as:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain {domain_1} --domain {domain_2} --audit-plan-id {plan_id}
```

`resolve-outline-skill` declares no `--plan-id` and no `--audit-plan-id`; its only flag is the repeatable `--domain`. The live canonical block in `manage-config` shows the bare form, and `extension-api/standards/ext-point-outline.md` shows the same bare form at both of its call sites. The documented invocation therefore cannot run.

In this run the call was made three times (06:53:45Z and 07:04:40Z in 3-outline, 07:40:57Z in 4-plan) and was rejected each time with exit 2. The caller used `--plan-id` rather than the documented `--audit-plan-id`, so both the document and the call were wrong in different ways — but the document is what a careful reader follows, and it leads to the same rejection.

## Root cause

The Step 9a call was written when the verb accepted a plan id, or was copied from a sibling verb that does. The canonical block and the extension-point doc were updated; the workflow step was not. Nothing binds the three sites, so the drift is invisible until a run hits it.

## Proposed action

Replace the Step 9a invocation with the bare `resolve-outline-skill --domain {domain} ...` form and add a one-line note that the verb takes no plan flag. Better, have the doc cite `manage-config` Canonical invocations → `resolve-outline-skill` instead of restating the command, so the next flag change cannot leave a second copy behind.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:manage-config:manage-config resolve-outline-skill` exit 2, `occurrence_count: 3`, stderr lists the accepted verbs and rejects the extra argument.
- logs/script-execution.log lines 261-264, 279-282 (args `resolve-outline-skill --plan-id ... --domain ...`).
- `phase-3-outline/standards/outline-workflow-detail.md` Step 9a vs `manage-config/SKILL.md` § resolve-outline-skill vs `extension-api/standards/ext-point-outline.md` lines 73 and 127.
