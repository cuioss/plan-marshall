---
name: default:architecture-refresh
description: Refresh architecture descriptors after a plan ships — tier-0 deterministic discover + diff-driven commit, tier-1 LLM re-enrichment
order: 25
default_on: true
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Architecture Refresh

Pure executor for the `architecture-refresh` finalize step. The pre-baseline is the committed `origin/main` tree: `_project.json` and the per-module `enriched.json` files are git-tracked, so `origin/main`'s `.plan/project-architecture/` is a zero-cost snapshot of the architecture surface as it stood before this plan. Tier 0 extracts that baseline, re-runs `discover --force`, and commits the regenerated descriptor when the working tree actually shifted; Tier 1 optionally re-enriches the affected modules via an LLM pass.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `architecture-refresh` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer beyond the documented Tier-0 / Tier-1 knob reads and the absent-baseline short-circuit.

This step is **inline** (executed directly inside the finalize main context, not via a separate Task agent) because the Tier-1 `prompt` mode requires an `AskUserQuestion` interaction. Inline steps are not timeout-wrapped — they execute under the host platform's standard per-call ceiling.

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `{plan_id}` | dispatcher | Forwarded from `phase-6-finalize` Step 3. |
| `{worktree_path}` | dispatcher | Resolved by `phase-6-finalize` Step 0 — the active git worktree (or main checkout when no worktree is in use). All `git -C` calls use this path. Build/CI/architecture script calls accept either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch); the two flags are mutually exclusive — see `tools-script-executor/standards/cwd-policy.md` § "Bucket B" for the canonical two-state contract. The literal `--project-dir {worktree_path}` examples below are the explicit-override form; callers may substitute `--plan-id {plan_id}` to use auto-resolution. |
| `{main_checkout}` | dispatcher | Resolved by `phase-6-finalize` Step 0 — used post-worktree-removal only; this step ALWAYS runs against `{worktree_path}`. |
| `architecture_refresh.tier_0` | manage-run-config | `enabled` (default) | `disabled`. Read once at the top of Tier-0. |
| `architecture_refresh.tier_1` | manage-run-config | `prompt` (default) | `auto` | `disabled`. Read once at the top of Tier-1. |
| `change_type` | status metadata | Plan-level change type (`feature`, `bug_fix`, `verification`, `refactor`, …). Read once for the Tier-1 short-circuit. |

## Step Sequence

The step flow is:

1. Read inputs (run-config knobs + change_type).
2. Extract the `origin/main` architecture baseline (Tier-0-enabled only); short-circuit when `origin/main` carries no committed baseline.
3. Tier 0 — `discover --force`, diff against the extracted baseline, reject a regressive descriptor delta at the commit gate, then commit when `.plan/project-architecture` is dirty on disk.
4. Tier 1 — LLM re-enrichment of the affected modules (`added ∪ removed`).
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  metadata --plan-id {plan_id} --get --field change_type
```

When `change_type` is absent, treat it as `unknown` and proceed (no Tier-1 short-circuit applies; the Tier-1 knob alone governs).

## Step 2: Extract the origin/main Architecture Baseline

The pre-baseline is `origin/main`'s committed `.plan/project-architecture/` tree. Because `_project.json` and the per-module `enriched.json` files are git-tracked, the committed tree is the snapshot to diff the freshly-regenerated descriptors against — no separate capture is needed at plan start.

### 2a. Tier-0 disabled short-circuit

If the run-config returned `tier_0: disabled`, skip extraction and the entire Tier-0 deterministic pass. `affected_modules` is never computed (treated as UNKNOWN in Tier 1). Log the decision and proceed to Step 4:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 skipped — architecture_refresh.tier_0 = disabled"
```

When Tier 0 is disabled, Tier 1 still runs against the *unchanged* `.plan/project-architecture/` descriptor. The two tiers are independently switchable; the only coupling is that Tier-1 `auto`/`prompt` consumes the `diff-modules --pre` result, which a Tier-0-disabled path does not produce. Tier-1 documents how it handles a missing diff (see Step 4 below).

### 2b. Extract the committed baseline tree

Extract `origin/main`'s `.plan/project-architecture/` subtree into a temp directory under the worktree. Clear any previous extraction, create a fresh extraction root, archive the subtree, then unpack it — four single commands:

```bash
rm -rf {worktree_path}/.plan/temp/architecture-baseline {worktree_path}/.plan/temp/architecture-baseline.tar
```

```bash
mkdir -p {worktree_path}/.plan/temp/architecture-baseline
```

```bash
git -C {worktree_path} archive --format=tar --output=.plan/temp/architecture-baseline.tar origin/main .plan/project-architecture
```

