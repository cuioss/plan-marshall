---
lane:
  class: derived-state
  cost_size: S
name: default:architecture-refresh
description: Refresh architecture descriptors in the pre-push settle stage — tier-0 deterministic discover gated on the attribution verdict, tier-1 LLM re-enrichment
order: 10
default_on: true
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Architecture Refresh

Pure executor for the `architecture-refresh` finalize step. The pre-baseline is the committed `origin/main` tree: `_project.json` and the per-module `enriched.json` files are git-tracked, so `origin/main`'s `.plan/project-architecture/` is a zero-cost baseline of the architecture surface as it stood before this plan. The architecture verbs read that baseline by ref (`--pre-ref origin/main`) — this step materializes nothing on disk. Tier 0 re-runs `discover --force --apply plan`, which writes only the plan-attributable part of the regenerated descriptor, and commits it when the regression gate is green; Tier 1 optionally re-enriches the affected modules via an LLM pass.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `architecture-refresh` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer beyond the documented Tier-0 / Tier-1 knob reads, the absent-baseline short-circuit, and the attribution-verdict branches.

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
2. Probe the `origin/main` architecture baseline with `diff-modules --pre-ref origin/main` (Tier-0-enabled only); short-circuit when `origin/main` carries no committed baseline.
3. Tier 0 — `discover --force --apply plan`, branch on the attribution verdict, reject a regressive descriptor delta at the commit gate, then commit when `.plan/project-architecture` is dirty on disk.
4. Tier 1 — LLM re-enrichment of the affected modules (`added ∪ removed`), reached only on a verdict that leaves no migration deferred and nothing unattributable.
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

## Step 2: Probe the origin/main Architecture Baseline

The pre-baseline is `origin/main`'s committed `.plan/project-architecture/` tree. Because `_project.json` and the per-module `enriched.json` files are git-tracked, the committed tree is the baseline to compare against — no capture is needed at plan start, and none is taken here: `--pre-ref` reads the tree from git inside the verb and leaves no file behind.

### 2a. Tier-0 disabled short-circuit

If the run-config returned `tier_0: disabled`, skip the probe and the entire Tier-0 deterministic pass. `affected_modules` is never computed (treated as UNKNOWN in Tier 1). Log the decision and proceed to Step 4:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 skipped — architecture_refresh.tier_0 = disabled"
```

When Tier 0 is disabled, Tier 1 still runs against the *unchanged* `.plan/project-architecture/` descriptor. The two tiers are independently switchable; the only coupling is that Tier-1 `auto`/`prompt` consumes the `diff-modules` result, which a Tier-0-disabled path does not produce. Tier-1 documents how it handles a missing diff (see Step 4 below).

### 2b. Diff the working tree against origin/main

One call reads the committed baseline by ref and classifies the modules:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  --project-dir {worktree_path} diff-modules --pre-ref origin/main
```

Capture the four buckets from the TOON output: `added`, `removed`, `changed`, `unchanged`. **Against a derived-less git baseline the `changed` bucket is noise.** `origin/main` commits `_project.json` + `enriched.json` only — `derived.json` is ephemeral and never committed — so the baseline side has no per-module `derived.json` sha and EVERY common module classifies as `changed`. The reliable drift signal is therefore the index-derived buckets only:

```text
affected_modules = added ∪ removed     # sorted; intra-module structural drift (the changed bucket) is out-of-scope
```

A `status: error` other than `snapshot_not_found` (for example `invalid_ref`) is a step failure: log it with the standard error template below, mark the step `outcome failed` with `--display-detail "baseline diff failed — see work.log"`, and return.

### 2c. Absent-baseline short-circuit (Branch A)

When `diff-modules` returns `error: snapshot_not_found`, `origin/main` carries no committed `.plan/project-architecture/_project.json` — there is no baseline to compare against. Because the probe runs before discover, this short-circuit precedes every write. Mark the step done with the no-baseline outcome and return without running discover / commit or Tier 1:

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

## Step 3: Tier 0 — Attributed Refresh

