---
name: default:finalize-step-simplify
description: Domain-agnostic phase-6 cognitive simplification pass — reviews the plan's changeset against the minimum-viable-code anti-patterns and deletes surplus structure directly in the worktree
order: 8
---

# Finalize Step: simplify

Cognitive simplification pass for the `default:finalize-step-simplify` finalize step. Reviews the plan's change surface against the "minimum viable code" anti-patterns and deletes the surplus structure directly in the worktree, BEFORE `commit-push` materialises the commit. This is the dynamic, judgement-driven complement to plugin-doctor's static `SIMPLICITY_*` rules: the doctor catches the mechanically-recognisable patterns at edit time, this step reasons about everything else at finalize time.

Domain-agnostic **by construction** — the dispatched prompt loads ONLY the three domain-invariant foundation standards (D1/D2/D3 below). No language- or bundle-specific guidance is loaded, so the step applies uniformly to Java, Python, JavaScript, documentation, and marketplace changesets alike.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-simplify` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The step is gated into the manifest at composition time by the two `manage-execution-manifest` decision surfaces described in **Activation and skip-reason** below, so this executor is never dispatched for the plans those surfaces exclude.

## Activation and skip-reason

Two independent composition-time surfaces decide whether `finalize-step-simplify` lands in `manifest.phase_6.steps` (both owned by `manage-execution-manifest` — see [`manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)):

1. **The `simplify_inactive` pre-filter** — drops the step when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`. This is the change-shape gate: a pure-analysis / verification / enhancement plan, or a plan that touched zero files, has no surplus structure worth a holistic sweep.
2. **The `plan.phase-6-finalize.simplify` run-at-all gate** (`auto` default | `always` | `never`, read via `manage-config plan phase-6-finalize get --field simplify`) — the operator override applied by the finalize-selection post-matrix transform. `auto` defers to the `simplify_inactive` pre-filter (historical behaviour); `always` forces the step in even when the pre-filter would have dropped it; `never` removes it unconditionally. The config contract (field definition, default, validation via `validate_run_at_all`) is owned by [`manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) § phase-6-finalize; this step is the consumer.

**Visible skip-reason**: whenever the step is skipped, the composer emits a decision-log line to the plan's `logs/decision.log` that names which surface fired, so the omission is observable rather than silent:

- Pre-filter skip (`auto` deferred to a failing `simplify_inactive`):

  ```
  (plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — change_type={value} affected_files_count={N}
  ```

- Ceremony `never` skip (operator forced the step out):

  ```
  (plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — finalize.simplify=never, dropped finalize-step-simplify from phase_6.steps
  ```

A `record-step` row with `outcome: skipped` is additionally appended to the manifest's `execution_log[]` when the dispatcher resolves the step as absent, so the skip is both decision-logged at compose time and execution-logged at finalize time.

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `--scope {changeset|artifact}` — review scope (default `changeset`).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands and edits below MUST target `{worktree_path}`.

The step derives the plan's live footprint on demand from the worktree (via `compute-footprint`) to bound the review to the plan's own change surface — it never reviews files the plan did not touch.

**Scope semantics:**

- **`changeset`** (default) — review the diff hunks of each modified file against the base SHA. The agent reasons about the lines the plan added or changed, not the file's pre-existing content.
- **`artifact`** — review each modified file in full. Used when the plan rewrote files substantially and the surrounding context matters.

## HEAD-dependency

`finalize-step-simplify` is a member of `HEAD_DEPENDENT_STEPS` (see `phase-6-finalize/SKILL.md`). Because it applies edits directly to the worktree, a loop-back fix task that advances HEAD past the recorded `head_at_completion` MUST re-fire this step so the simplification pass runs against the newer tree. Capture `git rev-parse HEAD` immediately before the terminal `mark-step-done` call and forward it via `--head-at-completion {sha}`.

## Workflow

### Step 1: Resolve the simplicity posture and changeset

Derive the plan's live footprint from the worktree (the union of the `{base}...HEAD` diff and the porcelain working-tree state); the returned `files` list is the change surface to review:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

Resolve the active `simplicity` posture description (D3 — the value→description string the plan recorded at refine/outline time):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field simplicity --audit-plan-id {plan_id}
```

The `simplicity` value (`lean` / `pragmatic` / `defensive`) tunes how aggressively the review deletes surplus structure: `lean` deletes everything not justified by a live caller, `pragmatic` keeps low-risk surplus, `defensive` only flags the clearest cases.

Also resolve the per-invocation **coverage instruction** — this step is a runtime CONSUMER of the [coverage-gathering contract](../../dev-agent-behavior-rules/standards/coverage-gathering-contract.md). Read the contract runtime path: `coverage_instruction` (the expanded block) → re-expand the identifier via `coverage expand` → `coverage resolve --phase phase-6-finalize` (project default) → `inherit/inherit` (behavior-preserving):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field coverage_scope

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field coverage_instruction
```

