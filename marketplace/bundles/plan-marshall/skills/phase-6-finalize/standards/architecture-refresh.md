---
name: default:architecture-refresh
description: Refresh architecture descriptors after a plan ships — tier-0 deterministic discover + diff-driven commit, tier-1 LLM re-enrichment
order: 25
---

# Architecture Refresh

Pure executor for the `architecture-refresh` finalize step. Detects whether the plan changed any module's structural surface and, when it did, refreshes the project's `.plan/project-architecture/` descriptor and (optionally) re-enriches the affected modules with an LLM pass.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `architecture-refresh` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer beyond the documented Tier-0 / Tier-1 knob reads.

This step is **inline** (executed directly inside the finalize main context, not via a separate Task agent) because the Tier-1 `prompt` mode requires an `AskUserQuestion` interaction. Inline steps are not timeout-wrapped — they execute under Claude Code's standard per-call ceiling.

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `{plan_id}` | dispatcher | Forwarded from `phase-6-finalize` Step 3. |
| `{worktree_path}` | dispatcher | Resolved by `phase-6-finalize` Step 0 — the active git worktree (or main checkout when no worktree is in use). All `git -C` and build/CI/architecture script calls in this document MUST pass this value via `--project-dir`. |
| `{main_checkout}` | dispatcher | Resolved by `phase-6-finalize` Step 0 — used post-worktree-removal only; this step ALWAYS runs against `{worktree_path}`. |
| `architecture-pre/` snapshot | phase-1-init Step 5d | Pre-plan snapshot at `.plan/local/plans/{plan_id}/architecture-pre/`. Greenfield plans skipped the snapshot — see "Greenfield handling" below. |
| `architecture_refresh.tier_0` | manage-run-config | `enabled` (default) | `disabled`. Read once at the top of Tier-0. |
| `architecture_refresh.tier_1` | manage-run-config | `prompt` (default) | `auto` | `disabled`. Read once at the top of Tier-1. |
| `change_type` | status metadata | Plan-level change type (`feature`, `bug_fix`, `verification`, `refactor`, …). Read once for the Tier-1 short-circuit. |

## Step Sequence

The step flow is:

1. Read inputs (run-config knobs + change_type).
2. Greenfield handling — if no `architecture-pre/` snapshot exists, mark step done and exit.
3. Tier 0 — deterministic discover + diff + commit.
4. Tier 1 — LLM re-enrichment (skipped for `bug_fix` / `verification` change types).
5. Mark step complete with `--display-detail` summarising the outcome.

## Step 1: Read Inputs

Read both run-config knobs up-front so the rest of the document references resolved values:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh get-tier-0
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh get-tier-1
```

Read the plan's `change_type` from status metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  metadata --plan-id {plan_id} --get --field change_type
```

When `change_type` is absent, treat it as `unknown` and proceed (no Tier-1 short-circuit applies; the Tier-1 knob alone governs).

## Step 2: Greenfield Handling

If `.plan/local/plans/{plan_id}/architecture-pre/_project.json` does not exist, the plan was initialised on a greenfield project (no architecture descriptor at init time). There is nothing to diff against — the deterministic discover would have nothing to compare to and the LLM re-enrichment has no baseline. Mark the step done with the greenfield outcome and exit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files \
  exists --plan-id {plan_id} --file architecture-pre/_project.json
```

If `exists: false`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-6-finalize:architecture-refresh) Skipped — no architecture-pre snapshot (greenfield plan)"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "skipped (greenfield — no pre-snapshot)"
```

Return — do not execute Tier-0 or Tier-1.

## Step 3: Tier 0 — Deterministic Refresh

Tier 0 is the free, deterministic half of architecture refresh: it re-runs `architecture discover --force` and uses `diff-modules --pre` to decide whether anything actually shifted. When something did, it commits the regenerated descriptor; when nothing did, it exits early.

### 3a. Tier-0 disabled short-circuit

If the run-config returned `tier_0: disabled`, skip Tier 0 entirely and proceed to Step 4 (Tier 1). Document the decision in the work log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 skipped — architecture_refresh.tier_0 = disabled"
```

When Tier 0 is disabled, Tier 1 still runs against the *unchanged* `.plan/project-architecture/` descriptor. The two tiers are independently switchable; the only coupling is that Tier-1 `auto` consumes the `diff-modules --pre` result, which Tier-0-disabled paths do not produce. Tier-1 documents how it handles a missing diff (see Step 4 below).

### 3b. Run discover --force

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  discover --force --project-dir {worktree_path}
```

