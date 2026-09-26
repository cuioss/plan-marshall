# Resume Verb Workflow

Workflow doc for the `resume` verb: re-anchor a fresh session from the persisted tree alone. The persist/stop-resume contract — the ledger files (the header `status.json`, the `queue/{PLAN-ID}.json` rows, and `resume_anchor.md`) as machine authority, the generated `queue-view.md`, the resume-anchor discipline — is owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

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

The read assembles the ledger files into one document. Extract `phase`, `resume_anchor` (the text of `resume_anchor.md`), `workstreams[]`, and `plans` (the queue rows read from `queue/{PLAN-ID}.json`, in `(seq, id)` order). The resume anchor is the single field a fresh session trusts first — it names the exact next action. The same rows are also readable through `orchestrator queue --slug {slug}`, which additionally names any row file it could not read in `unreadable_rows`.

A slug naming an archived (closed-and-relocated) epic resolves from `archived-orchestrators/` via the read-fallback, so `resume --slug {archived}` re-anchors the frozen audit record without error — the read verb finds the archived tree when the active `orchestrator/{slug}/` path is absent. An archived epic is `phase: closed`; the resume is a read-only re-anchor of the frozen record (report and re-orient), not a re-opening.

#### Recovery: `legacy_layout`

When the read refuses with `error: legacy_layout`, the epic's `status.json` still carries the queue or the anchor — the ledger was never converted to the per-concern layout. It is refused rather than read as an empty ledger, so nothing below can proceed on it. Convert it:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator migrate-layout \
  --slug {slug}
```

The conversion preserves every value, strips the generated blocks out of `epic.md` without touching a hand-written byte, and writes a fresh `queue-view.md`; a second run reports `already_migrated`. Commit the converted files, then restart this workflow at Step 2.

### Step 2.5: Closed-epic early return (read-only gate)

The read-only gate keys off `phase == closed`, NOT narrowly "is it archived" — a `phase: closed` epic (archived or not) has no further orchestration work. `close` requires that no launched plan remains before it sets `phase: closed` and writes the terminal resume anchor ("epic closed — see history.md"), so a closed epic's queue is already settled.

**When `phase == closed`**: report the frozen state to the operator — the `phase`, the terminal resume anchor, and each queue row with its final per-plan outcome — and STOP. Skip Steps 3, 4, and 5 entirely: no view regeneration, no queue reconciliation/transition, no resume-anchor or work-log write. Emit only the Output section with `plans_launched: 0`, `plans_staged: 0`, and `reconciliations: 0`. The re-anchor is purely read-only — it persists nothing, honouring the "resume on a closed epic never reconciles or persists" contract in [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) (the "Archive relocates, never deletes" bullet).

**When `phase != closed`** (`init` or `orchestrating`): proceed to Step 3 as documented below.

### Step 3: Render START HERE and check the view

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

`resume-summary` is a read that writes nothing. It renders START HERE (`summary`) and the live Ordered Queue (`ordered_queue`) from the ledger files — not from `epic.md`, which carries neither block — and reports `view_current`: whether the committed `queue-view.md` matches a fresh render. Re-orient from the returned `summary`.

When `view_current` is `false` — the view is behind the ledger, or absent — bring it level:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

Then read `epic.md` for the human context (Vision, Queue annotations, Decisions, Open Defects, Watches) — any statement there that conflicts with the ledger files is stale prose; reconcile ledger files → `epic.md`, never the reverse.

**Derived-beats-narrative reconciliation rule.** The block's `**Inbox (derived)**` line and the returned `inbox_queued` / `inbox_archived` / `inbox_state` fields are derived at render time from the epic's `inbox/` directory. When they disagree with a count sentence in the resume anchor prose, **the derived line wins** — the anchor is the stale party, not the filesystem. Correct the anchor via `manage-status update-field` (the Step 5 call below), in the same ledger-first direction this doc already mandates; never edit the derived line to match the prose. An `inbox_state: missing` is NOT "zero queued": it means the epic has no `inbox/` directory, so nothing could be drained from it — treat it as a scaffold gap to report, not as an empty queue.

#### Recovery: a merge conflict in `queue-view.md`

A session resuming after a merge can find git conflict markers in `queue-view.md` — two sessions each regenerated the view after staging different plans. The file is derived, so the conflict carries no information. ⛔ **Never merge `queue-view.md` by hand.** Merge the source files, then run `regenerate-view` on the merged tree (the call above) and `git add queue-view.md`. The verb never reads `queue-view.md`, so it simply overwrites the conflict markers.

When `regenerate-view` refuses with `row_unreadable` or `ledger_unreadable` instead, a SOURCE file — a `queue/{PLAN-ID}.json` row or the header — still holds a conflict, most often a duplicate plan id staged on two machines. That is a genuine conflict: resolve the named file first, then regenerate. The refusal writes nothing, so regeneration never hides it.

### Step 4: Verify in-flight plan states (ground truth)

For each `launched` plan in the queue, verify the recorded state against ground truth within the small-ops carve-out — the plan's actual lifecycle state, its PR/CI state via read-side `plan-marshall:tools-integration-ci:ci` calls. A plan that shipped or stalled while no session was watching is reconciled now (queue transition + `epic.md` narrative update per [`analyze.md`](analyze.md) semantics).

### Step 5: Report and confirm the anchor

Report the re-anchored state to the operator: epic phase, queue summary, in-flight plans, open defects/watches, and the next action from the resume anchor. When Step 4's verification changed the next action, update the anchor. The Step 3 derived-beats-narrative rule also fires here: when the rendered block's derived inbox counts contradict a count sentence carried in the resume anchor, the anchor is corrected to agree with the derived counts — the derived line is authoritative and is never edited to match the prose. The value is written to the anchor file, `resume_anchor.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

When Step 4 changed any queue state or this step changed the anchor, the view rendered at Step 3 is stale. Regenerate it BEFORE returning, and commit it with the changed ledger files:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

When nothing changed, the view is already current and this regeneration is skipped.

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
