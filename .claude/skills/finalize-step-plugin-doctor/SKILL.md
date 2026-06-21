---
name: finalize-step-plugin-doctor
description: Finalize-phase wrapper that runs the plugin-doctor quality-gate — scoped to the skills the plan touched, or whole-tree when a plugin-doctor/plan-doctor rule changes or the scope read is indeterminate — gating structural lint before push
user-invocable: false
mode: script-executor
allowed-tools: Bash
order: 6
---

# Finalize Step: plugin-doctor

## Purpose

Run the plugin-doctor `quality-gate` invariant rule set (argparse safety, argument-naming, manage-invocation, extension contracts, shell-substitution, lesson-id / historical prose, role-field) scoped to the marketplace source of any skill the plan modifies — gating structural lint **before push**. Catches structural breakage that the Python `quality-gate` (ruff/mypy/pytest) cannot detect. The `affected_files` read (Step 1) and skill-dir extraction (Step 2) SUPPLY the `--paths` targets the gate scopes to; the skip-clean exit (Step 3) skips the gate when the read succeeds and the plan touched no skill.

The wrapper runs in one of three mutually-exclusive modes, selected deterministically (see Step 2.5 for the precedence): it runs **whole-tree** (no `--paths`) when the changed set touches a plugin-doctor / plan-doctor analyzer or rule script — a rule change re-classifies skills the diff never touched, so only a full marketplace pass catches the breakage (the **F1 trigger**); it runs **whole-tree** when the `affected_files` read is indeterminate (broken, not empty); and otherwise it **scopes** the gate to the changed skill directories (the common case).

Ordered at `order: 6` so it slots between `default:finalize-step-pre-push-quality-gate` (order 5) and `project:finalize-step-pre-submission-self-review` (order 7) — structural lint gates before the commit is pushed, not after CI.

When the plan runs in an isolated worktree, the gate first regenerates a worktree-bound executor so the `manage-invocation-invalid` rule probes each script's `--help` against the worktree's TRUE argparse surface. Without this step, the worktree's `.plan/execute-script.py` is a symlink to the main checkout's executor, whose embedded mappings resolve every `manage-*` notation to the main-checkout (pre-plan) script — making a newly added subcommand read as a false-positive "unregistered" and a newly required flag read as a false-negative that masks the real CI finding.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-plugin-doctor` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to query references.json for affected_files)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **before** `default:commit-push` in the steps list so structural lint gates before push.

In a worktree-backed plan, the gate step is preceded by a worktree-fresh-executor regeneration (Step 4 below) that rebinds notation→path resolution to the worktree's scripts. Regeneration failure is non-fatal (logged WARN) — a gate run against the still-stale executor is no worse than not regenerating, so finalize must not hard-block on a mapping refresh.

## Workflow

### Step 1: Read affected files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field affected_files
```

Parse the returned list of file paths. Capture the read's status and error: `status: success` means the read resolved (the list MAY be empty); `status: error` with `error: field_not_found` means the scope-deriving read is broken (not empty) and Step 3's indeterminate branch applies.

### Step 2: Extract skill directory paths (the `--paths` supplier)

Filter the file list to entries matching either pattern:
- `marketplace/bundles/{bundle}/skills/{skill}/` (marketplace skills)
- `.claude/skills/{skill}/` (project-local skills)

For each matching file, extract the skill directory path (everything up to and including the skill name directory). Deduplicate the result. These extracted skill directories are the `--paths` targets supplied to the `quality-gate` invocation in Step 5.

