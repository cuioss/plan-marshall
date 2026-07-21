# Resume Verb Workflow

Workflow doc for the `resume` verb: re-anchor a fresh session from the persisted tree alone. The persist/stop-resume contract — `status.json` as machine authority, the generated START-HERE block, the `resume_anchor` discipline — is owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Read the machine authority

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Extract `phase`, `resume_anchor`, `workstreams[]`, and `plans[]`. The `resume_anchor` is the single field a fresh session trusts first — it names the exact next action.

A slug naming an archived (closed-and-relocated) epic resolves from `archived-orchestrators/` via the read-fallback, so `resume --slug {archived}` re-anchors the frozen audit record without error — the read verb finds the archived tree when the active `orchestrator/{slug}/` path is absent. An archived epic is `phase: closed`; the resume is a read-only re-anchor of the frozen record (report and re-orient), not a re-opening.

### Step 2.5: Closed-epic early return (read-only gate)

The read-only gate keys off `phase == closed`, NOT narrowly "is it archived" — a `phase: closed` epic (archived or not) has no further orchestration work. `close` requires that no launched plan remains before it sets `phase: closed` and writes the terminal `resume_anchor` ("epic closed — see history.md"), so a closed epic's queue is already settled.

**When `phase == closed`**: report the frozen state to the operator — the `phase`, the terminal `resume_anchor`, and each entry of `plans[]` with its final per-plan outcome — and STOP. Skip Steps 3, 4, and 5 entirely: no START-HERE regeneration, no queue reconciliation/transition, no `resume_anchor` or work-log write. Emit only the Output section with `plans_launched: 0`, `plans_staged: 0`, and `reconciliations: 0`. The re-anchor is purely read-only — it persists nothing, honouring the "resume on a closed epic never reconciles or persists" contract in [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md) (the "Archive relocates, never deletes" bullet).

**When `phase != closed`** (`init` or `orchestrating`): proceed to Step 3 as documented below.

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
