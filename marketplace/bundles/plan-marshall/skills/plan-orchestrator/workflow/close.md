# Close Verb Workflow

Workflow doc for the `close` verb: freeze the epic into `history.md` and mark it closed. The close-freezes-never-deletes rule is owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

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

### Step 2: Pre-close reconciliation

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Confirm the queue is settled: no `launched` plan remains unreconciled (a still-in-flight plan blocks the close — analyze its state first per [`analyze.md`](analyze.md), or record the operator's explicit decision to close with it parked). Regenerate the two derivable blocks one final time so the frozen record carries the terminal queue state:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Write **both** returned blocks verbatim into `epic.md` (Write tool) BEFORE Step 3 freezes `history.md`: the `summary` between the `BEGIN/END GENERATED: resume-summary` markers, and the `ordered_queue` between the `BEGIN/END GENERATED: ordered-queue` markers. `history.md` is derived from the epic's final state, so `epic.md` must already carry BOTH terminal blocks when it is frozen — a stale Ordered Queue table frozen here is permanent, so do not leave either write implicit.

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