```bash
tar -xf {worktree_path}/.plan/temp/architecture-baseline.tar -C {worktree_path}/.plan/temp/architecture-baseline
```

The `git archive` pathspec `.plan/project-architecture` produces tar entries rooted at that path, so after extraction the baseline descriptor lives at `{baseline_dir} = {worktree_path}/.plan/temp/architecture-baseline/.plan/project-architecture` — the directory that directly contains `_project.json`. Step 3b feeds `{baseline_dir}` to `diff-modules --pre`.

### 2c. Absent-baseline short-circuit (Branch A)

When `origin/main` carries no committed `.plan/project-architecture/_project.json`, there is no baseline to diff against. Two equivalent signals reach this branch: the `git archive` call in 2b exits non-zero (the pathspec matched nothing in `origin/main`), or — when a partial tree extracts without `_project.json` — `diff-modules` in Step 3b returns `error: snapshot_not_found`. On either signal, mark the step done with the no-baseline outcome and return without running discover / diff / commit or Tier 1:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-6-finalize:architecture-refresh) Skipped — no committed origin/main architecture baseline"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "skipped — no committed origin/main architecture baseline"
```

## Step 3: Tier 0 — Deterministic Refresh

Tier 0 regenerates the descriptor with `architecture discover --force`, diffs it against the extracted baseline to surface the affected module set, and commits only when the regenerated descriptor actually changed on disk.

### 3a. Run discover --force

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  discover --force --project-dir {worktree_path}
```

The `--force` flag instructs `manage-architecture` to bypass any freshness checks and rewrite `_project.json` plus the per-module `enriched.json` stubs. `derived.json` is not persisted, so `--force` does not rewrite per-module derived files; the call is an idempotent refresh of the module index and a re-seed of empty enrichment stubs for newly-discovered modules.

### 3b. Diff against the extracted baseline

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  diff-modules --pre {baseline_dir} --project-dir {worktree_path}
```

Capture the four buckets from the TOON output: `added`, `removed`, `changed`, `unchanged`. **Against a derived-less git baseline the `changed` bucket is noise.** `origin/main` commits `_project.json` + `enriched.json` only — `derived.json` is ephemeral and never committed — so the snapshot side has no per-module `derived.json` sha and EVERY common module classifies as `changed`. The reliable drift signal is therefore the index-derived buckets only:

```text
affected_modules = added ∪ removed     # sorted; intra-module structural drift (the changed bucket) is out-of-scope
```

If `diff-modules` returns `error: snapshot_not_found`, the extracted baseline lacked `_project.json` → treat as the absent-baseline case (Step 2c Branch A): mark the step done with the no-baseline detail and return.

### 3c. Commit gate — porcelain status

Decide whether to commit on the REAL on-disk delta after `discover --force`, not on the diff buckets (which always report every common module as `changed` against this baseline). Check the architecture path only:

```bash
git -C {worktree_path} status --porcelain .plan/project-architecture
```

Empty output → the regenerated descriptor is byte-identical to the committed tree; there is nothing to commit. Log Branch C and proceed to Tier 1 with `affected_modules` as computed in 3b:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 — .plan/project-architecture clean after discover, no commit needed"
```

### 3c.5. Regression gate — reject regressive descriptor deltas

When `git status --porcelain .plan/project-architecture` is non-empty there is a regenerated delta queued for commit. Before committing it, inspect WHAT changed in the project-identity fields — the commit gate must refuse a *regressive* delta even though the porcelain status is non-empty. A regressive delta is a regenerated `name` that lost the curated value (canonically, overwritten with the worktree/plan-id basename) or a `description` / `description_reasoning` blanked from a previously-curated value. This is the defense-in-depth backstop for the `api_discover` identity-preservation fix: even if a future source path reintroduces the corruption, the commit gate refuses to ship it onto the plan's PR.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  descriptor-regression-check --pre {baseline_dir} --project-dir {worktree_path}
```

Parse `status`, `regressive` (bool), and `violations[]` from the TOON output. `{baseline_dir}` is the same extracted-baseline directory Step 3b passed to `diff-modules`.

- **`status: error`** → the regression check itself failed (e.g., the baseline directory cannot be read, the project-architecture descriptor is malformed, or a required field is absent). Treat this the same as `regressive: true`: do NOT commit, do NOT push. Log an ERROR carrying the TOON `error` and `detail` fields, mark the step `outcome failed`, and return — the delta is left uncommitted in the worktree.
- **`regressive: false`** → the delta is benign (the module index shifted, project identity intact). Proceed to 3d and commit.
- **`regressive: true`** → do NOT commit, do NOT push. The regenerated descriptor lost curated project identity. Log an ERROR naming the violated fields, leave the regressive descriptor uncommitted in the worktree, mark the step `outcome failed`, and return — do NOT abort the finalize pipeline (the next plan retries from a clean state once the source path is repaired):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-6-finalize:architecture-refresh) Regressive descriptor delta refused — {violation_fields}; leaving .plan/project-architecture uncommitted"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome failed \
  --display-detail "regressive descriptor delta refused — {violation_fields}"
```