Tier 0 regenerates the descriptor with `architecture discover --force --apply plan`, which classifies its own rewrite of the on-disk tree and writes only the plan-attributable part of it. The delta classes, their attribution (plan / migration / undecidable) and the verdict each set of classes reduces to are published once, in `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/manage-api.md` § discover — see that section; this step consumes the verdict and does not restate the table.

Two segments can leave `.plan/project-architecture` dirty, and only the second is discover's doing: plan-time writers that edited descriptors during the plan without committing them (segment 1), and the discover rewrite itself (segment 2). The attribution verdict governs segment 2 only. Segment 1 is plan-caused by construction and always flows through the unchanged porcelain + regression gates below.

### 3a. Run discover --force --apply plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  --project-dir {worktree_path} discover --force --apply plan
```

Parse `status`, `attribution`, `applied`, `delta_classes[]{class,attribution,module_count}`, `unclassified_fields[]{document,field}` and `unresolved_key_packages_count` from the TOON output. `{migration_classes}` below is the comma-separated `class` list of the `delta_classes` rows whose `attribution` is `migration`; `{plan_classes}` is the same for `plan`; `{unclassified_fields}` is the comma-separated `document:field` list.

On `status: error`, log ERROR, mark the step `outcome failed` with `--display-detail "discover failed — see work.log"`, and return.

Branch on `attribution` and record the outcome — every verdict gets a decision-log line, so no verdict passes silently:

- **`clean`** — the regenerated tree carries nothing the pre-state lacks; nothing was written.

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 discover — attribution clean, applied {applied}"
  ```

- **`plan_attributable`** — plan classes only; the plan projection was written (`applied: plan`, or `none` when the projection equals the pre-state).

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 discover — attribution plan_attributable, applied {applied}; plan classes: {plan_classes}"
  ```

- **`mixed`** — plan and migration classes; only the plan projection was written, and the migration classes stay unwritten for the steward upgrade to land. Set `migration_deferred = true`.

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 discover — attribution mixed, applied {applied}; plan classes: {plan_classes}; deferred migration classes: {migration_classes} ({unresolved_key_packages_count} unresolved key_packages). Reconcile via /marshall-steward upgrade"
  ```

- **`migration_only`** — migration classes only; nothing was written. Set `migration_deferred = true`.

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 discover — attribution migration_only, nothing written; migration classes: {migration_classes} ({unresolved_key_packages_count} unresolved key_packages). Reconcile via /marshall-steward upgrade"
  ```

- **`undecidable`** — at least one difference no class explains; nothing was written. Set `unattributable = true` and log the unclassified fields at WARNING as well as in the decision log:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARNING \
    --message "[WARNING] (plan-marshall:phase-6-finalize:architecture-refresh) Unattributable descriptor delta — unclassified fields: {unclassified_fields}; discover wrote nothing. Reconcile via /marshall-steward upgrade"
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 discover — attribution undecidable, nothing written; unclassified fields: {unclassified_fields}"
  ```

- **`no_baseline`** — the worktree carries no `_project.json` although `origin/main` does (Step 2 ruled out the reverse). There is no pre-state to attribute against and nothing was written; handle it exactly as `undecidable`, naming `no_baseline` in place of the unclassified fields.

Whatever the verdict, continue to 3b — segment-1 writes still reach the gates.

### 3b. Refresh the affected module set

When `applied` is `plan`, discover changed the on-disk index, so the Step 2b buckets describe the tree before the write. Re-run the same diff and take `affected_modules = added ∪ removed` from it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  --project-dir {worktree_path} diff-modules --pre-ref origin/main
```

When `applied` is `none`, discover wrote nothing and the Step 2b buckets already describe the post-discover tree — reuse them.

### 3c. Commit gate — porcelain status

Decide whether to commit on the REAL on-disk delta, not on the diff buckets (which always report every common module as `changed` against this baseline). Check the architecture path only:

```bash
git -C {worktree_path} status --porcelain .plan/project-architecture
```

Under `--apply plan` the only content that can be dirty here is plan-caused: segment-1 writes plus the plan projection. A migration class or an unattributable difference is never on disk, so it can never reach the commit below.

Empty output → there is nothing to commit. Log it and proceed to the Tier-1 entry gate (Step 4) with `affected_modules` as computed in 3b; `tier1_exit_detail()` selects the Step 5 exit cell:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 — .plan/project-architecture clean after discover, no commit needed"
```

