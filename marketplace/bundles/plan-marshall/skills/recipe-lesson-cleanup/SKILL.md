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

### Step 1b: Premise Verification

Runs after the lesson body has been read and BEFORE Step 2 maps the lesson kind to a `change_type`. Without this gate, the recipe will faithfully translate stale directives into a deliverable, then phase-4-plan will faithfully translate them into tasks, and the executor will fight the live tree to apply prescriptions that no longer match it. The gate exists to catch the staleness once, at the cheapest possible point, before scope is locked.

**Authoritative heuristics**: This sub-step deliberately does NOT redefine the extraction or verification heuristics. They live in `marketplace/bundles/plan-marshall/skills/phase-1-init/standards/lesson-source-premise-check.md`, which is the canonical source for file-path / function-name / CLI-shape / anti-pattern matching, the verification-helper table, and the per-kind "stale when" rules. Read that document and apply its passes verbatim to the lesson body resolved in Step 1. Re-implementing the heuristics here would create a second source of truth that drifts out of sync with phase-1-init.

**Sub-step a — Enumerate concrete factual assertions.** Apply the extraction passes from the standard to the lesson body, producing a working set of `(reference, kind)` tuples covering every concrete factual assertion: file paths, function/method/subcommand names, CLI invocation shapes (`python3 .plan/execute-script.py {notation} {subcommand}`), and anti-pattern signatures. Each tuple is tied to one or more directives in the lesson — record the back-link so dropping the assertion can also drop the corresponding directive. Prose claims that do not resolve to a checkable reference are out of scope for the gate; they remain in the directive set unchanged.

**Sub-step b — Quick-check each assertion against the live tree.** Apply the verification-helper table from `marketplace/bundles/plan-marshall/skills/phase-1-init/standards/lesson-source-premise-check.md` (the canonical source) — do not restate it here.

Record each verification as `(reference, kind, status, evidence)` where `status` is `valid` or `stale`. Do not abort on the first stale match — the gate needs the full picture to decide whether to drop selectively or abort wholesale.

**Sub-step c — Drop stale directives from scope before Step 3.** For every assertion marked `stale`, follow the recorded back-link and drop the directive(s) it underpinned from the working set. The dropped directives MUST NOT appear as deliverables in Step 3; the residual (valid) directive set is the input phase-3-outline composes from. A directive that depends on multiple assertions is dropped if ANY of its assertions is stale — the recipe never tries to "rescue" a directive by ignoring the broken half.

**Sub-step d — Record each dropped scope item via the decision log.** For every dropped directive, emit one decision-log entry with the prefix `(plan-marshall:recipe-lesson-cleanup:premise-check)` so reviewers can audit the scope reduction:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-lesson-cleanup:premise-check) Dropped directive '{directive_title}' — stale assertion: {reference} ({evidence})"
```

When a directive is underpinned by multiple stale assertions, list them comma-separated in the `{evidence}` segment. Kept directives are NOT logged individually — only drops, since drops shrink scope and require audit visibility.

**Abort condition — lesson fully obsolete.** When ALL directives in the lesson have been dropped (the residual set is empty), the recipe MUST abort with an explicit error rather than silently emit an empty outline. Return:

```toon
status: error
error: lesson_fully_obsolete
plan_id: {plan_id}
lesson_id: {lesson_id}
message: "Every directive in lesson '{lesson_id}' was dropped during premise verification — the lesson no longer matches the live tree."
recovery: "Close the lesson via 'python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons delete --lesson-id {lesson_id}', or refine it manually before re-running the recipe."
```

Do not call `manage-solution-outline write`, do not transition phase, do not emit a no-op outline. The recipe is the gate — an empty residual scope means the gate fired.

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

## Step 2b: Verify Proposed Fix Against Current Code (phase-2-refine Step 3c surrogate)

Runs after the lesson kind is mapped (Step 2) and BEFORE Step 3 composes the deterministic outline. This step closes a structural gap: lesson-sourced plans set `source: lesson` in `request.md`, which makes phase-2-refine take its **Recipe Shortcut** (skipping the iterative refine loop and forcing confidence to 100). That shortcut bypasses phase-2-refine **Step 3c — Proposed-Fix Verification**, so the lesson's `## Recommended Fix` (or equivalent "Recommended Follow-Up" / "Solution / Action" / "Application" section) would otherwise flow straight into Step 3's deliverable composition without ever being challenged against the current code path.

This step is the recipe's surrogate for that bypassed verification. It runs before **any** `request.md` Clarifications block update and before any `solution_outline.md` content is composed, so divergences are recorded into the plan inputs rather than retro-fitted afterwards.

**Authoritative patterns**: This sub-step deliberately does NOT redefine the proposed-fix extraction, probe construction, or result-handling heuristics. The reusable patterns live in `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/proposed-fix-verification.md`, which is the canonical source for the trigger condition, extraction fields, probe budget, and Valid/Insufficient/Inconclusive result table. Read that document and apply its passes against the current lesson body.

The recipe layer adds one constraint on top of the canonical patterns: the lesson's `## Recommended Fix` (or equivalent) is a **starting hypothesis only** — never authoritative implementation guidance. The recipe re-derives the minimal correct change from disk; it does not transcribe the recommendation.

