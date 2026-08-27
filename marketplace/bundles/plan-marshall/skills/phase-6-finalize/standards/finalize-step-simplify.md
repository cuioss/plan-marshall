---
lane:
  class: prunable
  prunable_when: no_code_delta
  cost_size: M
name: default:finalize-step-simplify
description: Domain-agnostic phase-6 cognitive simplification pass — reviews the plan's changeset against the minimum-viable-code anti-patterns and deletes surplus structure directly in the worktree
order: 8
mutates_source: true
head_dependent: true
default_on: true
presets:
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: simplify

Cognitive simplification pass for the `default:finalize-step-simplify` finalize step. Reviews the plan's change surface against the "minimum viable code" anti-patterns and deletes the surplus structure directly in the worktree; the dispatcher's commit instrumentation commits the edits before the `push` barrier runs. This is the dynamic, judgement-driven complement to plugin-doctor's static `SIMPLICITY_*` rules: the doctor catches the mechanically-recognisable patterns at edit time, this step reasons about everything else at finalize time.

Domain-agnostic **by construction** — the dispatched prompt loads ONLY the three domain-invariant foundation standards (D1/D2/D3 below). No language- or bundle-specific guidance is loaded, so the step applies uniformly to Java, Python, JavaScript, documentation, and marketplace changesets alike.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes non-`manage-*` scripts too, and a `manage-*`-scoped convention left exactly those calls uncovered — the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than looking for a fixed field list: beyond `status` and `error` the diagnostic fields vary by verb — `ci` verbs carry `operation`, `error_cause`, and `context`, the plan-resolution envelopes carry `message` and `plan_id` instead, and neither list is exhaustive. `error` is sometimes a hard-coded generic string whose real cause sits in one of the other fields, so dropping them can discard the cause entirely. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return — the envelope's diagnostic fields are not success payload, and dropping any of them leaves the step reporting a failure with no cause. A malformed or truncated stdout that carries **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause. There is no envelope to preserve on that sub-path — synthesize the error TOON instead, naming the call (notation, subcommand, and arguments) and carrying the raw stdout verbatim as the only account of the cause that exists.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-simplify` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The step is gated into the manifest at composition time by the two `manage-execution-manifest` decision surfaces described in **Activation and skip-reason** below, so this executor is never dispatched for the plans those surfaces exclude.

## Activation and skip-reason

