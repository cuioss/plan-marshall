# Close Verb Workflow

Workflow doc for the `close` verb: freeze the epic into `history.md` and mark it closed. The close-freezes-never-deletes rule is owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

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

### Step 2: Pre-close reconciliation

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

The read returns the assembled ledger — the header, the queue rows as `plans`, and the resume anchor. Confirm the queue is settled: no `launched` plan remains unreconciled (a still-in-flight plan blocks the close — analyze its state first per [`analyze.md`](analyze.md), or record the operator's explicit decision to close with it parked). A `legacy_layout` refusal means the ledger was never migrated: run `orchestrator migrate-layout --slug {slug}` first (see [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `migrate-layout`), then resume here.

Render the terminal queue state. `resume-summary` is a read that writes nothing; it returns the START HERE block as `summary` and the live Ordered Queue as `ordered_queue`, both rendered from the ledger:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Keep both returned blocks for Step 3, which writes them into `history.md`. Then bring the generated view up to the same terminal state, so the tracked `queue-view.md` the closed tree keeps agrees with the ledger it is frozen beside:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

Nothing is pasted into `epic.md` — it is hand-written narrative only, and it is frozen as it stands.

### Step 3: Freeze into history.md

Write `history.md` via the Write tool: the epic's final state — vision as pursued, the Step 2 `summary` and `ordered_queue` blocks verbatim, the queue outcome per plan, the decision record, unresolved defects and watches (carried forward as leads, not silently dropped), and the closing rationale. `history.md` is written from the rendered blocks, never from a hand-written table, so a stale queue is never frozen permanently.

Report the queue outcome over the terminal status vocabulary (see [`orchestration-model.md` § Plan-Status Vocabulary](../../persona-plan-orchestrator/standards/orchestration-model.md#plan-status-vocabulary)), per plan row read in Step 2:

- **Shipped** — a row at `shipped` or `landed`: the work finished and merged.
- **Closed unshipped** — a row at `superseded`, `transferred`, `retired`, or `resolved`, named by its own status: the work ended without shipping, and the status says how.
- **Parked** — a row still at `parked`: live work that did not finish before the close, carried forward as a lead.

A row at any other status reached this step only through the operator's explicit decision in Step 2; name it with its status and that decision.

`epic.md` and the rest of the tree remain on disk untouched — close freezes, never deletes; the tree is the audit record.

### Step 4: Mark the epic closed

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field phase --value closed --store orchestrator
```

Set the terminal resume anchor, written to `resume_anchor.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "epic closed — see history.md" --store orchestrator
```

START HERE renders the phase and the anchor, so regenerate the view once more and commit it with the closed ledger:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
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
display_detail: "epic {slug} closed: {D} shipped, {U} closed unshipped, {K} parked"
slug: {slug}
phase: closed
plans_shipped: {D}
plans_closed_unshipped[U]{plan,status}:
  PLAN-NN,superseded
plans_parked: {K}
carried_forward_leads: {N}
history: history.md
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

`plans_shipped` counts the `shipped` and `landed` rows. `plans_closed_unshipped[]` names each row that closed without shipping together with its own status (`superseded` / `transferred` / `retired` / `resolved`), so the four different endings are never folded into one count. `plans_parked` counts the rows still `parked`.