Capture `{cov_scope}` and `{cov_instruction}` (absent → treat as `inherit`). **`simplicity` controls aggressiveness; coverage controls scope + depth.** When `--scope` is unset, derive the effective scope from `{cov_scope}`: `change-set`/`inherit` → `changeset`; `artifact`/`component`/`module`/`overall` → `artifact`. `inherit/inherit` reproduces today's default (`changeset` scope, face-value review).

### Step 2: Resolve the dispatch target

The cognitive review dispatches under `--phase phase-6-finalize` (no `--role`; finalize-step-simplify tracks `phase-6-finalize.default`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize
```

Extract the `target` field from the TOON output and use it as `{target}` below.

### Step 3: Dispatch the simplification review

Dispatch the domain-agnostic simplification prompt. The dispatched agent loads ONLY the three foundation standards — no domain skills:

- **D1** `plan-marshall:dev-general-code-quality` — the `## Minimum Viable Code` section enumerates the seven anti-patterns (see `dev-general-code-quality/standards/code-organization.md` § `#minimum-viable-code`).
- **D2** `plan-marshall:dev-agent-behavior-rules` — Principle 7 "Implement the Minimum, Not the Maximum" (see `dev-agent-behavior-rules/standards/agent-behavior-rules.md`).
- **D3** the resolved `simplicity` posture description string from Step 1.

```
Task: plan-marshall:{target}
  prompt: |
    name: finalize-step-simplify
    plan_id: {plan_id}
    skills[2]:
    - plan-marshall:dev-agent-behavior-rules
    - plan-marshall:dev-general-code-quality
    instructions: |
      Review the plan's change surface for surplus structure and delete it.
      Scope: {scope} ({changeset} = diff hunks vs base SHA; {artifact} = each
      modified file in full). The files to review are the footprint `files`
      list resolved in Step 1; never touch a file outside that list. Apply the
      "minimum viable code" anti-patterns from dev-general-code-quality
      standards/code-organization.md #minimum-viable-code under the resolved
      simplicity posture "{simplicity_description}": delete unused parameters,
      thin re-export shims, defensive catch-alls around already-handled
      failures, near-identical helpers collapsible into one, signature-restating
      docstrings, single-caller config keys, and speculative abstractions with
      no second implementation. Apply edits directly to the worktree via Edit.
      Coverage depth (from the resolved coverage instruction "{cov_instruction}"):
      at T1/T2/inherit, review each anti-pattern at face value (today's behavior);
      at T3+, trace each deletion candidate's callers and cross-references before
      deleting it. inherit/inherit reproduces today's face-value review.
      When a deletion would change a public/protected element or could plausibly
      serve an imminent requirement, leave it and record it as a finding instead
      of editing. Return TOON with status, findings[] (file/line/anti_pattern/
      action), and applied_edits count.

    WORKTREE: --plan-id {plan_id}
```

Parse the returned TOON: `findings[]` and `applied_edits`.

### Step 4: Capture HEAD and mark step done

Capture the post-edit HEAD for the HEAD-dependency contract:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture as `{head_sha}`. Then mark the step done, forwarding the SHA:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-simplify --outcome done \
  --head-at-completion {head_sha} \
  --display-detail "Simplify: {applied_edits} edits, {findings_count} findings"
```

The `display_detail` string appears in the renderer's per-step `[OK]` row. The `--head-at-completion` SHA is consulted by the dispatcher's HEAD-comparison on re-entry (see SKILL.md § HEAD-dependent steps).

## Error Handling

| Scenario | Action |
|----------|--------|
| Live footprint empty (`compute-footprint` returns no `files`) | Mark `done` with `display_detail "Simplify: no changeset"` — nothing to review |
| `simplicity` field absent | Default to the `lean` posture description and proceed |
| Dispatched agent returns an error TOON | Mark `failed` with the agent's error in `display_detail`; finalize halts per the dispatcher's error handling |

## Related

- [../../dev-general-code-quality/standards/code-organization.md](../../dev-general-code-quality/standards/code-organization.md) — § `#minimum-viable-code` (D1): the seven anti-patterns the review deletes
- [../../dev-agent-behavior-rules/standards/agent-behavior-rules.md](../../dev-agent-behavior-rules/standards/agent-behavior-rules.md) — Principle 7 (D2): "Implement the Minimum, Not the Maximum"
- [../../manage-execution-manifest/standards/decision-rules.md](../../manage-execution-manifest/standards/decision-rules.md) — the composition rule that gates this step into `phase_6.steps`
- [../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md](../../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md) — the static `SIMPLICITY_*` rules this step's cognitive pass complements