`{violation_fields}` is the comma-separated list of `violations[].field` values (e.g., `name, description`).

### 3d. Non-empty status — commit the refresh

When `git status --porcelain .plan/project-architecture` is non-empty AND the 3c.5 regression gate returned `regressive: false`, the regenerated descriptors are dirty in the worktree and safe to ship. Stage and commit the architecture path only:

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
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 commit — {added_count} added / {removed_count} removed"
```

`affected_modules = added ∪ removed` (the bucket union, sorted) — pass forward to Step 4.

## Step 4: Tier 1 — LLM Re-enrichment

Tier 1 re-runs the LLM-curated enrichment pass on the modules whose structure was added or removed. It is the expensive half of architecture refresh and is gated by both a change-type shortcut and a tier knob.

### 4a. change_type shortcut

If `change_type` is `bug_fix` or `verification`, skip Tier 1 entirely. These change types do not warrant LLM re-enrichment regardless of the run-config setting because they target behaviour, not structure — `bug_fix` repairs an existing capability and `verification` adds tests around it; neither shifts the architectural narrative captured in `enriched.json`. Log and continue to Step 5:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — change_type = {change_type}"
```

### 4b. Affected-modules empty (Tier-0-enabled, no added/removed)

When Tier 0 ran and `added ∪ removed` is empty, `affected_modules = []`. There is no enrichment to do — log and exit Tier 1 cleanly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — no affected modules"
```

Continue to Step 5.

### 4c. Affected-modules unknown (Tier-0-disabled path)

When Tier 0 was disabled in 2a, `affected_modules` was never computed — the diff-modules call did not run. In that case, treat Tier 1 as if the user wants the deterministic input first; emit a work-log warning and skip Tier 1 to avoid running LLM enrichment over an arbitrary surface:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[WARNING] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — Tier 0 disabled, no diff to scope re-enrichment"
```

This branch is intentional: enabling Tier 1 without Tier 0 produces a re-enrichment pass with no scoping signal. The remediation is to re-enable Tier 0 (`architecture-refresh set-tier-0 --value enabled`) on the next plan; this run exits cleanly. Continue to Step 5.

### 4d. Tier-1 knob dispatch

With `affected_modules` non-empty and `change_type` not in the shortcut list, dispatch by the run-config tier-1 value:

#### `disabled` — note in PR and exit

The user has chosen to never re-enrich automatically. Record a note in the PR body so a future contributor (or `/marshall-steward` Step 13) knows enrichment is pending. There is no atomic append verb on the `ci` surface — `pr edit` REPLACES the body from a prepared scratch file. The pattern is therefore: allocate a scratch body path with `prepare-body --for edit`, write the combined body (existing body + the re-enrichment note) into that path, then `pr edit` to push it.

`{pr_number}` is the PR number resolved earlier in finalize by the `create-pr` step's outcome record.

First read the current PR body so the note is appended rather than overwriting it (`pr view` is branch-identified — pass `--head {worktree_branch}`):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr view --head {worktree_branch}
```

Allocate the scratch body path (the call returns the `body_path` to write into):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr prepare-body --plan-id {plan_id} --for edit
```

Write the combined content — the existing body followed by the re-enrichment note — into the returned `body_path` via the Write tool:

```text
Write(file_path="{body_path}", content="{existing_body}\n\nArchitecture re-enrichment recommended for: {affected_modules_csv}. Run /marshall-steward Step 13 to refresh.")
```

Push the edited body:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr edit --pr-number {pr_number} --plan-id {plan_id}
```

`{affected_modules_csv}` is the sorted, comma-separated module-name list (e.g., `oauth-sheriff-core, oauth-sheriff-quarkus`). Log the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 disabled — appended re-enrichment note to PR body"
```

Continue to Step 5.

#### `auto` — run re-enrichment without prompting

Re-run the LLM enrichment pass against the affected modules. There is no batch verb — the LLM MUST iterate `affected_modules_csv` (the sorted, comma-separated module-name list captured from the `added ∪ removed` buckets in 3b) and follow `manage-architecture/SKILL.md` Steps 5–8 for each module. Each iteration calls three per-verb subcommands; every call carries `--project-dir {worktree_path}`:

```text
for each module M in affected_modules_csv:
    # Step 6 — write responsibility + purpose
    python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
      enrich module --name M \
      --responsibility "{1-3 sentence description}" \
      --responsibility-reasoning "{source}" \
      --purpose {purpose-value} \
      --purpose-reasoning "{signal}" \
      --project-dir {worktree_path}

    # Step 7 — write 2-4 key packages (one call per package)
    for each architecturally significant package P of M:
        python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
          enrich package --module M --package P \
          --description "{1-2 sentence description}" \
          --project-dir {worktree_path}

    # Step 8 — refresh skills-by-profile
    python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
      enrich skills-by-profile --module M \
      --skills-json '{"<profile>": ["<bundle:skill>", ...]}' \
      --reasoning "{why these profiles/skills apply}" \
      --project-dir {worktree_path}
```

There is no batch form of the enrich verb that accepts a comma-separated module list — only the per-module triplet (`enrich module` / `enrich package` / `enrich skills-by-profile`) is registered, and it rewrites `enriched.json` for one named module per call without touching `derived.json`. Follow the per-module signal analysis documented in `manage-architecture/SKILL.md` Steps 5–8 (purpose-value table, key-package selection, skills-by-profile resolution) to determine each command's arguments.

After enrichment completes for every module in `affected_modules_csv`, stage and commit the updated `enriched.json` files:

```bash
git -C {worktree_path} add .plan/project-architecture
```

