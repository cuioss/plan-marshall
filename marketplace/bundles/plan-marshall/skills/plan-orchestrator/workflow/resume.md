# Resume Verb Workflow

Workflow doc for the `resume` verb: re-anchor a fresh session from the persisted tree alone. The persist/stop-resume contract — `status.json` as machine authority, the generated START-HERE block, the `resume_anchor` discipline — is owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `orchestrator` and `platform_runtime` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

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

**When `phase == closed`**: report the frozen state to the operator — the `phase`, the terminal `resume_anchor`, and each entry of `plans[]` with its final per-plan outcome — and STOP. Skip Steps 3, 4, and 5 entirely: no START-HERE regeneration, no queue reconciliation/transition, no `resume_anchor` or work-log write. Emit only the Output section with `plans_launched: 0`, `plans_staged: 0`, and `reconciliations: 0`. The re-anchor is purely read-only — it persists nothing, honouring the "resume on a closed epic never reconciles or persists" contract in [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) (the "Archive relocates, never deletes" bullet).

**When `phase != closed`** (`init` or `orchestrating`): proceed to Step 3 as documented below.

### Step 3: Regenerate and reconcile the derivable blocks

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Paste **both** returned blocks verbatim between their generated-block markers in `epic.md` — the `summary` between the `resume-summary` markers and the `ordered_queue` between the `ordered-queue` markers. Then read `epic.md` for the human context (Vision, Decisions, Open Defects, Watches) — any statement there that conflicts with `status.json` is stale prose; reconcile status.json → epic.md, never the reverse.

**Derived-beats-narrative reconciliation rule.** The block's `**Inbox (derived)**` line and the returned `inbox_queued` / `inbox_archived` / `inbox_state` fields are derived at render time from the epic's `inbox/` directory. When they disagree with a count sentence in the `resume_anchor` prose, **the derived line wins** — the anchor is the stale party, not the filesystem. Correct the anchor via `manage-status update-field` (the Step 5 call below), in the same status.json → epic.md direction this doc already mandates; never edit the derived line to match the prose. An `inbox_state: missing` is NOT "zero queued": it means the epic has no `inbox/` directory, so nothing could be drained from it — treat it as a scaffold gap to report, not as an empty queue.

### Step 4: Verify in-flight plan states (ground truth)

For each `launched` plan in the queue, verify the recorded state against ground truth within the small-ops carve-out — the plan's actual lifecycle state, its PR/CI state via read-side `plan-marshall:tools-integration-ci:ci` calls. A plan that shipped or stalled while no session was watching is reconciled now (queue transition + `epic.md` update per [`analyze.md`](analyze.md) semantics).

### Step 5: Report and confirm the anchor

When Step 4's ground-truth verification changed any queue state (a plan transitioned, a reconciliation landed), the Step 3 blocks are now stale — they rendered the pre-reconciliation queue. Regenerate and replace **both** blocks (START-HERE and Ordered Queue) between their markers BEFORE returning, so the persisted `epic.md` reflects the reconciled queue:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

When Step 4 changed nothing, the Step 3 block is already current and this regeneration is skipped.

Report the re-anchored state to the operator: epic phase, queue summary, in-flight plans, open defects/watches, and the next action from `resume_anchor`. When Step 4's verification changed the next action, update the anchor. The Step 3 derived-beats-narrative rule also fires here: when the regenerated block's derived inbox counts contradict a count sentence carried in `resume_anchor`, the anchor is corrected to agree with the derived counts — the derived line is authoritative and is never edited to match the prose:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Log the resume:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging work \
  --plan-id {slug} --level INFO --message "[STATUS] (plan-marshall:plan-orchestrator) Session resumed on epic {slug}" --store orchestrator
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