### 3c.5. Regression gate — reject regressive descriptor deltas

When `git status --porcelain .plan/project-architecture` is non-empty there is a delta queued for commit. Before committing it, inspect WHAT changed against the `origin/main` baseline — the commit gate must refuse a *regressive* delta even though the porcelain status is non-empty. A regressive delta loses curated content: a regenerated project `name` that lost the curated value (canonically, overwritten with the worktree/plan-id basename), a `description` / `description_reasoning` blanked from a previously-curated value, a blanked module `responsibility`, or a lost or blanked `key_packages` entry. The fields the check covers are the ones its own response names in `examined_fields`, and this step logs them rather than restating them. This is the defense-in-depth backstop for the discover preservation and attribution rules: even if a future source path reintroduces the corruption, the commit gate refuses to ship it onto the plan's PR.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  --project-dir {worktree_path} descriptor-regression-check --pre-ref origin/main
```

Parse `status`, `regressive` (bool), `violations[]`, `examined_fields` and `modules_examined` from the TOON output.

- **`status: error`** → the regression check itself failed (e.g., the baseline cannot be read by ref, the project-architecture descriptor is malformed, or a required field is absent). The check never ran, so this is NOT a regression verdict and the response carries no `violations[]`, `examined_fields` or `modules_examined` to name. It shares only the commit decision with `regressive: true`: do NOT commit. Log an ERROR carrying the payload's `error` field together with the rest of the payload (the error shapes are documented in `manage-architecture/standards/client-api.md` § descriptor-regression-check), mark the step `outcome failed` with `--display-detail "regression check failed — {error}"`, and return — the delta is left uncommitted in the worktree.
- **`regressive: false`** → the delta is benign. Log the verdict together with the coverage it was computed over, so a green gate states what it examined, then proceed to 3d and commit:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:architecture-refresh) Regression gate green — examined_fields: {examined_fields}; modules_examined: {modules_examined}"
  ```

- **`regressive: true`** → do NOT commit. The delta lost curated content. Log an ERROR naming the violated fields and the coverage, leave the regressive descriptor uncommitted in the worktree, mark the step `outcome failed`, and return — do NOT abort the finalize pipeline (the next plan retries from a clean state once the source path is repaired):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-6-finalize:architecture-refresh) Regressive descriptor delta refused — {violation_fields} (examined_fields: {examined_fields}; modules_examined: {modules_examined}); leaving .plan/project-architecture uncommitted"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome failed \
  --display-detail "regressive descriptor delta refused — {violation_fields}"
```

`{violation_fields}` is the comma-separated list of `violations[].field` values (e.g., `name, enriched.key_packages`); `{examined_fields}` is the comma-separated `examined_fields` list.

### 3d. Non-empty status — commit the refresh

When `git status --porcelain .plan/project-architecture` is non-empty AND the 3c.5 regression gate returned `regressive: false`, the dirty descriptors are plan-caused and safe to ship. Stage and commit the architecture path only:

```bash
git -C {worktree_path} add .plan/project-architecture
```

```bash
git -C {worktree_path} commit -m "chore(architecture): refresh derived data after {plan-title}"
```

`{plan-title}` is the plan's short description, captured from `manage-status read --plan-id {plan_id}` field `plan.short_description`. When `short_description` is `None` or empty, use the literal `plan-id` as the slug (e.g., `chore(architecture): refresh derived data after phase-d-auto-refresh`). The subject is accurate because `--apply plan` keeps every tool migration off disk: what this commit carries is plan-caused.

The commit message intentionally does NOT name the affected modules — the modules list is derivable from the commit's diff and from the diff-modules log line above. Naming them inline would duplicate the audit trail and inflate the subject when many modules change.

**This step does NOT push.** It commits and stops. `default:push` (order 11) is a **pure push barrier** that runs immediately after this step (order 10) and ships the converged branch — including this commit — so the refresh lands on the same PR as the plan's substantive commits without this step pushing anything. Pushing here would be a second push of the same branch from a step the single-push contract does not authorise; see `push.md`, which states that the barrier "asserts the tree is clean and pushes the converged branch to remote" and "produces NO commit". The division is exact: this step produces the commit, the barrier ships it.

Log the artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 commit — {added_count} added / {removed_count} removed"
```

