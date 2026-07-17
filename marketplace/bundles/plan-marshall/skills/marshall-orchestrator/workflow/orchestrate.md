# Orchestrate Workflow (status / next)

Shared workflow doc for the two queue-facing verbs: `status` (report the queue and resume state) and `next` (emit the next ready-to-run `/plan-marshall` command). The doc branches on the invoked verb after the shared read steps. The emit-only hand-off rule and the surface-disjointness rule are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |
| verb | Yes | `status` or `next` — resolved by the SKILL router (no verb defaults to `status`). |

## Workflow

### Step 1: Read the queue (shared)

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator queue \
  --slug {slug}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

### Step 2 (verb = `status`): Report

Render the queue report from the machine authority: per-plan status (staged / launched / shipped / parked), workstream grouping, open defects and watches from `epic.md`, and the `resume_anchor`. When the report reveals stale prose in `epic.md` (a queue row disagreeing with `status.json`), reconcile status.json → epic.md and regenerate the START-HERE block:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Skip Steps 3–5 and return.

### Step 3 (verb = `next`): Select the next launchable plan

Pick the first `staged` plan in queue order whose dependencies (sequencing notes in its `plans/PLAN-NN-{plan_slug}.md` spec) are satisfied. Check **surface disjointness** against every currently-launched plan: the candidate may be emitted while another plan is in flight ONLY when their expected surfaces do not overlap. Overlapping candidates are sequenced — report the overlap and the plan being waited on instead of emitting.

### Step 4 (verb = `next`): Emit the command

EMIT the ready-to-run command for the operator, composed from the staged spec:

```text
/plan-marshall plan={proposed_plan_id}
```

together with the spec's request payload (the spec body is the request source). The verb NEVER launches the plan inline — the operator runs the emitted command; implementation happens exclusively inside the plan lifecycle. When the operator confirms the launch, record the transition:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator queue \
  --slug {slug} --transition PLAN-NN --status launched
```

### Step 5 (verb = `next`): Log and set the resume anchor

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{emit decision: PLAN-NN emitted, disjointness verdict}" --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Regenerate the START-HERE block (Step 2 invocation) after any queue-touching change.

## Output

`status` verb:

```toon
status: success | error
display_detail: "epic {slug}: {S} staged, {L} launched, {D} shipped"
slug: {slug}
verb: status
resume_anchor: "{anchor}"
```

`next` verb:

```toon
status: success | error
display_detail: "emitted {PLAN-NN} for epic {slug}"
slug: {slug}
verb: next
emitted_plan: PLAN-NN
emitted_command: "/plan-marshall plan={proposed_plan_id}"
disjointness: clear | sequenced-behind-{PLAN-MM}
```

`display_detail` is ≤80 chars, ASCII, no trailing period. When disjointness sequences the candidate, `emitted_plan`/`emitted_command` are absent and `display_detail` names the blocking plan.