The `--force` flag instructs `manage-architecture` to bypass any cache freshness checks and rewrite every per-module `derived.json` plus the `_project.json` index. This is the only call in the step that mutates the live architecture descriptor — Tier 1 (re-enrichment) only touches `enriched.json`, never `derived.json`.

### 3c. Diff against the pre-snapshot

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  diff-modules --pre .plan/local/plans/{plan_id}/architecture-pre \
  --project-dir {worktree_path}
```

Capture the four buckets from the TOON output: `added`, `removed`, `changed`, `unchanged`. The first three are the *affected modules* surface — the union `added ∪ removed ∪ changed` is what Tier 1 (when active) re-enriches.

### 3d. Empty-diff branch

If `len(added) + len(removed) + len(changed) == 0`, the plan changed no module's structural surface. Log the decision and proceed to Tier 1 with an empty affected-modules set:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 — no module structure changed, no commit needed"
```

There is no commit when the diff is empty: the regenerated descriptor (from 3b) is byte-identical to the pre-snapshot's structural surface, so `git status --porcelain` against `.plan/project-architecture/` is empty and there is nothing to commit. Proceed to Step 4 (Tier 1) with `affected_modules = []`.

### 3e. Non-empty diff branch — commit the refresh

When at least one module is `added`, `removed`, or `changed`, regenerated descriptors are dirty in the worktree. Stage and commit the architecture path only:

```bash
git -C {worktree_path} add .plan/project-architecture
```

```bash
git -C {worktree_path} commit -m "chore(architecture): refresh derived data after {plan-title}"
```

`{plan-title}` is the plan's short description, captured from `manage-status read --plan-id {plan_id}` field `plan.short_description`. When `short_description` is `None` or empty, use the literal `plan-id` as the slug (e.g., `chore(architecture): refresh derived data after phase-d-auto-refresh`).

The commit message intentionally does NOT name the affected modules — the modules list is derivable from the commit's diff and from the diff-modules log line above. Naming them inline would duplicate the audit trail and inflate the subject when many modules change.

After the commit, push immediately so the refresh lands on the same PR as the plan's substantive commits:

```bash
git -C {worktree_path} push
```

Log the artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 commit — {added_count} added / {removed_count} removed / {changed_count} changed"
```

`affected_modules = added ∪ removed ∪ changed` (the bucket union, sorted) — pass forward to Step 4.

## Step 4: Tier 1 — LLM Re-enrichment

Tier 1 re-runs the LLM-curated enrichment pass on the modules whose derived structure changed. It is the expensive half of architecture refresh and is gated by both a change-type shortcut and a tier knob.

### 4a. change_type shortcut

If `change_type` is `bug_fix` or `verification`, skip Tier 1 entirely. These change types do not warrant LLM re-enrichment regardless of the run-config setting because they target behaviour, not structure — `bug_fix` repairs an existing capability and `verification` adds tests around it; neither shifts the architectural narrative captured in `enriched.json`. Log and continue to Step 5:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — change_type = {change_type}"
```

### 4b. Affected-modules empty (Tier-0-enabled empty-diff path)

When Tier 0 ran and the diff was empty, `affected_modules = []`. There is no enrichment to do — log and exit Tier 1 cleanly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — no affected modules"
```

Continue to Step 5.

### 4c. Affected-modules unknown (Tier-0-disabled path)

When Tier 0 was disabled in 3a, `affected_modules` was never computed — the diff-modules call did not run. In that case, treat Tier 1 as if the user wants the deterministic input first; emit a work-log warning and skip Tier 1 to avoid running LLM enrichment over an arbitrary surface:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[WARNING] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — Tier 0 disabled, no diff to scope re-enrichment"
```

This branch is intentional: enabling Tier 1 without Tier 0 produces a re-enrichment pass with no scoping signal. The remediation is to re-enable Tier 0 (`architecture-refresh set-tier-0 --value enabled`) on the next plan; this run exits cleanly. Continue to Step 5.