`affected_modules = added ∪ removed` (the bucket union, sorted) — pass forward to Step 4.

### 3e. Deferred or unattributable verdict — end after Tier 0

When `unattributable` or `migration_deferred` is set, Tier 1 does not run, and the step ends here with the matching Step 5 template. A deferred migration leaves the `enriched.json` vocabulary mid-migration, so re-enriching now would write package entries into a map the upgrade path has yet to migrate; an unattributable delta leaves the descriptor state unknown. Both are reconciled through `/marshall-steward upgrade` (see `marshall-steward/references/upgrade-flow.md`), not through a plan's finalize. Log the skip:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — attribution {attribution} leaves the descriptor for /marshall-steward upgrade"
```

Then select the Step 5 template:

- `unattributable` → **Branch H**, whether or not 3d committed segment-1 writes (the commit is on record in the `[ARTIFACT]` line; the discover delta is what went uncommitted).
- `migration_deferred` and 3d did NOT commit → **Branch G**.
- `migration_deferred` and 3d committed → **Branch I**.

## Step 4: Tier 1 — LLM Re-enrichment

Tier 1 re-runs the LLM-curated enrichment pass on the modules whose structure was added or removed. It is the expensive half of architecture refresh and is gated by the Tier-0 verdict (3e), a change-type shortcut and a tier knob. It is reached only when Tier 0 was disabled or its verdict was `clean` or `plan_attributable`.

### 4a. change_type shortcut

If `change_type` is `bug_fix` or `verification`, skip Tier 1 entirely. These change types do not warrant LLM re-enrichment regardless of the run-config setting because they target behaviour, not structure — `bug_fix` repairs an existing capability and `verification` adds tests around it; neither shifts the architectural narrative captured in `enriched.json`. Log the skip:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — change_type = {change_type}"
```

Continue to Step 5. When Tier 0 was disabled, `affected_modules` was never computed and the cell is **Branch B**; otherwise `tier1_exit_detail()` in the Pseudo-Code Summary selects it.

### 4b. Affected-modules empty (Tier-0-enabled, no added/removed)

When Tier 0 ran and `added ∪ removed` is empty, `affected_modules = []`. There is no enrichment to do — log and exit Tier 1 cleanly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 skipped — no affected modules"
```

Continue to Step 5 — **Branch J** when Step 3d committed, **Branch C** when it did not. An empty module union does not mean nothing was committed.

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

#### `disabled` — record the deferral and exit

The user has chosen to never re-enrich automatically, so the affected-module list must be recorded somewhere a future contributor (or `/marshall-steward` Step 13) will find it.

> **⚠ Owed follow-up — the PR-body note cannot be written from this step, and is not prescribed here.**
> This branch previously prescribed `ci pr view` → `ci pr prepare-body --for edit` → `ci pr edit --pr-number {pr_number}`. **No PR exists when this step runs.** `default:architecture-refresh` is order **10**; `default:create-pr` is order **20**. There is therefore no `{pr_number}` to resolve at order 10 — the "resolved earlier in finalize by the `create-pr` step's outcome record" the old text relied on refers to a step that has not run yet — and every one of those three calls would fail against a PR that does not exist.
>
> The fix is a **re-homing**, not a rewrite of this branch: the deferred-enrichment note belongs in a surface that runs after `default:create-pr` (order 20) — either appended by a post-`create-pr` step, or carried as a fact this step records and a later step consumes when it edits the PR body. Re-homing it is deliberately **out of scope here** and is recorded as owed rather than left standing as a prescription that cannot succeed. Until it lands, the deferral is recorded in the decision log and the step's `display_detail` (below), both of which are readable without a PR.
>
> **Condition on the re-homing.** Wherever the `ci pr view` → `ci pr prepare-body --for edit` → `ci pr edit` chain is re-homed, it lands with a positive shape requirement per call — each is usable when and only when the return carries `status: success` together with the field the next call consumes (`pr_number` for `view`, the prepared body path for `prepare-body`), and every other shape stops the step. The chain also makes its host document's exit-code convention obligatory in the widened form, because none of the three calls is `manage-*`. This document keeps the `manage-*`-scoped convention below precisely because, with the chain removed, every call it now issues IS `manage-*` — the scope is derived from the calls present, not inherited.

Record the deferral in the decision log. `{affected_modules_csv}` is the sorted, comma-separated module-name list (e.g., `oauth-sheriff-core, oauth-sheriff-quarkus`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 disabled — re-enrichment deferred for: {affected_modules_csv}. Run /marshall-steward Step 13 to refresh."
```

