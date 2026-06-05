---
name: recipe-generalization-sweep
description: Project-local audit recipe that sweeps the plan-marshall bundle for meta-project-specific leaks and emits remediation deliverables grouped by disposition
user-invocable: false
allowed-tools: Read, Write, Glob, Grep, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Bundle Generalization Sweep

Project-local audit recipe that sweeps the `plan-marshall` bundle (optionally all bundles) for implementations specific to *developing the meta-project itself* — "meta-leaks" — classifies each leak under a fixed **disposition vocabulary**, and emits a `solution_outline.md` whose deliverables carry out the remedies. Deliverables are grouped by disposition with a confirmation gate on destructive and contested calls.

Where `recipe-plugin-compliance` sweeps for plugin-architecture compliance and `recipe-plan-review` reviews a landed plan against its request, this recipe sweeps for *generalization* defects: bundle-shipped surfaces that only make sense when the working tree **is** the plan-marshall repo. The defect class is real — `recipe-marshal-json-config-audit` itself slipped into the bundle with a "domain-invariant" description despite being meta-only, and was caught only because its `recipe_domain` row was missing (the load-bearing discovery row). This recipe encodes the methodology so future meta-leaks are caught the same way without re-deriving the MOVE-signature, the disposition vocabulary, or the decision rules each time.

Like the sibling project-local recipes it is LLM-driven (no backing script for adjudication), with a deterministic candidate-surfacer used only as an *accelerator* — never the sole filter (Step 2). It is loaded by phase-3-outline's recipe path; it is not user-invocable.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |
| `recipe_domain` | `plan-marshall-plugin-dev` |
| `recipe_profile` | `implementation` |

The backticked recipe-domain row above is **MANDATORY** — `manage-config list-recipes` scans `.claude/skills/recipe-*/SKILL.md` for that backticked row, and **silently skips** any recipe whose Input-Parameters table lacks it. This was the exact defect that hid `recipe-marshal-json-config-audit`. Keep the backticked recipe_domain token confined to the table row only — the discovery scanner matches the last line bearing that literal, so repeating it in prose would shadow the table value.

There is no `recipe_scope` / `recipe_thoroughness` input — the cell is pinned (Step 0). The package-source parameter is omitted because the sweep audits a bundle surface rather than iterating packages. The recipe is plan-bound; it persists the resolved cell to `status.json` metadata.

## Enforcement

**Execution mode**: Deliverable-collection audit recipe — pin the coverage cell, enumerate the audit surface, full-read every skill to surface leaks, assign a disposition per leak, trace multi-site impact, gate destructive/contested calls, write the solution outline. Loaded by phase-3-outline's recipe path; not user-invocable.

**Prohibited actions:**
- Never raise an `AskUserQuestion` for the coverage cell — the cell is pinned `T5 / overall` (Step 0). The only `AskUserQuestion` this recipe drives is the Step 6 confirmation gate (DELETE / MOVE-vs-AGGREGATE / new-ext-point).
- Never use the deterministic candidate-surfacer (Grep of MOVE-signature markers) as the sole leak filter — the full-read of every skill is the floor; the grep is the net. A pure grep pass MISSES leaks with no literal marker (the adversarial lesson).
- Never adjudicate a leak by its `name` / `description` — judge by the body against MOVE-signature criteria A–E.
- Never restate the thoroughness ladders, the grade-to-the-floor rule, the coupling constraint, or the cell → instruction expansion table — cross-reference `dev-agent-behavior-rules/standards/thoroughness.md` and `coverage-gathering-contract.md`.
- Never emit a DELETE, a MOVE-vs-AGGREGATE fork, or a new-ext-point proposal as a deliverable without passing the Step 6 confirmation gate.
- Never access `.plan/` files directly — all access goes through `python3 .plan/execute-script.py` manage-* scripts.

**Constraints:**
- Strictly comply with all rules from `dev-agent-behavior-rules`, especially tool usage and workflow step discipline.
- The persisted cell is `coverage_thoroughness=T5`, `coverage_scope=overall`, plus the `coverage expand`-produced `coverage_instruction`, written to `status.json` metadata.
- Each collected deliverable records its `T5 × overall` cell for the floor-graded self-report and enumerates every multi-site consumer the disposition touches (callers, q-gate validators, `plugin.json`, tests, cross-refs).

## Workflow

### Step 0: Pin + expand + persist the coverage cell (NO gather)

The generalization sweep is exhaustive and adversarial by design — every skill must be read in full, candidates re-verified against disk (fabrication guard), and the leak list looped until dry. The recipe therefore **pins** the cell `thoroughness=T5, scope=overall` rather than gathering it:

- `scope=overall` — the entire `plan-marshall` bundle (optionally extended to all bundles).
- `thoroughness=T5` — exhaustive/adversarial depth: full-read every skill, re-verify each candidate against disk, loop until no new leaks surface.
- The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) is satisfied because `overall ≥ component`.

This recipe implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md)'s **consume** obligation but deliberately skips the **gather** (`AskUserQuestion`) step. Expand the pinned cell once and persist BOTH the identifier and the expanded instruction to `status.json` metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness T5 --scope overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value T5
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

Consume the **expanded instruction** (NOT the raw cell) in Steps 2–7 to govern review depth and breadth. Do NOT restate the `thoroughness.md` ladders or the contract's cell → instruction table here — cross-reference them. `coverage expand` enforces the coupling constraint; the pinned `T5 / overall` pair satisfies it by construction, so a violation here is a contract bug, not a re-gather case.

### Step 1: Enumerate the audit surface

List every skill in the audit radius plus its `SKILL.md` / `standards/` / `references/` / `scripts/`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture files --module plan-marshall
```

For the all-bundle variant, enumerate every bundle first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

The default radius is the `plan-marshall` bundle (where meta-leaks live by definition); the all-bundle escape hatch widens to every bundle.

### Step 2: Surface leak candidates (exhaustive full-read; grep is an accelerator, not a filter)

T5 requires reading **every** skill in full — a pure grep-for-markers pass would MISS leaks with no literal marker (the adversarial lesson: `recipe-marshal-json-config-audit` was "domain-invariant" yet meta). So:

1. **Full-read each skill** (`SKILL.md` + its `standards/` / `references/` / `scripts/`). The full read is the floor.
2. **Additionally** run the deterministic candidate-surfacer — Grep the MOVE-signature markers (Step 3 criteria B–D: `marketplace/bundles/`, `marketplace/targets/`, `target/claude/`, `~/.claude/plugins/cache/`, `--module plan-marshall`, `doc/{user,developer,adr,refactor}/`, repo-root `CLAUDE.md`) — to pre-flag high-signal files for prioritized scrutiny and as a cross-check. The grep is the net, never the sole filter.

Re-verify every candidate quote against disk before recording it (fabrication guard).

### Step 3: Apply the MOVE signature (judge by body, not description)

For each skill/section, test against criteria A–E. Any **one** marks a meta-leak; judge by the **body** — the `description`/`name` is not evidence:

- **A** — binds `recipe_domain: plan-marshall-plugin-dev`.
- **B** — operationally targets the meta-repo's own structure (`marketplace/bundles/`, `marketplace/targets/`, `target/claude/`, `~/.claude/plugins/cache/`, marketplace inventory, regen/sync of this repo's cache/executor, audit of this repo's bundles).
- **C** — hard-codes `--module plan-marshall` / `module: plan-marshall` as the operation target.
- **D** — cross-references meta-only docs (`doc/{user,developer,adr,refactor}/…`, repo-root `CLAUDE.md`).
- **E** — entire function only makes sense when the working tree **is** the plan-marshall repo.

### Step 4: Assign a disposition using the decision rules

For each confirmed leak pick **exactly one** disposition from the vocabulary below, applying the decision rules. Record evidence as `file:line` + verbatim quote (re-verified against disk).

#### Disposition vocabulary

| Disposition | Meaning | Applies when |
|-------------|---------|--------------|
| **SHIP** | Correct in the bundle | Generic infra; no action |
| **MOVE** | Relocate to `.claude/skills/` | Meta-*machine*-only — meaningless even to a consumer authoring plugins |
| **AGGREGATE** | Move behind a domain extension point (existing or new) | Real *domain* knowledge; should load conditionally for the right `skill_domain` |
| **GENERALIZE** | Parameterize (config or resolver) | Consumer-relevant capability with a hard-coded meta path |
| **DELETE** | Remove outright | Dead cruft — completed migration, orphaned artifacts |
| **RELOCATE-doc** | Move meta documentation to `doc/` | Shipped skill documenting the meta repo's own internals |
| **HYGIENE** | Drop / relativize | Dead links into the meta `doc/` tree |

#### Decision rules

1. **MOVE vs AGGREGATE fork.** If a *consumer who authors plan-marshall plugins* would benefit → AGGREGATE behind a domain extension (shipped in `pm-plugin-development`, gated to `plan-marshall-plugin-dev`). Only if meaningless even to that consumer → MOVE to `.claude/skills/`.
2. **Aggregation is ext-point-bounded.** Aggregate only where a domain ext-point exists: `ext-point-{outline, triage, verify-steps, self-review-surfacing, recipe, finalize-steps, build, provider, dynamic-level-executor, execution-context-workflow}` + `classify_paths()`. Where none fits, either GENERALIZE or **propose creating a new ext-point**.
3. **Obsolescence check → DELETE, not relocate.** Before relocating a "meta-only mechanism," ask whether newer architecture already removes its reason to exist (e.g. ADR-002's cache-freeze obsoleted the self-modifying classification). A guard for a hazard that can no longer occur is cruft.
4. **Structural vs usage meta-only.** A surface can be generic structurally (`.claude/` exists everywhere) yet meta-only in practice. Distinguish — it changes MOVE vs AGGREGATE vs keep.
5. **DELETE fits only dead cruft** — completed migrations, orphaned dirs/artifacts. A capability still in use is never DELETE.
6. **Description lies.** Always adjudicate on the body (criteria A–E), never the frontmatter claim.

### Step 5: Trace consumers / multi-site impact

A leak is rarely one file: a relocation or removal touches callers, q-gate validators, `plugin.json`, tests, and cross-references. Each deliverable MUST enumerate every site the disposition touches (e.g. a self-modifying-removal leak may span three enforcement sites). Use `architecture which-module --path P` and `architecture find --pattern P` to trace consumers; fall back to `Grep` for content-level reference searches.

### Step 6: Confirmation gate on destructive/contested dispositions

Before emitting deliverables, raise an `AskUserQuestion` for every contested or destructive call:

- every **DELETE** — is the mechanism truly obsolete?
- every **MOVE-vs-AGGREGATE** fork — does a plugin-authoring consumer benefit (→ AGGREGATE) or not (→ MOVE)?
- any **new-ext-point** proposal (decision rule 2).

Safe dispositions (HYGIENE, dead-dir DELETE) may auto-include without a prompt. Persist every gate answer to `decision.log` and capture it in the outline's `## Decision record` (Step 7). This mirrors `recipe-marshal-json-config-audit`'s aspect-2 deletion gate and `recipe-plan-review`'s analyze-then-confirm pattern.