**Sub-step a — Treat the lesson's recommended fix as a hypothesis.** Locate the lesson's "what to do" section. Common headings include `## Recommended Fix`, `## Recommended Follow-Up`, `## Solution / Action`, and `## Application`. Capture the recommendation verbatim as `hypothesis_fix` for each directive that survived Step 1b. A lesson with no such section skips this sub-step entirely — there is no hypothesis to challenge, and the directives stand as written.

**Sub-step b — Re-derive the minimal correct change from the live tree.** For each surviving directive, read the surrounding code path on disk using the architecture inventory first — `architecture files --module X` to enumerate the module's components, `architecture which-module --path P` and `architecture find --pattern P` for module-spanning lookups — and fall back to `Glob`, `Grep`, and `Read` only for sub-module component lookup, content searches inside an already-known file, or when the architecture verb returns elision:

- Resolve every component the directive touches (skill notations, file paths, function names, scripts) in the live worktree.
- Trace the actual current behavior — what the code does today, what it calls, what its callers expect.
- Derive the **minimal correct change** that addresses the directive's symptom against this current state. The minimal change is the smallest edit that makes the symptom stop manifesting; it is NOT the largest edit that the recommendation suggests.

**Sub-step c — Compare hypothesis against verified-correct minimal change and note divergences.** For each directive with a `hypothesis_fix`, compare it against the minimal correct change derived in sub-step b. Classify each comparison into one of four divergence categories:

| Category | Meaning |
|----------|---------|
| `convergent` | Hypothesis matches the minimal correct change — no action needed |
| `over-broad` | Hypothesis prescribes more than the minimal change requires (e.g., touches unrelated files, adds defensive code beyond the symptom) |
| `redundant` | Part or all of the hypothesis is already satisfied by code that landed elsewhere after the lesson was authored |
| `mis-targeted` | Hypothesis addresses a contract / API / pattern that no longer exists, or addresses the wrong layer |

Record each non-convergent comparison as `(directive, category, hypothesis_summary, verified_change_summary, evidence)` for use in sub-step d.

**Sub-step d — When verified-correct fix diverges, update the plan inputs.** For each directive in `over-broad`, `redundant`, or `mis-targeted`:

1. Update the plan's `request.md` Clarifications block with the verified-correct fix and the rationale for divergence. The Clarifications block is the canonical place phase-3-outline reads for refined intent — by writing here, the recipe ensures Step 3's deliverable composition sees the verified version, not the hypothesis.
2. Record the divergence so it surfaces in the eventual commit message or PR body. Both `phase-6-finalize:commit-push` and `phase-6-finalize:create-pr` consume the decision log and the request.md Clarifications block when composing message bodies — the entry below feeds both.

Resolve the canonical `request.md` path, then update `## Clarifications` and `## Clarified Request` directly via Edit/Write — the same three-step path-allocate flow phase-2-refine uses:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request path --plan-id {plan_id}
```

Use `Edit` (or `Write`, when no file exists yet) against the resolved path to append a Clarifications entry per divergent directive in this shape:

```
- Directive: {directive_title}
  Hypothesis: {hypothesis_summary}
  Verified fix: {verified_change_summary}
  Rationale: {category} — {evidence}
```

When all divergences are written, mark the request clarified so phase-3-outline picks up the refined intent:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request mark-clarified --plan-id {plan_id}
```

Then emit a decision-log entry per divergence so reviewers can audit the scope adjustment:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:recipe-lesson-cleanup:fix-verification) Diverged from hypothesis for '{directive_title}' — {category}: hypothesis was '{hypothesis_summary}', verified change is '{verified_change_summary}'"
```

`convergent` directives are NOT logged individually — only divergences, since divergences alter scope and require audit visibility.

**Sub-step e — Log the verification summary.** Emit one work.log entry summarizing the pass:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[RECIPE:2b] (plan-marshall:recipe-lesson-cleanup) Proposed-fix verification: {N} directives probed, {C} convergent, {D} divergent ({over_broad} over-broad, {redundant} redundant, {mis_targeted} mis-targeted)"
```

**Hand-off to Step 3.** Step 3 composes deliverables from the **verified directive set** — i.e., the residual directives from Step 1b with each `over-broad` / `redundant` / `mis-targeted` directive replaced by its verified-correct minimal change. The hypothesis text is not used directly. Step 3 reads the updated Clarifications block and composes deliverables from there.

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
- `plan-marshall:phase-2-refine` Step 3c — Canonical proposed-fix verification, defined in `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/proposed-fix-verification.md`. Lesson-sourced plans (`source: lesson` in `request.md`) take phase-2-refine's Recipe Shortcut and bypass Step 3c, so this recipe's Step 2b is the surrogate that closes the gap.
- `plan-marshall:phase-3-outline` § Recipe Path — Loads this skill with the input parameters and skips Q-Gate accordingly.
- `plan-marshall:phase-4-plan` § Manifest Composition — Reads `scope_estimate=surgical` and applies cascade rules.
- `plan-marshall:recipe-refactor-to-profile-standards` — Sister recipe; same shape, different scope (codebase-wide tech-debt sweep vs. single-lesson surgical cleanup).