Continue to Step 5 (Branch F).

#### `auto` — run re-enrichment without prompting

Re-run the LLM enrichment pass against the affected modules. There is no batch verb — the LLM MUST iterate `affected_modules_csv` (the sorted, comma-separated module-name list captured from the `added ∪ removed` buckets in 3b) and follow `manage-architecture/SKILL.md` Steps 5–8 for each module. Each iteration calls three per-verb subcommands; every call carries `--project-dir {worktree_path}`:

```text
for each module M in affected_modules_csv:
    # Step 6 — write responsibility + purpose
    python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
      --project-dir {worktree_path} enrich module --name M \
      --responsibility "{1-3 sentence description}" \
      --responsibility-reasoning "{source}" \
      --purpose {purpose-value} \
      --purpose-reasoning "{signal}"

    # Step 7 — write 2-4 key packages (one call per package)
    for each architecturally significant package P of M:
        python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
          --project-dir {worktree_path} enrich package --module M --package P \
          --description "{1-2 sentence description}"

    # Step 8 — refresh skills-by-profile
    python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
      --project-dir {worktree_path} enrich skills-by-profile --module M \
      --skills-json '{"<profile>": ["<bundle:skill>", ...]}' \
      --reasoning "{why these profiles/skills apply}"
```

There is no batch form of the enrich verb that accepts a comma-separated module list — only the per-module triplet (`enrich module` / `enrich package` / `enrich skills-by-profile`) is registered, and it rewrites `enriched.json` for one named module per call without touching `derived.json`. Follow the per-module signal analysis documented in `manage-architecture/SKILL.md` Steps 5–8 (purpose-value table, key-package selection, skills-by-profile resolution) to determine each command's arguments.

After enrichment completes for every module in `affected_modules_csv`, stage and commit the updated `enriched.json` files:

```bash
git -C {worktree_path} add .plan/project-architecture
```

```bash
git -C {worktree_path} commit -m "chore(architecture): re-enrich affected modules after {plan-title}"
```

As in Tier 0, this step does not push — the order-11 `default:push` barrier ships this commit with the rest of the converged branch.

Log the artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 auto — re-enriched {affected_module_count} modules"
```

Continue to Step 5.

#### `prompt` (default) — AskUserQuestion gate

Ask the user whether to re-enrich now or defer. Use the AskUserQuestion shape below verbatim — the option labels are part of the documented UX:

```text
Question: "Architecture re-enrichment recommended for: {affected_modules_csv}. Re-enrich now?"
Options:
  - "Re-enrich now"
  - "Skip — note in PR"
```

On `Re-enrich now`: follow the `auto` branch above (enrich + commit; no push — the order-11 barrier ships it) verbatim, then log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 prompt — user accepted, re-enriched {affected_module_count} modules"
```

