# 03 — Security audit as a finalize step (+ profile question)

**Shares the audit engine with [02](02-audit-recipes.md)'s `recipe-security-audit`.**

## Problem

Security in plan-marshall is reactive only (Sonar / PR-bot findings) and scattered
across `ext-triage-*` + per-domain standards. There is no proactive pre-ship
security pass.

## Approach

Add `default:finalize-step-security-audit` to phase-6, following the verified
finalize-step contract: frontmatter `name` / `description` / `order` /
`configurable`; terminal `mark-step-done --outcome --display-detail`;
HEAD-dependent if it self-commits fixes; member of `MAY_MUTATE_WORKTREE_STEPS` if
it edits. Discovery uses the **live `finalize-step-*` channel** (the dead
`provides_finalize_steps()` hook was removed in PR #752 — do not reintroduce it).

**`escalate_ask` no-mark invariant:** if the step needs a user decision it returns
`status: escalate_ask` and **must not** call `mark-step-done` — the
dispatcher/orchestrator owns the continuation and records the outcome (the
post-dispatch carve-out from PR #747). Only the terminal `done` / `loop_back` /
`failed` paths mark the step.

**General approach + per-domain context loading** (as directed):

1. Compute the live footprint (`manage-references compute-footprint`).
2. Detect affected domains (java / python / js / oci / …).
3. Load the matching domain security skills as context:
   - java → `pm-dev-java:java-core` (input-validation + security-patterns),
     `java-quarkus`, `pm-dev-java-cui:cui-http`
   - python → `pm-dev-python:python-core` (injection hardening)
   - js → `pm-dev-frontend:javascript` (XSS / DOM trust)
   - oci → `pm-dev-oci:oci-security` (OWASP Docker Top 10, supply chain)
   - all → `untrusted-ingestion`, `workflow-permission-web` (cross-cutting)
4. Run the audit (shared engine with [02](02-audit-recipes.md)'s
   `recipe-security-audit`); emit findings — mapped to valid `FINDING_TYPES`
   (`bug` / `anti-pattern`; no `security-issue` type, see [principles §2](principles.md))
   — → triage via domain `ext-triage-*`.
5. `configurable: [{key: security_audit, default: auto, description: "auto|always|never"}]`
   so it is gated like `finalize-step-simplify`.

## Open decision — the profile

Two options:

- **(a) No profile (recommended to start).** The finalize step + recipe cover the
  need; per-domain skills are loaded by domain detection, not by a profile. Lowest
  blast radius — no change to `APPLICABLE_PROFILES`, phase-4, or
  `skills_by_profile`.
- **(b) Introduce a `security` profile.** Adds `security` to `APPLICABLE_PROFILES`
  so deliverables can be security-typed and domains declare
  `skills_by_profile.security`. More expressive (security becomes a first-class
  task type) but touches phase-4 planning, architecture enrichment, and every
  domain bundle.

**Recommendation:** ship (a) first; promote to (b) only if we want security as a
*planned task type* rather than an audit gate. Resolve at the outline gate.

## Affected surface

- New `phase-6-finalize/standards/finalize-step-security-audit.md`.
- `manage-execution-manifest` decision-rules (candidate set, ordering, ceremony gate).
- marshal.json seed (`plan.phase-6-finalize.steps` + `security_audit` knob) in all
  three repos + consumer migration.
- Shared audit engine (with [02](02-audit-recipes.md)).
- (Option b only) `extension-api/standards/profiles.md`, phase-4-plan, domain
  `get_skill_domains()`.

## Documentation to update (deliverables of this plan)

- `doc/concepts/security.adoc` — the proactive security audit gate and its
  per-domain skill loading.
- `doc/concepts/automatic-reviews.adoc` — the new finalize step alongside
  automated-review and Sonar roundtrip.
- `doc/user/configuration.adoc` — the `security_audit` (`auto|always|never`) knob.
- (Option b only) `doc/concepts/extension-architecture.adoc` — the `security`
  profile.

## On completion

Delete this document and remove the `03` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Medium (option a) / large (option b). Shares the audit engine with [02](02-audit-recipes.md).
