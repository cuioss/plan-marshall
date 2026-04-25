---
name: recipe-lesson-cleanup
description: Domain-invariant recipe for converting a single lesson-learned into a slim, deterministic plan with surgical-style cascades
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Lesson Cleanup

Generic, domain-invariant recipe for turning a single lesson-learned into a deterministic plan that fixes exactly what the lesson directs and nothing else. Mirrors `recipe-refactor-to-profile-standards` in shape: phase-3-outline loads this skill and walks its workflow once, emitting one deliverable per lesson directive. The recipe forces surgical scope so the manifest composer's `surgical+tech_debt` / `surgical+bug_fix` / `surgical+enhancement` cascade rules collapse Phase 5 verification and Phase 6 finalize down to the minimum safe set.

**No separate analysis step** — the lesson body itself is the deliverable source. Each directive in the lesson maps directly to one deliverable; the change_type is derived deterministically from the lesson kind. Q-Gate is skipped because the recipe path is its own gate.

## Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Enforcement

**Execution mode**: Walk the four phase-aligned steps below in order. Each step has a single explicit job — no improvisation, no extra discovery passes.

**Prohibited actions:**
- Never invent extra deliverables beyond the lesson directives. The lesson body is the source of truth — if it lists three directives, the outline has three deliverables, full stop.
- Never set `scope_estimate` to anything other than `surgical`. This recipe exists specifically to drive the surgical cascade rules in the manifest composer.
- Never call Q-Gate validation from within this recipe. The recipe path bypasses Q-Gate by design (see phase-3-outline § Recipe Path).
- Never override the `change_type` derived from lesson kind. The mapping (`bug → bug_fix`, `improvement → enhancement`, `anti-pattern → tech_debt`) is fixed.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline.
- One deliverable per lesson directive — never merge or split.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `lesson_id` | string | Yes | Lesson identifier (e.g., `2025-12-02-001`) |

**Note**: Unlike `recipe-refactor-to-profile-standards`, this recipe takes no `recipe_domain`, `recipe_profile`, or `recipe_package_source` parameters. The lesson body — already moved into the plan directory by `phase-1-init` Step 5b — is the sole input.

---

## Step 1: Resolve Lesson Body and Kind (Phase 2 surrogate)

The recipe replaces the iterative `phase-2-refine` loop. Confidence is forced to 100 because the lesson is the contract.

Read the lesson document copied into the plan directory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file lesson-{lesson_id}.md
```

Parse the lesson frontmatter to extract:

- `kind` (one of `bug`, `improvement`, `anti-pattern`)
- `title`
- `directives[]` — the actionable items declared in the lesson body (one per `## Directive` heading, or one per bullet under `## Actions`, depending on lesson layout)

Persist the forced confidence to the plan refine config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field confidence --value 100 --trace-plan-id {plan_id}
```

Log the recipe-driven confidence override:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-lesson-cleanup) Forced confidence=100 (recipe path: lesson body is the contract)"
```

---

## Step 2: Map Lesson Kind to change_type

Apply the fixed mapping:

| Lesson kind | change_type |
|-------------|-------------|
| `bug` | `bug_fix` |
| `improvement` | `enhancement` |
| `anti-pattern` | `tech_debt` |

If the lesson kind is anything else, abort with an explicit error — do not guess. The mapping is the contract that drives the manifest composer's cascade selection downstream.

```toon
status: error
error: unknown_lesson_kind
message: "Lesson kind '{kind}' is not mapped — supported: bug, improvement, anti-pattern"
recovery: "Tag the lesson with one of the supported kinds, then re-run."
```

---

## Step 3: Compose Deterministic Outline (Phase 3 surrogate)

For each lesson directive, emit one deliverable. The outline is purely structural — no LLM reasoning, no Q-Gate, no decomposition pass.

**3a. Read the deliverable template:**

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**3b. Resolve the target outline path:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**3c. Compose the document.** For every directive in the lesson:

- **Title**: `Lesson cleanup: {directive_title}`
- **Description**: The directive body verbatim from the lesson
- **Metadata**:
  - `change_type`: derived in Step 2
  - `execution_mode`: `automated`
  - `domain`: from the lesson's `component` field (fall back to `plan-marshall-plugin-dev` for plugin-bundle lessons)
  - `scope_estimate`: `surgical` — REQUIRED. This drives the `surgical+{change_type}` cascade rule in the manifest composer.
- **Skills**: derived from the lesson's `related` field (skill notations) — passed verbatim to the composed deliverable.
- **Affected files**: from the lesson's `affected_files` field if present; otherwise empty (the executor task will discover them from the directive body).

The top-level outline metadata MUST also include `scope_estimate: surgical` so phase-3-outline writes the value into status metadata for the manifest composer to read.

**3d. Write the outline** with the `Write` tool to `{resolved_path}`. Sections in order:

- `# Solution: Lesson Cleanup — {lesson_title}` header with `plan_id`, `lesson_id`, `kind`, `change_type`, `scope_estimate: surgical` metadata
- `## Summary` — one sentence echoing the lesson title and directive count (e.g., "Apply the 3 directives from lesson {lesson_id} as surgical changes.")
- `## Overview` — list of derived skills and the lesson kind → change_type mapping
- `## Deliverables` — one deliverable per directive, using the template structure from 3a

**3e. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

**3f. Skip Q-Gate** — the recipe path is its own gate. Log the bypass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-lesson-cleanup) Skipped Q-Gate validation (recipe path)"
```

---

## Step 4: Hand Off to Phase 4 (Manifest Composition)

Phase-4-plan reads the outline, sees `scope_estimate: surgical`, and applies the surgical cascade rules per change_type:

- `surgical + bug_fix` → Phase 5 keeps `quality-gate` only; Phase 6 keeps `commit-push`, `create-pr`, `lessons-capture` only.
- `surgical + enhancement` → Phase 5 keeps `quality-gate` only; Phase 6 keeps `commit-push`, `create-pr`, `lessons-capture` only.
- `surgical + tech_debt` → Phase 5 keeps `quality-gate` only; Phase 6 keeps `commit-push`, `create-pr`, `lessons-capture` only.

In all three surgical cases, the composer drops `automated-review`, `sonar-roundtrip`, and `knowledge-capture` from Phase 6, matching the success criteria for this recipe.

This recipe does not invoke phase-4-plan directly — phase-3-outline returns control to the orchestrator, which advances to phase-4-plan as usual. The manifest composer reads `scope_estimate` from the outline metadata.

---

## Output

```toon
status: success
plan_id: {plan_id}
lesson_id: {lesson_id}
lesson_kind: {kind}
change_type: {derived}
scope_estimate: surgical
deliverables_count: {N}
outline_path: {resolved_path}
next_phase: 4-plan
```

---

## Related

- `plan-marshall:phase-1-init` Step 5b — Moves the lesson into the plan directory before this recipe runs.
- `plan-marshall:phase-3-outline` § Recipe Path — Loads this skill with the input parameters and skips Q-Gate accordingly.
- `plan-marshall:phase-4-plan` § Manifest Composition — Reads `scope_estimate=surgical` and applies cascade rules.
- `plan-marshall:recipe-refactor-to-profile-standards` — Sister recipe; same shape, different scope (codebase-wide tech-debt sweep vs. single-lesson surgical cleanup).
