# Resume Verb Workflow

Workflow doc for the `resume` verb: re-anchor a fresh session from the persisted tree alone. The persist/stop-resume contract — `status.json` as machine authority, the generated START-HERE block, the `resume_anchor` discipline — is owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Session-opening verbs surface the epic in the terminal title. Push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

The push is best-effort and gating is inherited: when the terminal-title surface is not configured, the seam is a silent no-op — no push happens and the verb proceeds normally.

### Step 2: Read the machine authority

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Extract `phase`, `resume_anchor`, `workstreams[]`, and `plans[]`. The `resume_anchor` is the single field a fresh session trusts first — it names the exact next action.

A slug naming an archived (closed-and-relocated) epic resolves from `archived-orchestrators/` via the read-fallback, so `resume --slug {archived}` re-anchors the frozen audit record without error — the read verb finds the archived tree when the active `orchestrator/{slug}/` path is absent. An archived epic is `phase: closed`; the resume is a read-only re-anchor of the frozen record (report and re-orient), not a re-opening.

### Step 3: Regenerate and reconcile START HERE

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Paste the returned block verbatim between the generated-block markers in `epic.md`. Then read `epic.md` for the human context (Vision, Decisions, Open Defects, Watches) — any statement there that conflicts with `status.json` is stale prose; reconcile status.json → epic.md, never the reverse.

### Step 4: Verify in-flight plan states (ground truth)

For each `launched` plan in the queue, verify the recorded state against ground truth within the small-ops carve-out — the plan's actual lifecycle state, its PR/CI state via read-side `plan-marshall:tools-integration-ci:ci` calls. A plan that shipped or stalled while no session was watching is reconciled now (queue transition + `epic.md` update per [`analyze.md`](analyze.md) semantics).

### Step 5: Report and confirm the anchor

When Step 4's ground-truth verification changed any queue state (a plan transitioned, a reconciliation landed), the Step 3 START-HERE block is now stale — it rendered the pre-reconciliation queue. Regenerate it and replace the block between the generated-block markers BEFORE returning, so the persisted `epic.md` reflects the reconciled queue:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

When Step 4 changed nothing, the Step 3 block is already current and this regeneration is skipped.

Report the re-anchored state to the operator: epic phase, queue summary, in-flight plans, open defects/watches, and the next action from `resume_anchor`. When Step 4's verification changed the next action, update the anchor:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Log the resume:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging work \
  --plan-id {slug} --level INFO --message "[STATUS] (plan-marshall:marshall-orchestrator) Session resumed on epic {slug}" --store orchestrator
```

## Output

```toon
status: success | error
display_detail: "epic {slug} re-anchored: {anchor-short}"
slug: {slug}
phase: init | orchestrating | closed
plans_launched: {N}
plans_staged: {N}
reconciliations: {N}
resume_anchor: "{anchor}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period (truncate the anchor to fit).
