# Archive Verb Workflow

Workflow doc for the `archive` verb: relocate a *closed* epic tree from `orchestrator/{slug}/` to `archived-orchestrators/{slug}/` for store-root tidiness. `archive` is a post-close, opt-in, mechanical move — it never freezes and never deletes; the tree is preserved as the permanent audit record, just at a tidier home. The archive-relocates-never-deletes rule and the no-retention policy are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

`archive` refuses a non-closed epic — run `close` first (see [`close.md`](close.md)), then `archive`.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing, closed epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Session-opening verbs surface the epic in the terminal title for the duration of the verb:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

The push is best-effort and gating is inherited: when the terminal-title surface is not configured, the seam is a silent no-op — no push happens and the verb proceeds normally.

### Step 2: Pre-archive check

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Confirm `phase == closed`. When the epic is not yet closed, STOP and run `close` first — `archive` is a post-close relocation. This pre-check is a fast-fail courtesy; the `orchestrator.py archive` subcommand (Step 4) independently refuses a non-closed epic with `error: not_closed` and performs no move, so deferring entirely to the subcommand's refusal is also correct.

### Step 3: Log the archive decision (BEFORE the move)

Log the decision to the orchestrator store BEFORE the relocation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{archive decision: relocating closed epic {slug} to archived-orchestrators/}" --store orchestrator
```

The BEFORE ordering keeps the first-time archive's decision in the tree that is about to move: on a first archive the active `orchestrator/{slug}/` tree still exists, so the log write lands there and is relocated into the archived audit record along with the rest of the epic.

The `--store orchestrator` log write resolves transparently for BOTH a first-time archive and a repeated request. `plan_logging.get_log_path` resolves the orchestrator store with the `allow_archived=True` read-fallback (an audit-trail append is not a business-state mutation), so on a REPEAT request — where the active tree is already gone and only `archived-orchestrators/{slug}/` remains — the decision write lands in the archived `logs/` tree instead of scaffolding an empty active-path directory. That transparency is load-bearing for idempotency: without it, the log write would resurrect an empty active `orchestrator/{slug}/` tree, and Step 4's `cmd_archive` `source.exists()` probe would then misread the epic as not-yet-archived (falling into the `not_closed` refusal) instead of reaching the idempotent `already_archived: true` success path.

### Step 4: Invoke the mechanical relocation

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator archive \
  --slug {slug}
```

This is the deterministic directory move. It refuses a non-closed epic (`error: not_closed`, no move), a missing epic (`error: not_found`), or an existing archive (`error: archive_conflict`); an already-archived slug returns idempotent success (`already_archived: true`). On success it returns `archived_to` as the **absolute, main-anchored filesystem path** `str(dest)` — e.g. `/abs/path/.plan/local/archived-orchestrators/{slug}` — not the relative `archived-orchestrators/{slug}` form. `cmd_archive` itself carries **no** `display_detail` field; the `display_detail` in the Output section below is composed by the calling workflow (this LLM), not emitted by the script. The read verbs (`status`, `resume`) resolve the archived epic transparently, so archiving never orphans the audit record.

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
display_detail: "epic {slug} archived to archived-orchestrators/"
slug: {slug}
already_archived: true | false
archived_to: /abs/path/.plan/local/archived-orchestrators/{slug}
```

`archived_to` is the absolute, main-anchored filesystem path `cmd_archive` returns via `str(dest)` (not the relative `archived-orchestrators/{slug}` form). `display_detail` is composed by the calling workflow — `cmd_archive` does not emit it — and is ≤80 chars, ASCII, no trailing period.