Example: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` → `marketplace/bundles/plan-marshall/skills/phase-5-execute`

### Step 2.5: Select gate mode (F1 trigger → whole-tree)

The gate runs in exactly one of three modes. Evaluate them in this fixed precedence order and pick the first that applies:

1. **F1-trigger whole-tree mode** — at least one entry in the Step 1 `affected_files` list matches either `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` OR `marketplace/bundles/plan-marshall/skills/plan-doctor/**` (a plugin-doctor / plan-doctor analyzer or rule script changed). A rule change re-classifies skills the diff never touched, so the gate MUST run over the whole marketplace — Step 5 runs `quality-gate` with **no `--paths`** against the resolved `--marketplace-root`. This precedes the skip-clean exit: even when no skill directory survived Step 2 filtering, an F1-trigger hit forces a whole-tree run rather than a skip.
2. **Indeterminate-read whole-tree fallback** — the Step 1 read returned `status: error` / `error: field_not_found` (the scope-deriving read is broken, not empty). Step 5 runs `quality-gate` with **no `--paths`** (see Step 3 Case (b)).
3. **Scoped mode** (the common case) — neither whole-tree condition holds; Step 5 scopes the gate to the skill directories extracted in Step 2.

When the F1 trigger fires, skip the Step 3 skip-clean exit entirely and proceed to Step 4, then run the whole-tree invocation in Step 5. The two whole-tree modes (F1 trigger, indeterminate read) share the same no-`--paths` invocation — they differ only in what selects them.

### Step 3: Skip-clean exit (only on a successful, genuinely-empty read)

The skip-clean exit is taken ONLY when the Step 2.5 F1 trigger did NOT fire AND the Step 1 read succeeded (`status: success`) AND zero skill paths remain after Step 2 filtering — the plan genuinely touched no skill. An F1-trigger hit (Step 2.5 mode 1) forces a whole-tree run and MUST NOT take this exit. An errored (`status: error` / `error: field_not_found`) read is **indeterminate** (the input is broken, not empty) and MUST NOT take this exit either; it falls through to the whole-tree fallback below.

**Case (a) — successful read, zero skill paths after filtering** (the plan touched no skill): log, record the step as done, and return success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-plugin-doctor) No skill changes detected; skipping plugin-doctor quality-gate"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "no skill changes detected"
```

**Case (b) — read returns `status: error` / `error: field_not_found`** (indeterminate scope, not empty): do NOT take the skip-clean exit and do NOT record `--outcome done --display-detail "no skill changes detected"` off the broken read. Instead, fall back to gating the full plan scope so structural lint still runs: log the indeterminate-read fallback, proceed to Step 4 (resolve worktree path), then in Step 5 run the `quality-gate` with **no `--paths` scoping** (whole-tree gate) against the resolved `--marketplace-root`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) affected_files read indeterminate; falling back to whole-tree plugin-doctor quality-gate"
```

### Step 4: Regenerate a worktree-fresh executor

Resolve the active worktree path:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Parse `worktree_path` from the returned TOON. This value also determines the `--marketplace-root` passed to Step 5:

- **Non-empty `worktree_path`** (worktree-backed plan) — Step 5 uses `--marketplace-root {worktree_path}/marketplace` (the parent of `bundles/` inside the worktree, NOT `bundles/`), so the gate runs against the in-progress edits.
- **Empty `worktree_path`** (main-checkout flow) — Step 5 uses `--marketplace-root marketplace`. Skip the executor regeneration below and proceed to Step 5.

When `worktree_path` is non-empty, replace the worktree's `.plan/execute-script.py` symlink (which points at the main-checkout executor) with a worktree-bound executor so the `manage-invocation-invalid` rule probes `--help` against the worktree's argparse:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate \
  --marketplace-root {worktree_path}
```

This mirrors `test/conftest.py::_ensure_executor_present` on CI. Regeneration failure is **non-fatal**: log a WARN line and proceed to Step 5 with the existing executor.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) Worktree executor regeneration failed; gating against existing executor"
```

### Step 5: Run the quality-gate

**Scoped invocation** (the common case — Step 1 read succeeded and Step 2 yielded one or more skill directories): run the plugin-doctor `quality-gate` scoped to the skill directories extracted in Step 2, against the marketplace root resolved in Step 4 (`{worktree_path}/marketplace` for a worktree, `marketplace` for the main checkout):

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  quality-gate --paths {space-separated skill directory paths} --marketplace-root {marketplace root}
```

**Whole-tree invocation** (either whole-tree mode from Step 2.5 — the F1 trigger fired, OR the indeterminate case of Step 3 Case (b) where the `affected_files` read errored / `field_not_found`): run the `quality-gate` with **no `--paths` scoping** against the same resolved marketplace root, so the structural lint runs over the whole tree — catching a doctor / plan-doctor rule change that breaks an otherwise-untouched skill (F1), and not false-skipping off a broken scope-deriving read (indeterminate):

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  quality-gate --marketplace-root {marketplace root}
```

Parse the TOON output. The violation signal is `status: fail` (the script also exits 1) OR `total_issues > 0`. On a violation, log the failure, record the step outcome `failed`, and exit with `status: error` so phase-6-finalize aborts **before** `default:commit-push`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome failed \
  --display-detail "plugin-doctor: {total_issues} violations"
```

On `status: pass` / `total_issues: 0`, log, record the step as done, and exit success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "plugin-doctor clean: {N} skills gated"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Missing `pm-plugin-development` bundle | Fatal config error — the project opted into the wrapper without the dependency |
| Empty `worktree_path` (main-checkout flow) | Skip Step 4 regeneration — the executor already reflects the current checkout; proceed to the scan |
| Worktree executor regeneration fails | Non-fatal — log WARN and gate against the existing executor; finalize does not hard-block on a mapping refresh |
| Changed set touches a plugin-doctor / plan-doctor analyzer or rule script (F1 trigger, Step 2.5 mode 1) | Whole-tree mode: do NOT skip-clean even when no skill dir survived Step 2; run the whole-tree `quality-gate` (Step 5, no `--paths`) so a rule change that breaks an untouched skill is caught, then record the outcome from that gate run |
| `affected_files` read succeeds, zero skill paths after filtering, F1 trigger did NOT fire | Skip-clean exit (plan touched no skills) — record `mark-step-done --outcome done --display-detail "no skill changes detected"` so the `phase_steps_complete` handshake invariant counts the step as done |
| `affected_files` read returns `status: error` / `error: field_not_found` | Indeterminate: do NOT skip-clean; fall back to the whole-tree `quality-gate` (Step 5, no `--paths`) so structural lint still runs, then record the outcome from that gate run |
| plugin-doctor `status: fail` / `total_issues > 0` | Fatal — record `mark-step-done --outcome failed --display-detail "plugin-doctor: {total_issues} violations"`, then abort finalize before `default:commit-push` |
| plugin-doctor `status: pass` / `total_issues: 0` | Record `mark-step-done --outcome done --display-detail "plugin-doctor clean: {N} skills gated"` |

## Related

- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling pattern for cache sync
- `pm-plugin-development:plugin-doctor` — underlying tool; this wrapper invokes its scopeable `quality-gate --paths` verb (see that skill's `## Canonical invocations`)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