### Step 7: Write `solution_outline.md`

**7a. Read the deliverable template**:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**7b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**7c. Write the solution outline** using the Write tool to `{resolved_path}`. One deliverable per leak (or per disposition group), each carrying: title, disposition, evidence (`file:line` + quote), the consumer/multi-site list (Step 5), `change_type`, `module`, resolved verification commands, and the `T5 × overall` cell for the floor-graded self-report. Group deliverables by disposition, ordered lowest-risk first: **DELETE** (dead cruft) → **AGGREGATE** / **GENERALIZE** / **RELOCATE-doc** / **HYGIENE** → **MOVE** last (most contested). Include a top `## Summary` table (one row per leak: target · disposition · confidence) and a `## Decision record` capturing every Step 6 confirmation-gate answer.

**7d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

## Output contract

A `solution_outline.md` whose `## Deliverables` are grouped by disposition (DELETE first → MOVE last), each deliverable carrying disposition, `file:line` + quote evidence, the multi-site consumer list, `change_type`, `module`, and resolved verification commands. Plus a top `## Summary` table (one row per leak: target · disposition · confidence) and a `## Decision record` capturing every confirmation-gate answer. Recipe metadata (`recipe_key`, `recipe_skill`, the resolved domain) and the pinned coverage cell are persisted to `status.json` per the ext-point-recipe post-conditions.

## Related

- `plan-marshall:dev-agent-behavior-rules` `standards/thoroughness.md` — the scope × thoroughness ladders, grade-to-the-floor rule, and coupling constraint (single source of truth; this recipe pins `T5 / overall`).
- `plan-marshall:dev-agent-behavior-rules` `standards/coverage-gathering-contract.md` — the coverage-gathering contract this recipe implements (consume obligation; pinned-cell expand/persist; cell → instruction table). This recipe skips the gather step.
- `plan-marshall:manage-config` `coverage expand` — the static identifier → instruction expander that enforces the coupling constraint.
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements; project-local recipes are discovered from `.claude/skills/recipe-*` by `manage-config list-recipes`.
- `recipe-marshal-json-config-audit` — sibling project-local, pinned-cell audit recipe; the convention template for frontmatter, the mandatory `recipe_domain` row, and the user-confirmation gate.
- `recipe-plan-review` — sibling project-local, pinned-cell (`T5 / overall`) analyze-then-confirm recipe.
- `recipe-plugin-compliance` — sibling project-local sweep for plugin-architecture compliance (a different defect class kept deliberately separate from generalization).
- `plan-marshall:phase-3-outline` — loads this skill via the recipe path with the input parameters above.