The option label still says "note in PR" even though no PR-body note can be written at this order. Renaming it belongs with the re-homing that makes the note landable again, not before it; until then the label names the intent and the owed follow-up above names the gap.

On `Skip — note in PR`: follow the `disabled` branch above (record the deferral in the decision log; no PR-body write is possible at this order — see the owed follow-up there) verbatim, then log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:architecture-refresh) Tier 1 prompt — user declined, re-enrichment deferred"
```

Continue to Step 5.

## Step 5: Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the refresh outcome. The payload differs by branch — pick the matching template below. (Branch A's mark-step-done is emitted inline in Step 2c; Branches G, H and I are selected in Step 3e; the Tier-1 skip cells are selected by `tier1_exit_detail()` in the Pseudo-Code Summary.)

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

**Branch C — Tier 0 ran, nothing committed and no module structure change**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "no module structure changed"
```

**Branch D — Tier 0 committed and module structure changed (Tier 1 skipped via change_type or knob)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed derived data ({affected_module_count} modules)"
```

**Branch J — Tier 0 committed but no module structure change (`affected_module_count` is 0)**:

Reached when segment-1 plan-time descriptor edits left `.plan/project-architecture` dirty while `added` and `removed` are both empty. The count is deliberately not interpolated — rendering `(0 modules)` would advertise a module delta the round does not have:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed derived data; no module structure changed"
```

**Branch K — module structure changed but this step committed nothing**:

Reached when `added ∪ removed` against `origin/main` is non-empty while the porcelain status is clean — the descriptor change is already committed on the branch, so this step has nothing left to commit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "module structure changed ({affected_module_count} modules); nothing to commit"
```

**Branch E — Tier 0 + Tier 1 enrich (auto or prompt-accepted)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed + re-enriched ({affected_module_count} modules)"
```

**Branch F — Tier 0 commit, Tier 1 deferred (disabled or prompt-declined)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed; re-enrichment deferred"
```

**Branch G — tool migration only, nothing committed (Step 3e)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "tool migration not committed; run marshall-steward upgrade"
```

**Branch H — unattributable descriptor delta (Step 3e)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "descriptor delta unattributable; not committed"
```

**Branch I — plan-caused refresh committed, tool migration deferred (Step 3e)**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step architecture-refresh --outcome done \
  --display-detail "refreshed derived data ({affected_module_count} modules); migration deferred"
```

The `--display-detail` strings are subject to the output-template contract (≤80 chars, single line, no trailing period, plain ASCII) — see `phase-6-finalize/SKILL.md` "Required termination" and `standards/output-template.md` for the full convention.

## Error Handling

| Failure | Action |
|---------|--------|
| `diff-modules --pre-ref origin/main` returns `error: snapshot_not_found` | `origin/main` carries no committed architecture baseline. This is NOT a failure — treat as Branch A: mark the step done with `--display-detail "skipped — no committed origin/main architecture baseline"`, return without running discover / commit. |
| `diff-modules --pre-ref origin/main` returns any other `status: error` | Log ERROR, mark the step `outcome failed` with `--display-detail "baseline diff failed — see work.log"`, return — do NOT abort the finalize pipeline. |
| `discover --force --apply plan` returns `status: error` | Log ERROR, mark the step `outcome failed` with `--display-detail "discover failed — see work.log"`, return — do NOT abort the finalize pipeline. The next plan will retry from a clean state. |
| `discover` returns `attribution: undecidable` or `no_baseline` | NOT a failure. Nothing was written; log the unclassified fields at WARNING, still gate any segment-1 writes through 3c / 3c.5 / 3d, skip Tier 1, and mark the step done with Branch H. |
| `discover` returns `attribution: migration_only` or `mixed` | NOT a failure. The migration classes stay unwritten; gate what is dirty through 3c / 3c.5 / 3d, skip Tier 1, and mark the step done with Branch G (nothing committed) or Branch I (committed). The migration lands through `/marshall-steward upgrade`. |
| `descriptor-regression-check` returns `status: error` | The check could not run, so nothing is known about the delta — this is NOT a regression verdict. Do NOT commit. The payload carries no `violations[]`, `examined_fields` or `modules_examined`, so log ERROR with its `error` field and the rest of the payload, naming no violated fields or coverage, mark the step `outcome failed` with `--display-detail "regression check failed — {error}"`, leave `.plan/project-architecture` uncommitted, and return — do NOT abort the finalize pipeline. |
| `descriptor-regression-check` returns `regressive: true` | The delta lost curated content. Do NOT commit. Log ERROR with the violated fields and the `examined_fields` / `modules_examined` coverage, mark the step `outcome failed` with `--display-detail "regressive descriptor delta refused — {fields}"`, leave `.plan/project-architecture` uncommitted, and return — do NOT abort the finalize pipeline. The next plan retries from a clean state once the source path is repaired. |
| `architecture enrich` fails | Log ERROR, fall back to Branch F (deferral recorded in the decision log) — do NOT mark the whole step failed. The deterministic refresh has already shipped; the user can re-enrich manually via `/marshall-steward` Step 13. Mark the step done with `--display-detail "refreshed; enrich failed — see work.log"`. |
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

