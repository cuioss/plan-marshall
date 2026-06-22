# 03 — Security audit as a finalize step (uses a `security` profile)

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

**General approach + two-layer focused context loading** (as directed):

1. Compute the live footprint (`manage-references compute-footprint`).
2. Detect affected domains (java / python / js / oci / …).
3. Gather **focused** security context in two layers (general domain skills are not
   security-focused enough; a security review must gather everything it can):
   - **Cross-cutting layer (always loaded):** `plan-marshall:dev-general-security` —
     OWASP Top Ten, STRIDE, trust-boundary and secure-coding principles that apply
     regardless of domain. Plus the existing cross-cutting `untrusted-ingestion` /
     `workflow-permission-web`.
   - **Per-domain layer (resolved per affected module):** the module's
     `skills_by_profile.security` skills — dedicated, security-focused skills each
     domain declares for itself (carved out of the security sections currently
     buried in the general domain skills, e.g. java-core's input-validation +
     security-patterns, python-core's injection hardening, javascript's XSS/DOM
     trust, oci-security's OWASP-Docker + supply chain).
4. Run the audit (shared engine with [02](02-audit-recipes.md)'s
   `recipe-security-audit`); emit findings — mapped to valid `FINDING_TYPES`
   (`bug` / `anti-pattern`; no `security-issue` type, see [principles §2](principles.md))
   — → triage via domain `ext-triage-*`.
5. `configurable: [{key: security_audit, default: auto, description: "auto|always|never"}]`
   so it is gated like `finalize-step-simplify`.

## Decision — use a `security` profile

**Resolved: introduce a `security` profile.** A general-skill-only approach is
rejected — the general domain skills are not focused enough, and a security review
must gather all the focused context it can. The only non-profile alternative is a
central domain→security-skill map inside the audit step, which is the
domain-enumeration anti-pattern (core maintaining a per-domain table; cf.
`doc/refactor/principles.md` §6). The profile pushes the declaration into each
domain where it belongs: every domain declares its own
`skills_by_profile.security` in `get_skill_domains()`, and the audit resolves that
key for the affected modules.

`security` is added to `ExtensionBase.APPLICABLE_PROFILES` so
`skills_by_profile.security` is a valid enrichment/resolution key. It is a
**resolution-only profile**: the audit (recipe + finalize step) resolves its skills
directly; it is **not** auto-included in phase-4 task creation, so no plan spawns a
"security task" unless a deliverable explicitly declares the profile (a separate,
deferrable promotion to a planned task type).

## Key deliverable — security-aspect extraction sweep

The per-domain security skills are not authored from scratch: a dedicated task
**scans every domain bundle, extracts all security-related aspects from the
existing skills/standards, and relocates them into separate, security-focused
structures**:

- Sweep all `marketplace/bundles/*/skills/*` for security content (input
  validation, injection sinks, trust boundaries, secrets, crypto, supply chain,
  OWASP/STRIDE references — the same signal set the `ext-triage-*` extensions key
  on).
- **Domain-specific** extracted content → the dedicated per-domain security skill
  declared under that domain's `skills_by_profile.security`.
- **Cross-cutting** extracted content (OWASP Top Ten, STRIDE, general secure-coding
  principles) → `plan-marshall:dev-general-security`.
- Leave a cross-reference in the source general skill rather than duplicating, per
  the no-duplication doc rule.

This sweep is the systematic counterpart to "gather all the focused info we can":
it guarantees nothing security-relevant stays buried in a general skill.

## Affected surface

- New `phase-6-finalize/standards/finalize-step-security-audit.md`.
- New `plan-marshall:dev-general-security` skill — cross-cutting OWASP Top Ten /
  STRIDE / secure-coding (mirrors the `dev-general-*` family, e.g.
  `dev-general-code-quality`).
- `security` added to `ExtensionBase.APPLICABLE_PROFILES` +
  `extension-api/standards/profiles.md`.
- Per-domain `skills_by_profile.security` declarations in each domain's
  `get_skill_domains()`, plus the dedicated per-domain security skills carved out of
  the general domain skills' security sections.
- `manage-execution-manifest` decision-rules (candidate set, ordering, ceremony gate).
- marshal.json seed (`plan.phase-6-finalize.steps` + `security_audit` knob) in all
  three repos + consumer migration.
- Shared audit engine (with [02](02-audit-recipes.md)).

## Documentation to update (deliverables of this plan)

- `doc/concepts/security.adoc` — the proactive security audit gate, its per-domain
  skill loading, and the two-layer focused-context model (`dev-general-security` +
  per-domain `skills_by_profile.security`).
- `doc/concepts/automatic-reviews.adoc` — the new finalize step alongside
  automated-review and Sonar roundtrip.
- `doc/user/configuration.adoc` — the `security_audit` (`auto|always|never`) knob.
- `doc/concepts/extension-architecture.adoc` — the `security` profile.

## On completion

Delete this document and remove the `03` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Large — adds the `security` profile, a new `dev-general-security` skill, and
per-domain security skills across the domain bundles. Shares the audit engine with
[02](02-audit-recipes.md).
