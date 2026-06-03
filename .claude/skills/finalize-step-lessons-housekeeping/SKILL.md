---
name: finalize-step-lessons-housekeeping
description: Finalize-phase wrapper that reconciles the just-finished plan's outcome against the lessons-learned corpus, removing fully-covered lessons and trimming partially-covered ones
user-invocable: false
allowed-tools: Bash, Read, Edit
order: 996
---

# Finalize Step: lessons-housekeeping

## Purpose

Perform lessons-learned housekeeping after a plan finishes. Reason from the just-completed plan's outcome (what it changed, what it codified, which failure modes it eliminated) about the standing lessons-learned corpus, then:

- **Remove** lessons the plan made wholly redundant — the guarded failure mode can no longer occur, or the recommended practice is now codified/enforced.
- **Trim** lessons the plan made only partly redundant, removing the now-covered portion while preserving the still-relevant guidance.
- **Retain** everything else, biasing toward retention whenever coverage is ambiguous.

Every change — removal, adaptation, or deliberate retain — is recorded to the decision log so the housekeeping is fully auditable.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-lessons-housekeeping` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to read the plan outcome and to scope decision-log entries)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **after** `plan-marshall:plan-retrospective` (order 995) — the retrospective produces the `quality-verification-report.md` this step reads — and **before** `default:finalize-step-print-phase-breakdown` (order 997).

## Direct-file-access allowance

This step is granted **direct `Read`/`Edit` access to `.plan/local/lessons-learned/**`** as a documented exception to the CLAUDE.md "`.plan/` access: scripts only" hard rule. That rule itself carves out the exception: *"Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it."* This section is that explicit documentation.

The exception is deliberately narrow:

- **Removals still route through `manage-lessons remove`** — never delete a lesson `.md` file directly. The script writes an auditable tombstone, which the direct-`Edit` path cannot.
- **Only the partial-coverage *adaptation* edits touch lesson `.md` bodies directly** — trimming the now-covered portion of a lesson is a surgical body edit that no `manage-lessons` verb expresses, so it is performed with `Edit` against `.plan/local/lessons-learned/{id}.md`.
- **Reads** of lesson bodies for classification go through `manage-lessons list --full` / `manage-lessons get` where possible; direct `Read` of a lesson `.md` is permitted only to inspect the exact body region an adaptation will trim.

## Ordering

The canonical phase-6-finalize chain (resolved by each step's `order:` frontmatter):

```
default:record-metrics                          (990)
plan-marshall:plan-retrospective                (995)
project:finalize-step-lessons-housekeeping      (996)   <-- this step
default:finalize-step-print-phase-breakdown     (997)
default:archive-plan                            (1000)
```

## Workflow

### Step 1: Read the just-finished plan's outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field modified_files
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Read the retrospective's quality-verification report (written by `plan-marshall:plan-retrospective`, order 995):

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file quality-verification-report.md
```

Together these establish what the plan changed (modified files), why (the request), and the verified outcome — the basis for coverage classification.

### Step 2: Enumerate the lessons corpus

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

**Empty-corpus skip-clean exit**: if zero lessons exist, log and record the step as done, then return:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-lessons-housekeeping) 0 lessons — nothing to reconcile"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "0 lessons — nothing to reconcile"
```

### Step 3: Classify each lesson's coverage against the plan outcome

For each lesson, classify it against the plan outcome using a **conservative subsumption bar**:

- **Completely covered** — requires that the lesson's guarded failure mode can no longer occur, **OR** its recommended practice is now codified/enforced by this plan. Nothing weaker qualifies.
- **Partially covered** — the plan eliminated or codified *part* of what the lesson guards, but a residual concern remains.
- **Ambiguous / none** — anything that does not clearly meet the bar above. **Leave untouched (bias to retain)** and log the no-action decision.

When in doubt, retain. The cost of keeping a stale lesson is far lower than the cost of deleting a still-load-bearing one.

### Step 4: Remove completely-covered lessons

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id {id} --force --reason "{why} (plan {plan_id})"
```

This writes a tombstone — the removal stays auditable. The owning `{plan_id}` is folded into the `--reason` text (the `remove` verb has no separate plan flag) and is also captured by the Step 6 decision-log entry.

### Step 5: Trim partially-covered lessons

Use the `Edit` tool directly against the lesson body:

```
Edit: .plan/local/lessons-learned/{id}.md
```

Trim **only** the now-covered portion. Preserve the `key=value` header block at the top of the file verbatim, and preserve every still-relevant section of the body.

### Step 6: Log every change

Record a decision-log entry for **every** removal, **every** adaptation, **and every** deliberate retain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(project:finalize-step-lessons-housekeeping) {removed|adapted|retained} {id}: {reason}"
```

### Step 7: Record the step outcome

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-lessons-housekeeping --outcome done \
  --display-detail "{N} removed, {M} adapted, {K} retained"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Empty lessons corpus | Skip-clean exit — record `mark-step-done --outcome done --display-detail "0 lessons — nothing to reconcile"` so the `phase_steps_complete` handshake counts the step as done |
| Coverage ambiguous | Retain the lesson untouched (bias to retain) and log the no-action decision via `manage-logging decision` |
| `manage-lessons remove` failure on one lesson | Non-fatal — log the failure, leave that lesson in place, and continue with the remaining lessons. Housekeeping must never block finalize. |
| Adaptation `Edit` failure on one lesson | Non-fatal — log the failure, leave that lesson untouched, and continue. |
| Missing `quality-verification-report.md` | Non-fatal — proceed using `request.md` + `modified_files` alone; log that the retrospective report was unavailable |
| Step completes | Record `mark-step-done --outcome done --display-detail "{N} removed, {M} adapted, {K} retained"` |

The step's posture is **non-fatal throughout**: finalize must never abort because lessons housekeeping hit a snag on an individual lesson.

## Related

- [.claude/skills/finalize-step-plugin-doctor/SKILL.md](../finalize-step-plugin-doctor/SKILL.md) — sibling project-local finalize step (reads references.json, acts per-item)
- [.claude/skills/finalize-step-deploy-target/SKILL.md](../finalize-step-deploy-target/SKILL.md) — sibling project-local finalize step
- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling project-local finalize step
- `plan-marshall:manage-lessons` — lesson corpus management (list, remove with tombstone)
- `plan-marshall:manage-logging` — decision-log infrastructure used to audit every change
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