# did THIS step ship a descriptor commit? every Tier-1 exit below reads it,
# so it is bound before the Tier-0 branch that can set it
committed := false

# --- Tier 0 ---
if tier_0 != "enabled":
    log: "Tier 0 skipped — disabled"
    affected := UNKNOWN  # never computed
else:
    # read origin/main's committed baseline by ref; nothing is materialized
    diff := architecture --project-dir {worktree_path} diff-modules --pre-ref origin/main
        → on error snapshot_not_found (no committed baseline):
            log: "skipped — no committed origin/main architecture baseline"
            mark-step-done outcome=done detail="skipped — no committed origin/main architecture baseline"
            return
    # the changed bucket is noise against a derived-less git baseline
    # (snap_sha == None ⇒ every common module classifies as "changed")
    affected := diff.added ∪ diff.removed         # sorted; intra-module drift out-of-scope

    disc := architecture --project-dir {worktree_path} discover --force --apply plan
    # verdict vocabulary and class attribution: manage-api.md § discover
    log decision: attribution, applied, classes by attribution
    migration_deferred := disc.attribution in {"migration_only", "mixed"}
    unattributable     := disc.attribution in {"undecidable", "no_baseline"}
    if unattributable:
        log WARNING: "Unattributable descriptor delta — unclassified fields: {unclassified_fields}"
    if disc.applied == "plan":
        diff := architecture --project-dir {worktree_path} diff-modules --pre-ref origin/main
        affected := diff.added ∪ diff.removed

    # only plan-caused content can be dirty: segment-1 writes + the plan projection
    if git -C {worktree_path} status --porcelain .plan/project-architecture is empty:
        log: "Tier 0 — clean after discover, no commit needed"
    else:
        reg := architecture --project-dir {worktree_path} descriptor-regression-check --pre-ref origin/main
        if reg.status == "error":
            # the check never ran: no violations[], examined_fields or modules_examined to name
            log ERROR: "Regression check failed — {reg.error}"
            mark-step-done outcome=failed detail="regression check failed — {reg.error}"
            return    # leave .plan/project-architecture uncommitted
        if reg.regressive:
            log ERROR: "Regressive descriptor delta refused — {fields} (examined_fields, modules_examined)"
            mark-step-done outcome=failed detail="regressive descriptor delta refused — {fields}"
            return    # leave .plan/project-architecture uncommitted
        log decision: "Regression gate green — examined_fields, modules_examined"
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): refresh derived data after {plan-title}"
        # no push — the order-11 default:push barrier ships this commit
        committed := true
        log artifact

    if unattributable:
        log: "Tier 1 skipped — attribution leaves the descriptor for /marshall-steward upgrade"
        mark-step-done detail="descriptor delta unattributable; not committed"
        return
    if migration_deferred:
        log: "Tier 1 skipped — attribution leaves the descriptor for /marshall-steward upgrade"
        if committed:
            mark-step-done detail="refreshed derived data ({n} modules); migration deferred"
        else:
            mark-step-done detail="tool migration not committed; run marshall-steward upgrade"
        return