### 4d. Tier-1 knob dispatch

With `affected_modules` non-empty and `change_type` not in the shortcut list, dispatch by the run-config tier-1 value:

#### `disabled` — note in PR and exit

The user has chosen to never re-enrich automatically. Append a note to the PR body so a future contributor (or `/marshall-steward` Step 13) knows enrichment is pending:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr append-body --project-dir {worktree_path} \
  --text "Architecture re-enrichment recommended for: {affected_modules_csv}. Run /marshall-steward Step 13 to refresh."
```

`{affected_modules_csv}` is the sorted, comma-separated module-name list (e.g., `oauth-sheriff-core, oauth-sheriff-quarkus`). Log the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 disabled — appended re-enrichment note to PR body"
```

Continue to Step 5.

#### `auto` — run re-enrichment without prompting

Re-run the LLM enrichment pass against the affected modules. Use the canonical re-enrichment entry point (Steps 5–8 of the parent design's enrichment flow) via `manage-architecture`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich --modules {affected_modules_csv} --project-dir {worktree_path}
```

`{affected_modules_csv}` is the sorted, comma-separated module-name list captured from the diff buckets in 3c. The enrich verb rewrites `enriched.json` for each named module without touching `derived.json`.

After enrichment completes, stage and commit the updated `enriched.json` files:

```bash
git -C {worktree_path} add .plan/project-architecture
```

```bash
git -C {worktree_path} commit -m "chore(architecture): re-enrich {affected_modules_csv} after {plan-title}"
```

```bash
git -C {worktree_path} push
```

Log the artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 auto — re-enriched {affected_module_count} modules"
```

Continue to Step 5.

#### `prompt` (default) — AskUserQuestion gate

Ask the user whether to re-enrich now or defer. Use the AskUserQuestion shape below verbatim — the option labels are part of the documented UX and are referenced by `marshall-steward/references/wizard-flow.md` (Deliverable 4) so the configuration prompt and the runtime prompt stay aligned:

```
Question: "Architecture re-enrichment recommended for: {affected_modules_csv}. Re-enrich now?"
Options:
  - "Re-enrich now"
  - "Skip — note in PR"
```

On `Re-enrich now`: follow the `auto` branch above (enrich + commit + push) verbatim, then log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 prompt — user accepted, re-enriched {affected_module_count} modules"
```

On `Skip — note in PR`: follow the `disabled` branch above (PR body append) verbatim, then log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 prompt — user declined, appended note to PR body"
```

Continue to Step 5.

## Step 5: Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the refresh outcome. The payload differs by branch — pick the matching template below.

**Branch A — greenfield (Step 2 path)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "skipped (greenfield — no pre-snapshot)"
```

**Branch B — Tier 0 disabled, Tier 1 also skipped**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "tier-0 disabled; tier-1 skipped"
```

**Branch C — Tier 0 ran, no diff**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "no module structure changed"
```

**Branch D — Tier 0 commit only (Tier 1 skipped via change_type, knob, or empty diff)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed derived data ({affected_module_count} modules)"
```

**Branch E — Tier 0 + Tier 1 enrich (auto or prompt-accepted)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed + re-enriched ({affected_module_count} modules)"
```

**Branch F — Tier 0 commit, Tier 1 deferred to PR note (disabled or prompt-declined)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed; re-enrichment deferred to PR note"
```

The `--display-detail` strings are subject to the output-template contract (≤80 chars, single line, no trailing period, plain ASCII) — see `phase-6-finalize/SKILL.md` "Required termination" and `standards/output-template.md` for the full convention.

## Error Handling

| Failure | Action |
|---------|--------|
| `discover --force` returns `status: error` | Log ERROR, mark the step `outcome failed` with `--display-detail "discover failed — see work.log"`, return — do NOT abort the finalize pipeline. The next plan will retry from a clean state. |
| `diff-modules --pre` returns `error: snapshot_not_found` | Log ERROR, mark the step `outcome failed` with `--display-detail "snapshot lost — see work.log"`. The pre-snapshot directory should always exist at this point (Step 2's greenfield branch handles its absence) — if it disappeared mid-flight, surface the error rather than silently skipping. |
| `git -C {worktree_path} commit` fails with "nothing to commit" | This indicates `discover --force` was a no-op despite a non-empty diff (e.g., diff classified `unchanged` modules as `changed` due to a stale sha). Treat as Branch C (no diff) — log a WARNING, mark the step done with `--display-detail "no module structure changed (commit skipped)"`. |
| `git push` fails | Log ERROR, mark the step `outcome failed` with `--display-detail "push failed — see work.log"`. The `automated-review` step will not see the architecture commit; the user can push manually before merging. |
| `architecture enrich` fails | Log ERROR, fall back to Branch F (PR note) — do NOT mark the whole step failed. The deterministic refresh has already shipped; the user can re-enrich manually via `/marshall-steward` Step 13. Mark the step done with `--display-detail "refreshed; enrich failed — see work.log"`. |
| `AskUserQuestion` aborted | Treat the same as `Skip — note in PR` (Branch F). The user actively backing out is informationally equivalent to declining the prompt. |

All failures log via the standard work-log error template:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-6-finalize:architecture-refresh) {phase} failed — {error_message}"
```

## Pseudo-Code Summary

The decision flow as a single procedural block (authoritative — implementations follow this order):

```
read tier_0     := manage-run-config architecture-refresh get-tier-0
read tier_1     := manage-run-config architecture-refresh get-tier-1
read change_type := manage-status metadata get change_type

if not exists(.plan/local/plans/{plan_id}/architecture-pre/_project.json):
    log: "skipped (greenfield)"
    mark-step-done outcome=done detail="skipped (greenfield — no pre-snapshot)"
    return

# --- Tier 0 ---
if tier_0 == "enabled":
    architecture discover --force --project-dir {worktree_path}
    diff := architecture diff-modules --pre {snapshot_dir} --project-dir {worktree_path}
    affected := diff.added ∪ diff.removed ∪ diff.changed
    if len(affected) == 0:
        log: "Tier 0 — no module structure changed"
        # fall through to Tier 1 with empty affected
    else:
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): refresh derived data after {plan-title}"
        git -C {worktree_path} push
        log artifact