```bash
git -C {worktree_path} commit -m "chore(architecture): re-enrich affected modules after {plan-title}"
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

```text
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

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the refresh outcome. The payload differs by branch — pick the matching template below. (Branch A's mark-step-done is emitted inline in Step 2c.)

**Branch A — no committed origin/main baseline (Step 2c path)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "skipped — no committed origin/main architecture baseline"
```

**Branch B — Tier 0 disabled, Tier 1 also skipped**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "tier-0 disabled; tier-1 skipped"
```

**Branch C — Tier 0 ran, no diff**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "no module structure changed"
```

**Branch D — Tier 0 commit only (Tier 1 skipped via change_type, knob, or empty diff)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed derived data ({affected_module_count} modules)"
```

**Branch E — Tier 0 + Tier 1 enrich (auto or prompt-accepted)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed + re-enriched ({affected_module_count} modules)"
```

**Branch F — Tier 0 commit, Tier 1 deferred to PR note (disabled or prompt-declined)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed; re-enrichment deferred to PR note"
```

The `--display-detail` strings are subject to the output-template contract (≤80 chars, single line, no trailing period, plain ASCII) — see `phase-6-finalize/SKILL.md` "Required termination" and `standards/output-template.md` for the full convention.

## Error Handling

| Failure | Action |
|---------|--------|
| `git archive origin/main .plan/project-architecture` exits non-zero | `origin/main` carries no committed architecture baseline (the pathspec matched nothing). This is NOT a failure — treat as Branch A: mark the step done with `--display-detail "skipped — no committed origin/main architecture baseline"`, return without running discover / diff / commit. |
| `discover --force` returns `status: error` | Log ERROR, mark the step `outcome failed` with `--display-detail "discover failed — see work.log"`, return — do NOT abort the finalize pipeline. The next plan will retry from a clean state. |
| `diff-modules --pre` returns `error: snapshot_not_found` | The extracted baseline lacked `_project.json` — equivalent to no committed baseline. Treat as Branch A (NOT a failure): mark the step done with `--display-detail "skipped — no committed origin/main architecture baseline"`. |
| `descriptor-regression-check` returns `regressive: true` | The regenerated descriptor lost curated project identity (name overwritten with the worktree/plan-id basename, or description/description_reasoning blanked). Do NOT commit or push. Log ERROR, mark the step `outcome failed` with `--display-detail "regressive descriptor delta refused — {fields}"`, leave `.plan/project-architecture` uncommitted, and return — do NOT abort the finalize pipeline. The next plan retries from a clean state once the source path is repaired. |
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

```text
read tier_0      := manage-run-config architecture-refresh get-tier-0
read tier_1      := manage-run-config architecture-refresh get-tier-1
read change_type := manage-status metadata get change_type

# --- Tier 0 ---
if tier_0 != "enabled":
    log: "Tier 0 skipped — disabled"
    affected := UNKNOWN  # never computed
else:
    # extract origin/main's committed baseline tree
    mkdir -p {baseline_root}
    git -C {worktree_path} archive --format=tar --output={baseline_tar} origin/main .plan/project-architecture
        → on non-zero (no committed baseline):
            log: "skipped — no committed origin/main architecture baseline"
            mark-step-done outcome=done detail="skipped — no committed origin/main architecture baseline"
            return
    tar -xf {baseline_tar} -C {baseline_root}     # baseline_dir := {baseline_root}/.plan/project-architecture

    architecture discover --force --project-dir {worktree_path}
    diff := architecture diff-modules --pre {baseline_dir} --project-dir {worktree_path}
        → on error snapshot_not_found:
            log: "skipped — no committed origin/main architecture baseline"
            mark-step-done outcome=done detail="skipped — no committed origin/main architecture baseline"
            return
    # the changed bucket is noise against a derived-less git baseline
    # (snap_sha == None ⇒ every common module classifies as "changed")
    affected := diff.added ∪ diff.removed         # sorted; intra-module drift out-of-scope

    if git -C {worktree_path} status --porcelain .plan/project-architecture is empty:
        log: "Tier 0 — clean after discover, no commit needed"
        # fall through to Tier 1 with affected as computed
    else:
        reg := architecture descriptor-regression-check --pre {baseline_dir} --project-dir {worktree_path}
        if reg.regressive:
            log ERROR: "Regressive descriptor delta refused — {fields}"
            mark-step-done outcome=failed detail="regressive descriptor delta refused — {fields}"
            return    # leave .plan/project-architecture uncommitted
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): refresh derived data after {plan-title}"
        git -C {worktree_path} push
        log artifact

# --- Tier 1 ---
if change_type in {"bug_fix", "verification"}:
    log: "Tier 1 skipped — change_type = {change_type}"
    mark-step-done with appropriate detail
    return

if affected == UNKNOWN:           # tier_0 disabled
    log WARNING: "Tier 1 skipped — no diff to scope"
    mark-step-done with "tier-0 disabled; tier-1 skipped"
    return

if len(affected) == 0:            # tier_0 enabled but no added/removed
    log: "Tier 1 skipped — no affected modules"
    mark-step-done with "no module structure changed"
    return

switch tier_1:
    case "disabled":
        existing := ci pr view --head {worktree_branch}
        body_path := ci pr prepare-body --plan-id {plan_id} --for edit
        write "{existing}\n\nArchitecture re-enrichment recommended for: {csv}. Run /marshall-steward Step 13 to refresh." to body_path
        ci pr edit --pr-number {pr_number} --plan-id {plan_id}
        mark-step-done detail="refreshed; re-enrichment deferred to PR note"

    case "auto":
        for each module M in affected:
            # manage-architecture/SKILL.md Steps 5-8, per module
            architecture enrich module --name M --responsibility ... --purpose ... --project-dir {worktree_path}
            for each architecturally significant package P of M:
                architecture enrich package --module M --package P --description ... --project-dir {worktree_path}
            architecture enrich skills-by-profile --module M --reasoning ... --project-dir {worktree_path}
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): re-enrich affected modules after {plan-title}"
        git -C {worktree_path} push
        mark-step-done detail="refreshed + re-enriched ({n} modules)"

    case "prompt":              # default
        answer := AskUserQuestion(
            "Architecture re-enrichment recommended for: {csv}. Re-enrich now?",
            options=["Re-enrich now", "Skip — note in PR"])
        if answer == "Re-enrich now":
            # Execute the auto branch above verbatim — iterate affected and call
            # enrich module / enrich package / enrich skills-by-profile per module.
            execute auto branch above
        else:
            execute disabled branch above
```

## Cross-References

- `phase-1-init/SKILL.md` — phase-1-init does not snapshot the architecture descriptor; this step derives its pre-baseline from the committed `origin/main` tree instead.
- `manage-run-config/SKILL.md` `architecture-refresh` subcommand group — the source of truth for tier-0 / tier-1 knob semantics.
- `manage-architecture/standards/client-api.md` `discover`, `diff-modules`, and `descriptor-regression-check` — the deterministic backbone of Tier 0, including the derived-less-baseline classification note (every common module reports `changed` against a git baseline; consume `added` / `removed` only) and the commit-gate regression predicate that refuses a regressive project-identity delta.
- `manage-architecture` `enrich` verb — the LLM re-enrichment surface used by Tier 1 `auto` and `prompt`-accepted paths.
- `phase-6-finalize/standards/output-template.md` — the renderer that consumes `--display-detail` from the Branch A–F templates above.
- `phase-6-finalize/standards/required-steps.md` — declares `architecture-refresh` as a required step for the `phase_steps_complete` handshake.
