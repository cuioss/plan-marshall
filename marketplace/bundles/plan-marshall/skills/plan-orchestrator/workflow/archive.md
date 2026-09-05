# Archive Verb Workflow

Workflow doc for the `archive` verb: relocate a *closed* epic tree from `orchestrator/{slug}/` to `archived-orchestrators/{slug}/` for store-root tidiness. `archive` is a post-close, opt-in, mechanical move — it never freezes and never deletes; the tree is preserved as the permanent audit record, just at a tidier home. The archive-relocates-never-deletes rule and the no-retention policy are owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

`archive` refuses a non-closed epic — run `close` first (see [`close.md`](close.md)), then `archive`.

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
| `slug` | Yes | Epic slug of an existing, closed epic. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

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
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator archive \
  --slug {slug}
```

This is the deterministic directory move. It refuses a non-closed epic (`error: not_closed`, no move), a missing epic (`error: not_found`), or an existing archive (`error: archive_conflict`); an already-archived slug returns idempotent success (`already_archived: true`). The read verbs (`status`, `resume`) resolve the archived epic transparently, so archiving never orphans the audit record. See the Output section below for the `archived_to`/`display_detail` field contract.

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
