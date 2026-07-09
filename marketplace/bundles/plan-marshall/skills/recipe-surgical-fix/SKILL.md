---
name: recipe-surgical-fix
description: Micro-lane recipe for a pre-diagnosed surgical fix — composes a deterministic surgical outline for a root-cause-known change bounded to a single module
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
lane:
  profile: minimal
  steps:
    automated-review: minimal
---

# Recipe: Surgical Fix

The micro-lane fast path for a **pre-diagnosed surgical fix** — a change whose root cause is already known, whose exact edit is already known, that touches ≤~2 files / ~50 LOC, and that carries no cross-module behavioral delta. This recipe is a `phase-3-outline` surrogate: it takes the pre-diagnosed request as its contract, composes a deterministic `scope_estimate: surgical` outline with no discovery pass beyond the named files, and hands off to `phase-4-plan`, whose `surgical + {change_type}` cascade collapses Phase 5 verification and Phase 6 finalize to the minimum safe set.

The recipe introduces **no new lane tier and no new dispatch machinery** — it is a *composition* of already-shipped parts. Its `lane:` seed recommends `profile: minimal` (every element at the minimal floor) with one force-keep — `automated-review` held at `minimal` so structural review stays in the loop even on the leanest posture. The seed is the lowest-precedence lane input (recipe seed < operator posture < coverage-cell floor); the operator posture always overrides it. The `minimal` floor semantics and the adversarial-review class are owned by [`../extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md) — this recipe cross-references them rather than restating the lattice.

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

**Execution mode**: Walk the three phase-aligned steps below in order — resolve the pre-diagnosed inputs and verify surgical fit, compose the deterministic outline, hand off to Phase 4. Each step has a single explicit job — no improvisation, no extra discovery passes.

**Prohibited actions:**
- Never run a discovery pass beyond the affected files named in the pre-diagnosed request. The request IS the contract — this recipe does not re-derive scope, hunt for additional call sites, or expand the footprint.
- Never set `scope_estimate` to anything other than `surgical`. This recipe exists specifically to drive the `surgical + {change_type}` cascade rules in the manifest composer; a non-surgical request does not belong on this path.
- Never proceed when the fit gate (Step 1) fails. A request that crosses a module boundary, or whose fix is not already diagnosed, MUST abort with the redirect error — the recipe never silently widens scope to make a non-surgical request fit.
- Never call Q-Gate validation from within this recipe. The recipe path is its own gate (see `phase-3-outline` § Recipe Path).

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- One deliverable per affected file, or a single deliverable covering the whole surgical change when it is one cohesive edit — never invent deliverables beyond the pre-diagnosed change.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier. The pre-diagnosed request — root cause, exact change, affected files — is read from the plan's `request.md`, already populated by `phase-1-init` / `phase-2-refine`'s recipe shortcut (confidence forced to 100). |

**Note**: This recipe takes no `recipe_domain` / `recipe_profile` / `recipe_package_source` parameters. The pre-diagnosed `request.md` is the sole input; the affected module is derived from the named files in Step 1.

## When to use it — and when NOT to

Use the surgical-fix micro-lane when ALL of the following hold:

- The **root cause is already known** and the **exact change is already diagnosed** — this is not an investigation.
- The change touches **≤~2 files / ~50 LOC**.
- The change carries **no cross-module behavioral delta** — every affected file resolves to a single module, and no consumer contract changes.

Do **NOT** use it — route to the standard planning path instead — when ANY of the following hold:

- The fix **crosses a module boundary**, or changes a contract other consumers depend on.
- The fix is **not already diagnosed** (the request describes a symptom to investigate, not a change to apply).
- The change is broad, fans out across many files, or needs a discovery pass to bound its scope.

The Step 1 fit gate enforces this contract deterministically; a request that fails it aborts with a redirect rather than being force-fit onto the micro-lane.

---

## Step 1: Resolve the Pre-Diagnosed Inputs and Verify Surgical Fit (Phase 2 surrogate)

The recipe replaces the iterative `phase-2-refine` loop — confidence is forced to 100 because the pre-diagnosed request is the contract.

**1a. Read the pre-diagnosed request** copied into the plan directory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request path --plan-id {plan_id}
```

Read the resolved path with the `Read` tool and extract the three pre-diagnosed inputs:

- `root_cause` — the diagnosed cause of the defect / the reason for the change.
- `exact_change` — the specific edit to apply (the "what to change" the request already names).
- `affected_files[]` — the explicit file paths the change touches (≤~2 expected).

**1b. Verify surgical fit (the gate).** Resolve the owning module of every affected file:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  which-module --path {affected_file}
```

Collect the distinct module values. The request passes the fit gate only when ALL hold:

- Every affected file resolves to the **same single module** (no cross-module boundary).
- The affected-file count is **≤~2** and the change is a single cohesive edit (no fan-out).
- The request names a **concrete diagnosed change** (root cause + exact change are both present), not an investigation.

**1c. Abort on fit failure.** When the gate fails, do NOT compose an outline and do NOT widen scope to force a fit. Return the redirect error and stop:

```toon
status: error
error: not_surgical
plan_id: {plan_id}
reason: "{cross_module | not_pre_diagnosed | too_broad}"
message: "Request does not fit the surgical micro-lane: {specific reason}."
recovery: "Re-run without recipe=surgical-fix to route through the standard planning path (phase-2-refine → phase-3-outline)."
```

Log the abort so the scope decision is auditable:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-surgical-fix:fit-gate) Aborted — request does not fit the surgical class: {specific reason}"
```

When the gate passes, record the resolved module as `{module}` and continue to Step 2.

---

## Step 2: Compose the Deterministic Surgical Outline (Phase 3 surrogate)

Emit one deliverable per affected file (or a single deliverable when the change is one cohesive edit across the ≤~2 files). The outline is purely structural — no LLM decomposition, no Q-Gate.

**2a. Read the deliverable template:**

```text
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**2b. Resolve the target outline path:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**2c. Resolve the verification command** for the affected module (used as each deliverable's Verification Command):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --module {module} --audit-plan-id {plan_id}
```

**2d. Compose the document.** For the surgical change, emit deliverable(s) using the template structure from 2a:

- **Title**: `Surgical fix: {short change summary}`
- **Description**: the `exact_change` from the request, verbatim.
- **Metadata**:
  - `change_type`: the recipe default `bug_fix`, unless the request explicitly declares a different concrete change_type.
  - `execution_mode`: `automated`
  - `domain`: the affected module's domain.
  - `module`: `{module}` resolved in Step 1.
  - `scope_estimate`: `surgical` — REQUIRED. This drives the `surgical + {change_type}` cascade rule in the manifest composer.
- **Affected files**: the `affected_files[]` from the request, each with its `(intent)` marker (`write-replace` / `write-new`).
- **Verification**: the `executable` resolved in 2c, with a criteria line asserting the diagnosed change applied cleanly with no regressions.

The top-level outline metadata MUST also carry `scope_estimate: surgical` so `phase-3-outline` writes it into status metadata for the manifest composer.

**2e. Write the outline** with the `Write` tool to `{resolved_path}`. Sections in order:

- `# Solution: Surgical Fix — {short change summary}` header with `plan_id`, `change_type`, `scope_estimate: surgical` metadata.
- `## Summary` — one sentence naming the diagnosed change and affected file count.
- `## Overview` — the root cause and the exact change, one short paragraph.
- `## Deliverables` — the deliverable(s) from 2d, using the template structure.

**2f. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

**2g. Skip Q-Gate** — the recipe path is its own gate. Log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-surgical-fix) Skipped Q-Gate validation (recipe path)"
```

---

## Step 3: Hand Off to Phase 4 (Surgical Cascade)

Phase-4-plan reads the outline, sees `scope_estimate: surgical`, and composes the execution manifest through two independent passes. (1) The `surgical + {change_type}` change-type cascade sets `phase_5.verification_steps` to the role-intersected core (for `surgical + bug_fix`, `{quality-gate, module-tests}`) and trims the `phase_6` candidate set (dropping `ci-wait`) — per `manage-execution-manifest/standards/decision-rules.md` Row 5, this cascade NEVER silently suppresses `sonar-roundtrip` / `automated-review`. (2) The separate lane-resolution pass applies the recipe's `minimal` posture, and it is that pass which drops the `prunable` / `tier:auto` finalize elements such as `sonar-roundtrip` (per `ext-point-lane-element.md`). The recipe's `lane:` seed force-keeps `automated-review` in the loop so structural review still runs even on the minimal posture.

This recipe does not invoke phase-4-plan directly — `phase-3-outline` returns control to the orchestrator, which advances to phase-4-plan as usual. The manifest composer reads `scope_estimate` from the outline metadata.

---

## Output

```toon
status: success
plan_id: {plan_id}
change_type: {derived}
scope_estimate: surgical
module: {module}
deliverables_count: {N}
outline_path: {resolved_path}
next_phase: 4-plan
```

On fit-gate failure, the recipe returns the `not_surgical` error TOON from Step 1c instead.

---

## Related

- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements, and the recipe `lane:` seed contract.
- `plan-marshall:extension-api` `standards/ext-point-lane-element.md` — the `minimal` floor lattice and the `adversarial` class that governs `automated-review`; the seed cross-references it rather than restating it.
- `plan-marshall:phase-3-outline` § Recipe Path — loads this skill with the input parameters and skips Q-Gate accordingly.
- `plan-marshall:phase-4-plan` § Manifest Composition — reads `scope_estimate=surgical` and applies the cascade rules.
- `plan-marshall:recipe-lesson-cleanup` — sister deterministic-outline recipe; same surgical-scope shape, different source (a single lesson vs. a pre-diagnosed request).