# --- Tier 1 ---
# Shared exit detail for the Tier-1 skips below. It selects on BOTH dimensions,
# because neither implies the other: a round can commit segment-1 descriptor
# edits with an empty added ∪ removed union, and a round can see a non-empty
# union whose commit already landed earlier on the branch.
tier1_exit_detail() :=
    if committed and len(affected) > 0:  "refreshed derived data ({n} modules)"              # Branch D
    elif committed:                      "refreshed derived data; no module structure changed"  # Branch J
    elif len(affected) > 0:              "module structure changed ({n} modules); nothing to commit"  # Branch K
    else:                                "no module structure changed"                       # Branch C

if change_type in {"bug_fix", "verification"}:
    log: "Tier 1 skipped — change_type = {change_type}"
    if affected == UNKNOWN:       # tier_0 disabled ⇒ no module set to describe
        mark-step-done with "tier-0 disabled; tier-1 skipped"  # Branch B
    else:
        mark-step-done detail=tier1_exit_detail()
    return

if affected == UNKNOWN:           # tier_0 disabled ⇒ the commit block never ran, committed is false
    log WARNING: "Tier 1 skipped — no diff to scope"
    mark-step-done with "tier-0 disabled; tier-1 skipped"     # Branch B
    return

if len(affected) == 0:            # tier_0 enabled but no added/removed
    log: "Tier 1 skipped — no affected modules"
    mark-step-done detail=tier1_exit_detail()                 # Branch J when committed, else Branch C
    return

switch tier_1:
    case "disabled":
        # No PR exists at order 10 (default:create-pr is order 20), so no PR-body
        # write is prescribed here. Re-homing the note to a post-create-pr surface
        # is recorded as an owed follow-up in the `disabled` branch above.
        log decision: "Tier 1 disabled — re-enrichment deferred for: {csv}"
        mark-step-done detail="refreshed; re-enrichment deferred"

    case "auto":
        for each module M in affected:
            # manage-architecture/SKILL.md Steps 5-8, per module
            architecture --project-dir {worktree_path} enrich module --name M --responsibility ... --purpose ...
            for each architecturally significant package P of M:
                architecture --project-dir {worktree_path} enrich package --module M --package P --description ...
            architecture --project-dir {worktree_path} enrich skills-by-profile --module M --reasoning ...
        git -C {worktree_path} add .plan/project-architecture
        git -C {worktree_path} commit -m "chore(architecture): re-enrich affected modules after {plan-title}"
        # no push — the order-11 default:push barrier ships this commit
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

- `phase-1-init/SKILL.md` — phase-1-init does not snapshot the architecture descriptor; this step reads its pre-baseline from the committed `origin/main` tree by ref instead.
- `manage-run-config/SKILL.md` `architecture-refresh` subcommand group — the source of truth for tier-0 / tier-1 knob semantics.
- `manage-architecture/standards/manage-api.md` § discover — the `--apply` modes, the delta-class table, the attribution verdicts and their precedence; this step consumes the verdict and does not restate the table.
- `manage-architecture/standards/client-api.md` `diff-modules` and `descriptor-regression-check` — the `--pre-ref` baseline read, the derived-less-baseline classification note (every common module reports `changed` against a git baseline; consume `added` / `removed` only), and the commit-gate regression predicate with its published `examined_fields` coverage.
- `manage-architecture` `enrich` verb — the LLM re-enrichment surface used by Tier 1 `auto` and `prompt`-accepted paths.
- `marshall-steward/references/upgrade-flow.md` — the steward upgrade flow that lands a deferred tool migration on the plan-less steward PR; the reconcile path Branches G, H and I name.
- `phase-6-finalize/standards/output-template.md` — the renderer that consumes `--display-detail` from the Branch A–I templates above.
- `phase-6-finalize/standards/required-steps.md` — declares `architecture-refresh` as a required step for the `phase_steps_complete` handshake.
