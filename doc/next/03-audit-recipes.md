# 03 — Audit capabilities as recipes

**Keystone workstream. [04](04-routing-v2.md) routes onto these; `finalize-step-security-audit` shares the security audit engine.**

## Problem

A focused review or audit should deliver value *on its own*, without buying the
whole planning methodology. plan-marshall has no standalone audit entry point —
every capability requires a full plan. Recipes are exactly our standalone,
single-envelope, low-token mechanism (`ext-point-recipe`), so audits should be
recipes.

## Approach

Introduce an **audit recipe family**, starting with:

- **`recipe-code-review`** — focused structural/quality review of the current branch
  diff, emitting findings into `manage-findings` + triage (`ext-triage-*`). Single
  envelope.
- **`recipe-security-audit`** — on-demand security audit. Shares the audit engine
  with `finalize-step-security-audit` (see "shared engine").

Recipe definition follows the verified contract: a `recipe-{name}/SKILL.md` with
frontmatter `implements: plan-marshall:extension-api/standards/ext-point-recipe`,
`mode: workflow`; registered either via a bundle's `provides_recipes()` hook
(key / name / description / skill / default_change_type / scope) or via project
frontmatter (`recipe_domain` required, omit to hide a half-authored recipe).
Recipe-sourced plans skip quality analysis (phase-2-refine Step 3 sets
confidence = 100) and run their own discovery + deliverable workflow in one
envelope.

## Key design decisions

- **Findings, not prose.** Audit recipes emit into `manage-findings` so triage,
  loop-back, and suppression all work for free — the structural difference from
  external tools that print a report and stop. Findings map onto the closed
  `FINDING_TYPES` taxonomy (see [principles §2](principles.md)): `recipe-code-review`
  → `lint-issue`; `recipe-security-audit` → `bug` / `anti-pattern` (no
  `security-issue` type exists).
- **Shared audit engine.** The security audit *logic* (per-domain skill selection +
  audit run) is authored once and invoked from two entry points: this recipe
  (on-demand) and `finalize-step-security-audit` (automatic).
  No duplicated per-domain logic.
- **Surgical / diff-aware scope** so phase-4 manifest minimization already applies
  (surgical + verification → drops heavyweight finalize steps).
- **Always create a plan-directory — even for short plans.** A recipe/shortcut runs
  its phases inline (no per-phase execution-context, see [principles §3](principles.md))
  but still gets its own `.plan/local/plans/{plan_id}/` so runs stay apart and the
  plan-bound tooling (`manage-status`, `manage-findings`, the `ci` abstraction) works
  uniformly with no plan-less special case. (This also removes the friction where a
  plan-less change cannot use the `ci` abstraction's plan-bound `pr create`.)

## Affected surface

- New `recipe-code-review/`, `recipe-security-audit/` skills (plan-marshall bundle).
- `provides_recipes()` registration + `list-recipes` visibility.
- `manage-findings` (reuse), `ext-triage-*` (reuse).
- `/plan-marshall recipe=...` workflow doc.

## Open decisions

- Whether `recipe-code-review` also gets a finalize twin (a code-review gate) or
  stays on-demand only. **Recommendation:** on-demand only for now — the existing
  automated-review + Sonar roundtrip already cover the gate role.

## Documentation to update (deliverables of this plan)

- `doc/concepts/recipes.adoc` — the new audit recipe family and the
  shared-audit-engine relationship with `finalize-step-security-audit`.
- `doc/concepts/automatic-reviews.adoc` — how on-demand `recipe-code-review`
  relates to the automated-review + Sonar gate.
- `doc/concepts/security.adoc` — `recipe-security-audit` as the on-demand security
  entry point.
- `doc/user/commands.adoc` — `/plan-marshall recipe=code-review` /
  `recipe=security-audit` usage.

## On completion

Delete this document and remove the `03` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Medium. Unblocks [04](04-routing-v2.md); shares the security engine with `finalize-step-security-audit`.
