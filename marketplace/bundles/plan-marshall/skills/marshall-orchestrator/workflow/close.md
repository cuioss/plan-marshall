# Close Verb Workflow

Workflow doc for the `close` verb: freeze the epic into `history.md` and mark it closed. The close-freezes-never-deletes rule is owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Session-opening verbs surface the epic in the terminal title for the duration of the verb:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

The push is best-effort and gating is inherited: when the terminal-title surface is not configured, the seam is a silent no-op — no push happens and the verb proceeds normally.

### Step 2: Pre-close reconciliation

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Confirm the queue is settled: no `launched` plan remains unreconciled (a still-in-flight plan blocks the close — analyze its state first per [`analyze.md`](analyze.md), or record the operator's explicit decision to close with it parked). Regenerate the START-HERE block one final time so the frozen record carries the terminal queue state:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Write the returned `summary` verbatim into `epic.md` between the `BEGIN/END GENERATED: resume-summary` markers (Write tool) BEFORE Step 3 freezes `history.md`. `history.md` is derived from the epic's final state, so `epic.md` must already carry the terminal START-HERE block when it is frozen — do not leave this write implicit.

### Step 3: Freeze into history.md

Write `history.md` via the Write tool: the epic's final state — vision as pursued, the shipped/dropped/parked queue outcome per plan, the decision record, unresolved defects and watches (carried forward as leads, not silently dropped), and the closing rationale. `epic.md` and the rest of the tree remain on disk untouched — close freezes, never deletes; the tree is the audit record.

### Step 4: Mark the epic closed

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field phase --value closed --store orchestrator
```

Set the terminal resume anchor:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "epic closed — see history.md" --store orchestrator
```

Log the close decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{close decision: outcome summary, carried-forward leads}" --store orchestrator
```

### Step 5: Restore the terminal title

Restore the plan-scoped title on the way out. Resolve the session's bound plan:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session resolve-plan
```

When a plan id resolves, fire the plain plan-store repaint:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --plan-id {resolved_plan_id}
```

When no plan resolves, no restore push is needed — the next hook-driven render repaints the title from the session's state. Both pushes are best-effort no-ops when the terminal-title surface is not configured.

## Output

```toon
status: success | error
display_detail: "epic {slug} closed: {D} shipped, {K} parked"
slug: {slug}
phase: closed
plans_shipped: {D}
plans_parked: {K}
carried_forward_leads: {N}
history: history.md
```

`display_detail` is ≤80 chars, ASCII, no trailing period.