Two independent composition-time surfaces decide whether `finalize-step-simplify` lands in `manifest.phase_6.steps` (both owned by `manage-execution-manifest` — see [`manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)):

1. **The `simplify_inactive` pre-filter** — drops the step when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`. This is the change-shape gate: a pure-analysis / verification / enhancement plan, or a plan that touched zero files, has no surplus structure worth a holistic sweep.
2. **The `steps.default:finalize-step-simplify.lane` override** (`off` | `minimal` | `standard`/absent) — declared in EITHER of the two channels the composer merges: the project-wide `plan.phase-6-finalize.steps` map in marshal.json (read via `manage-config plan phase-6-finalize step get --step-id default:finalize-step-simplify`, reading `params.lane`) or the plan-scoped `status.metadata.finalize_step_overrides` map written by `manage-config finalize-steps set-lane --plan-id …`. The composer resolves this gate from the merged plan-local-over-marshal source, so a per-plan declaration governs it exactly as a project-wide one does. It is the operator override applied by the finalize-selection ceremony transform, which maps the per-element lane override onto the force-in / force-out decision (`off→never`, `minimal→always`, `standard`/absent→auto). `standard`/absent defers to the `simplify_inactive` pre-filter (historical behaviour); `minimal` forces the step in even when the pre-filter would have dropped it; `off` removes it unconditionally. The per-element `lane` override contract (values, resolution) is owned by [`manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) § phase-6-finalize and [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md); this step is the consumer.

**Visible skip-reason**: whenever the step is skipped, the composer emits a decision-log line to the plan's `logs/decision.log` that names which surface fired, so the omission is observable rather than silent:

- Pre-filter skip (`auto` deferred to a failing `simplify_inactive`):

  ```text
  (plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — change_type={value} affected_files_count={N}
  ```

- Ceremony `off`-lane skip (operator forced the step out via `lane: off`):

  ```text
  (plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — finalize-step-simplify.lane=off, dropped finalize-step-simplify from phase_6.steps
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

**Two boundaries, both carried into the dispatched prompt.** The footprint `files` list bounds *which files* may be touched (both scopes); under `changeset` a second, **line-level** boundary bounds *which lines within them* — only the lines the plan added or changed. Stating the file boundary alone was the defect: a simplifier handed a file it may edit and no line boundary is invited to rewrite pre-existing lines the changeset never touched, which is precisely the surplus-diff the step exists to remove. The line boundary is what `changeset` and `artifact` actually differ by, so Step 3's prompt states it explicitly rather than leaving it implied by the word "hunks".

## HEAD-dependency

`finalize-step-simplify` declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Because it applies edits directly to the worktree — which the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits after the step records `done`, advancing HEAD — a loop-back fix task that advances HEAD past the recorded `head_at_completion` MUST re-fire this step so the simplification pass runs against the newer tree. Capture `git rev-parse HEAD` immediately before the terminal `mark-step-done` call and forward it via `--head-at-completion {sha}`.

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

Also resolve the per-invocation **coverage instruction** — this step is a runtime CONSUMER of the [coverage-gathering contract](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md). Read the contract runtime path: `coverage_instruction` (the expanded block) → re-expand the identifier via `coverage expand` → `coverage resolve --phase phase-6-finalize` (project default) → `inherit/inherit` (behavior-preserving):

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

- **D1** `plan-marshall:ref-code-quality` — the `## Minimum Viable Code` section enumerates the seven anti-patterns (see `ref-code-quality/standards/code-organization.md` § `#minimum-viable-code`).
- **D2** `plan-marshall:persona-plan-marshall-agent` — Principle 7 "Implement the Minimum, Not the Maximum" (see `persona-plan-marshall-agent/standards/agent-behavior-rules.md`).
- **D3** the resolved `simplicity` posture description string from Step 1.

```text
Task: plan-marshall:{target}
  prompt: |
    name: finalize-step-simplify
    plan_id: {plan_id}
    skills[2]:
    - plan-marshall:persona-plan-marshall-agent
    - plan-marshall:ref-code-quality
    instructions: |
      Review the plan's change surface for surplus structure and delete it.
      Scope: {scope} ({changeset} = diff hunks vs base SHA; {artifact} = each
      modified file in full). The files to review are the footprint `files`
      list resolved in Step 1; never touch a file outside that list.
      Under {changeset} scope the boundary is LINE-level, not merely
      file-level: within an in-scope file, only the lines this plan added or
      changed are in scope. A line that is identical to its base-SHA content
      is PRE-EXISTING and out of scope — do not delete, rewrite, or "tidy" it,
      even when it exhibits one of the anti-patterns below. Opening a file to
      change three lines is not licence to rewrite the other three hundred.
      When a pre-existing line is genuinely worth changing, record it as a
      finding instead of editing it. (Under {artifact} scope the whole file is
      in scope, which is the entire difference between the two.) Apply the
      "minimum viable code" anti-patterns from ref-code-quality
      standards/code-organization.md #minimum-viable-code under the resolved
      simplicity posture "{simplicity_description}": delete unused parameters,
      thin re-export shims, defensive catch-alls around already-handled
      failures, near-identical helpers collapsible into one, signature-restating
      docstrings, single-caller config keys, and speculative abstractions with
      no second implementation. Do NOT delete a guard that sits at a real I/O /
      external-input boundary (an unguarded-parse fix, an isinstance type-guard
      on externally-sourced data, an envelope on a network/filesystem boundary):
      required real-boundary error handling is NOT speculative defensive
      complexity — see the required-vs-speculative carve-out in
      ref-code-quality standards/code-organization.md #minimum-viable-code.
      Do NOT delete a line this run's review process already committed to — a
      guard or branch added earlier in THIS finalize pass to answer a review
      comment is a decision, not surplus structure. The deterministic check in
      Step 3b catches what slips past this instruction, so a deletion you are
      unsure about is better left and reported as a finding.
      Apply edits directly to the worktree via Edit.
      Coverage depth (from the resolved coverage instruction "{cov_instruction}"):
      at T1/T2/inherit, review each anti-pattern at face value (today's behavior);
      at T3+, trace each deletion candidate's callers and cross-references before
      deleting it. inherit/inherit reproduces today's face-value review.
      When a deletion would change a public/protected element or could plausibly
      serve an imminent requirement, leave it and record it as a finding instead
      of editing. Return TOON with status, findings[] (file/line/anti_pattern/
      action), and applied_edits count.

    WORKTREE: {worktree_path}
```

Parse the returned TOON: `findings[]` and `applied_edits`.

### Step 3b: Reconcile against the run's review commitments

**A line the review process committed to earlier in THIS run must not be deleted silently.**

This step and `plan-marshall:automatic-review` (`order: 30`) run inside one finalize pass, and this step declares `head_dependent: true` — so a loop-back fix commit answering a review comment advances HEAD and **re-fires this sweep over the very lines that fix produced**. A guard added because a reviewer asked for it is indistinguishable from surplus structure to a pass that never saw the review, and the dispatcher's commit instrumentation (Step 4) then commits the deletion and the `push` barrier ships it. The review decision is reversed inside the run that made it, with no record anywhere.

Run the reconciliation seam over this step's OWN edits, **before** marking the step done — so the conflict is surfaced while the edits are still uncommitted and reversible:

```bash
mkdir -p {worktree_path}/.plan/temp
```

```bash
git -C {worktree_path} diff > {worktree_path}/.plan/temp/simplify-pass.diff
```

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_commitments reconcile \
  --plan-id {plan_id} --diff-file {worktree_path}/.plan/temp/simplify-pass.diff
```

The diff goes under `{worktree_path}/.plan/temp/` — the project's temp location, and git-ignored so it can never reach the plan's footprint or a commit. **Do not write it under `{worktree_path}/.git/`**: plan-marshall materialises `{worktree_path}` with `git worktree add`, where `.git` is a pointer **file** rather than a directory, so the redirect fails with *Not a directory* and the whole reconciliation is skipped in exactly the mode finalize normally runs in. See [`../SKILL.md` § Canonical invocations → `review_commitments reconcile`](../SKILL.md#review_commitments--reconcile) for the argument surface and the fail-closed states.

Branch on the returned `verdict`:

| `verdict` | Action |
|-----------|--------|
| `clear` | No deletion touched a committed line. Proceed to Step 4 unchanged. |
| `conflict` | For each `conflicts[]` record, **revert that deletion in the worktree** (restore the removed lines via `Edit`) and record the conflict as a `findings[]` entry with `anti_pattern: review_commitment_conflict` and an `action` naming the `finding_id` whose commitment it would have reversed. Then proceed to Step 4. |
| `status: error` (no `verdict` field) | An UNKNOWN verdict, never a clear pass. Emit one `[WARNING]` naming the error, revert nothing, and record `review_commitment_reconciliation: unknown` in the returned `findings[]` so the un-run check is legible rather than inferred from its absence. |

**The seam reports; this step decides.** `review_commitments` carries `gates_merge: false` and `proves: removal_conflict_only`, so a conflict is never a merge verdict and never halts the phase — the contract the deliverable asks for is that a committed line either **survives** the pass or its removal is **visible as a conflict**, never that a removal is impossible. Reverting is this step's disposition of that report, chosen because a simplification is by construction optional while a review decision is not: when the two disagree, the cheap side yields and the disagreement is recorded for a human to overturn if the reverter was wrong.

Include the reverted count in the `display_detail` and the return TOON so a run that hit conflicts is distinguishable from one that had none.

### Step 4: Capture HEAD, mark step done, and return commit_message

The simplification edits are applied directly to the worktree in Step 3. This step does NOT commit them — the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits any `mutates_source: true` step's output after it records `done`, using the `commit_message` this step returns. There is no hand-rolled self-commit and no `applied_edits` branch.

Capture the live HEAD for the HEAD-dependency contract:

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

**Detail variant — a review commitment was reverted (Step 3b `conflict`).** When Step 3b reverted at least one deletion, the default detail reports only the surviving edits and is silent on the fact that the pass tried to reverse a review decision. Use the variant below instead, so the conflict is legible in the step record rather than only in the return TOON:

```text
--display-detail "Simplify: {applied_edits} edits, {reverted_count} review-conflict reverts"
```

Size any further variant against its **worst-case placeholder expansion**, never its literal form — the `display_detail` ceiling is owned by [`external-step-contract.md`](external-step-contract.md) § "Required termination" (read the number there, do not restate it here).

**Record before returning (binding).** The `mark-step-done` call above MUST complete BEFORE the return TOON below is composed — it is the step's terminal action, never a trailing formality after the payload is assembled. Composing and emitting the return TOON without having landed that record is a **contract violation**, not a cosmetic omission: the dispatcher's post-dispatch completion guard (`phase-6-finalize/SKILL.md` Step 3 item 5d) asserts the record via `assert-step-recorded --require-terminal`, raises `step_record_missing` attributed to this step, and halts the phase. A `status: done` payload is NOT a substitute for the record — the guard reads `status.metadata.phase_steps`, not the return. The governing invariant for every dispatched leaf is [`ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) § the record-before-return corollary.

Return a `commit_message` element in this step's return TOON so the dispatcher's instrumentation uses it when committing the applied edits (when no edits were applied the porcelain check is empty and the dispatcher commits nothing, so the returned message is simply unused):

```toon
status: done
display_detail: "{the Branch A string, or the review-conflict variant above}"
reverted_count: {number of deletions Step 3b reverted — 0 on a clear reconciliation}
commit_message: "chore(simplify): collapse accidental complexity in {plan_id}"
```

`reverted_count` is emitted UNCONDITIONALLY, `0` included. A field present only when non-zero makes "no conflicts" and "the reconciliation never ran" the same absence, which is the distinction Step 3b's `status: error` branch exists to preserve.

## Error Handling

| Scenario | Action |
|----------|--------|
| Live footprint empty (`compute-footprint` returns no `files`) | Mark `done` with `display_detail "Simplify: no changeset"` — nothing to review |
| `simplicity` field absent | Default to the `lean` posture description and proceed |
| Dispatched agent returns an error TOON | Mark `failed` with the agent's error in `display_detail`; finalize halts per the dispatcher's error handling |
| `review_commitments reconcile` returns `status: error` | UNKNOWN verdict, never a clear pass. Log one `[WARNING]`, revert nothing, and record `review_commitment_reconciliation: unknown` in `findings[]` (Step 3b). Do NOT mark the step `failed` — the reconciliation is a report, not a gate |

## Related

- [../../ref-code-quality/standards/code-organization.md](../../ref-code-quality/standards/code-organization.md) — § `#minimum-viable-code` (D1): the seven anti-patterns the review deletes
- [../../persona-plan-marshall-agent/standards/agent-behavior-rules.md](../../persona-plan-marshall-agent/standards/agent-behavior-rules.md) — Principle 7 (D2): "Implement the Minimum, Not the Maximum"
- [../../manage-execution-manifest/standards/decision-rules.md](../../manage-execution-manifest/standards/decision-rules.md) — the composition rule that gates this step into `phase_6.steps`
- [../SKILL.md](../SKILL.md) § Canonical invocations → `review_commitments reconcile` — the same-run reconciliation seam Step 3b consults
- [../../automatic-review/standards/bot-participation-contract.md](../../automatic-review/standards/bot-participation-contract.md) — the review side of the same run, whose finding dispositions Step 3b reads as commitments
- [../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md](../../../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md) — the static `SIMPLICITY_*` rules this step's cognitive pass complements