else:
    log: "Tier 0 skipped — disabled"
    affected := UNKNOWN  # never computed

# --- Tier 1 ---
if change_type in {"bug_fix", "verification"}:
    log: "Tier 1 skipped — change_type = {change_type}"
    mark-step-done with appropriate detail
    return

if affected == UNKNOWN:           # tier_0 disabled
    log WARNING: "Tier 1 skipped — no diff to scope"
    mark-step-done with "tier-0 disabled; tier-1 skipped"
    return

if len(affected) == 0:            # tier_0 enabled but empty diff
    log: "Tier 1 skipped — no affected modules"
    mark-step-done with "no module structure changed"
    return

switch tier_1:
    case "disabled":
        ci pr append-body --text "Architecture re-enrichment recommended for: {csv}. Run /marshall-steward Step 13 to refresh."
        mark-step-done detail="refreshed; re-enrichment deferred to PR note"

    case "auto":
        architecture enrich --modules {csv} --project-dir {worktree_path}
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): re-enrich {csv} after {plan-title}"
        git -C {worktree_path} push
        mark-step-done detail="refreshed + re-enriched ({n} modules)"

    case "prompt":              # default
        answer := AskUserQuestion(
            "Architecture re-enrichment recommended for: {csv}. Re-enrich now?",
            options=["Re-enrich now", "Skip — note in PR"])
        if answer == "Re-enrich now":
            execute auto branch above
        else:
            execute disabled branch above
```

## Cross-References

- `phase-1-init/SKILL.md` Step 5d — produces the `architecture-pre/` snapshot consumed in Step 2 / Step 3c.
- `manage-run-config/SKILL.md` `architecture-refresh` subcommand group — the source of truth for tier-0 / tier-1 knob semantics.
- `manage-architecture/standards/client-api.md` `discover` and `diff-modules` — the deterministic backbone of Tier 0.
- `manage-architecture` `enrich` verb — the LLM re-enrichment surface used by Tier 1 `auto` and `prompt`-accepted paths.
- `phase-6-finalize/standards/output-template.md` — the renderer that consumes `--display-detail` from the Branch A–F templates above.
- `phase-6-finalize/standards/required-steps.md` — declares `architecture-refresh` as a required step for the `phase_steps_complete` handshake.
