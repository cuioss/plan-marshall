# PLAN-25: domain-conditional-loading-concept

epic: plan-optimization
workstream: WS-10

> **DESIGN-FIRST plan spec.** Produces a concept + ADR + migration path. **Implements NO executor change.**
> Operator-surfaced 2026-07-20 ("eventually we need a new plugin-concept for loading filter"); scoped
> against an orchestrator survey of the existing machinery (findings inlined below, re-ground at outline).

## Objective

Establish the missing concept: **domain content is in play only when its domain is active.** Today
domain specifics have nowhere to live except the core, so they leak there — cui-openRewrite marker
knowledge (`AUTO_SUPPRESS_RECIPES` naming `CuiLogRecordPatternRecipe`/`InvalidExceptionUsageRecipe`, the
marker grammar, a `search-markers` verb in the core build-API contract) sits in the core `plan-marshall`
bundle, unconditionally present for every consumer regardless of domain. Decide the model, record it as
an ADR, and lay a migration path — **before** anyone mutates the executor.

## Surveyed starting position (orchestrator, 2026-07-20 — re-ground at outline)

**Domain-conditional activation already exists and is pervasive — but it gates KNOWLEDGE/SKILLS, not
SCRIPTS/VERBS.** Most of this is a GENERALIZATION; exactly two pieces are genuinely NEW.

| Layer | Domain-conditional today? | Verdict |
|---|---|---|
| Skill/knowledge resolution by domain | **Yes** — `manage-config resolve-workflow-skill-extension --domain {d} --type {triage\|outline}`, **null-on-absent** | generalization (add a `--type`) |
| Ext-point implementor discovery | **Yes** — `extension_discovery.find_implementors()` with `default_on` / `presets` / `source` | generalization (add a domain filter) |
| Bundle applicability | **Yes** — `discover_applicable_extensions(project_root)` filters by `discover_modules()` | generalization (already the "is this bundle relevant" predicate) |
| Plan-scoped domain activation SIGNAL | **Yes** — `_cmd_domain_detect.py`: `domains = detector ∪ always_on ∪ glob_matched` → persisted to `references.domains` | generalization (signal exists and is persisted) |
| **Build verbs from domain bundles** | **NO** — `ext-point-build.md` mandates `skills/build-{tool}/` under the **plan-marshall** bundle; all 4 build skills are core-owned; optionality is **tool**-keyed, not domain-keyed | **NEW** |
| **Script-notation exposure in executor** | **NO** — `generate_executor.py` has **zero** `domain`/`skill_domains` references; registers every script of every installed bundle unconditionally | **NEW — nothing to generalize** |

**Core→domain reverse dispatch is ESTABLISHED, not novel:** `ext-triage-{domain}` (7 implementations,
dispatched from `workflow/triage.md:77` and `verification-feedback.md:214`), `arch-gate-{domain}`,
`ext-self-review-plan-marshall`, `provides_outline_skill`, `provides_recipes`. **Uniformly, every one
contributes a SKILL/markdown surface resolved by domain key — none contributes a SCRIPT the core
invokes.** The only existing workaround for scripts is `ext-point-self-review-surfacing`'s "first
implementor whose notation **resolves in the current executor**, else zero-generator fallback" — a
resolvability probe, not real gating.

## Deliverables

### D1 — decide and record the model (ADR)

Answer, per layer, what "active domain" means and **which layers actually gate**. The activation signal
already exists (`references.domains`); the open questions are scope and timing. **Decide explicitly:**
(a) is gating per-plan (using `references.domains`) or per-project (using `skill_domains` /
`discover_applicable_extensions`), or both at different layers? (b) does an inactive domain's component
become *invisible* or *present-but-refusing*? — note ADR-009's fail-closed posture argues against silent
absence; a refusal is diagnosable, a silent no-op is what produced the marker defect. (c) what is the
degrade path when nothing implements a needed surface (the existing zero-generator fallback shape)?
**Acceptance:** an accepted ADR stating the model, the gating layer(s), the visibility semantics, and
what is deliberately NOT gated. **Do not defer these to implementation.**

### D2 — specify domain-contributed executable surfaces

`ext-point-build` currently mandates build skills live in the core bundle, so a domain bundle **cannot**
own an executable verb — the structural reason the marker detector had nowhere to go. Specify the
contract that lets a domain bundle contribute one: declaration, discovery, dispatch, and the
core-side resolution shape (mirroring `resolve-workflow-skill-extension`'s null-on-absent). **Confirm at
outline** whether this extends `ext-point-build`, adds a sibling ext-point, or generalizes
`find_implementors` with a domain filter. **Acceptance:** a written contract sufficient for PLAN-23's
relocated detector to be contributed and dispatched as a first-class domain-owned verb, plus at least one
other candidate validated against it (see D4's inventory).

### D3 — specify domain-aware notation exposure (SPECIFICATION ONLY — no implementation)

The genuinely new mechanism: `generate_executor.py` is domain-blind. Specify how notation registration
could become domain-aware, **and do not implement it in this plan.** **⚠ Blast-radius warning, recorded
deliberately:** this exact file has produced TWO defects in this epic already — PLAN-08 #934 and
PLAN-13 #950 D1/D2 (first-hit-wins resolver; regenerate-every-run). It is high-risk, consumer-facing, and
a wrong move there silently breaks script resolution for every consumer. **Acceptance:** a specification
including the migration path, backward-compatibility story for existing notations, the failure mode when
a notation is requested for an inactive domain (tie to D1's visibility decision), and an explicit
recommendation on **whether this layer should be gated at all** — "specify then decline" is a legitimate
and possibly correct outcome, given the resolvability-probe workaround already exists.

### D4 — inventory the core-resident domain specifics

Enumerate (do not sample) what domain-specific content currently sits in the core bundle — the marker
case is the instance we found, not the population. Mirror PLAN-13 #950's
`provisioning-fail-closed-audit.md` shape: per site, a fix-or-justify disposition and which D1/D2/D3
mechanism would home it. **Acceptance:** a written inventory; each entry either mapped to a mechanism, or
justified as legitimately core-owned. This is what tells us whether the concept is worth its cost.

### D5 — CONCRETE ANCHOR + FIX: arch-gate seed/resolve mismatch (verified consumer instance)

The sharpest real instance of this concept — grounds D1 and D4 in a shippable fix so the plan is not
purely abstract. **Verified (orchestrator, 2026-07-20), from a cui-open-rewrite datapoint:**
`manage-config configure` seeds `default:verify:arch-gate` gated **ONLY** on domain-extension presence —
`_cmd_skill_domains.py:908-909` appends it whenever `_configured_domains_provide_arch_gate(domains_configured)`
is True, i.e. any active domain whose extension declares `provides_arch_gate()` (pm-dev-java does:
`extension.py:208`, binding `pm-dev-java:arch-gate-java`/ArchUnit). It **never checks whether any module
can actually RUN arch-gate**. At compose the step resolves via `architecture resolve --command arch-gate`
against the build MODULE's canonical commands — and a Maven module exposing `quality-gate`/`verify`/
`module-tests` but no `arch-gate` command → **unresolvable → blocks manifest compose.** The two gates
disagree: the SEED (domain-level presence) says yes, the RESOLVE (module-command level) says no.

**Provenance (git-verified):** the seed, the helper `_configured_domains_provide_arch_gate`, AND the java
`provides_arch_gate()` hook all landed together in **PR #802 (`5cde369fa`, 2026-06-29, "arch-gate L1
build")** — so this is an **original design gap, NOT a regression** (do not bisect for a breaking change).
#802 designed arch-gate as "resolvable via `architecture resolve`" yet gated the SEED purely on
domain-extension presence, never connecting the two gates; its MVP assumption was that a java module wires
an ArchUnit `@ArchTest` Surefire execution (so arch-gate resolves). A java-domain consumer that does NOT
wire ArchUnit (e.g. cui-open-rewrite's Maven module) breaks that assumption. #802 predates this epic.

This is exactly the concept's core question made concrete, and D1's visibility semantics decided on a real
case: **a domain-declared-but-module-unrunnable verify-step must not be seeded (or must be skipped at
compose), never left to block.** Note the manual workaround is NON-DURABLE — a consumer's
`manage-config remove-step` is re-appended by the next `configure` (the seed is deterministic from domain
presence), so the durable fix must be here. **Fix (confirm the seam at outline against D1's ADR):** gate
the arch-gate seed on resolvability (seed only when at least one configured module resolves an `arch-gate`
command), OR make compose skip an unresolvable domain-seeded verify-step rather than block — tie the
choice to D1's invisible-vs-present-but-refusing decision (ADR-009 fail-closed argues for a diagnosable
skip-with-warning over a silent drop). **Acceptance:** with java domain active but NO module resolving an
`arch-gate` command, `configure` does not seed (or compose skips) `default:verify:arch-gate`, with a
surfaced reason; a java module that DOES wire arch-gate still gets the step; regression test for both.
Generalize beyond arch-gate if the same seed-vs-resolve mismatch exists for other domain-seeded steps
(fold that enumeration into D4).

## Out of scope / do NOT expand
- **Implementing the executor change** — D3 is specification only. Any implementation is a follow-up plan
  gated on D1's ADR. (D5 is a SEPARATE concrete fix that does NOT touch the executor and does NOT wait on
  the ADR — a domain-seeded step that can't resolve is a self-contained robustness defect.)
- Relocating the marker detector — that is **PLAN-23**, which proceeds independently and supplies the
  first real instance to generalize from.
- Re-litigating the ext-point mechanism itself — it is mature (18 standards docs, two discovery paths).
  This plan EXTENDS it to executable surfaces; it does not redesign it.

## Absorbs
- Open Defect "no plugin concept for domain-conditional loading; domain specifics leak into the CORE"
  (operator, 2026-07-20).

## Expected Surface
- New ADR (D1) + `extension-api/standards/` ext-point spec (D2) + a specification doc (D3) + an inventory
  doc (D4). **Documentation-dominant EXCEPT D5**, which is a concrete code fix + regression test.
- Read-heavy, write-light against: `extension_discovery.py`, `_cmd_domain_detect.py`,
  `_cmd_skill_resolution.py`, `ext-point-build.md`, `ext-point-self-review-surfacing.md`,
  `build-api-reference.md`, `generate_executor.py` (READ ONLY in this plan).
- **D5 writes:** `manage-config/scripts/_cmd_skill_domains.py` (`_configured_domains_provide_arch_gate` /
  the seed at ~:908-909) and/or the manifest-compose resolve-or-skip path (`architecture resolve
  --command arch-gate`); test for java-domain-active-but-no-arch-gate-command.

## Dependencies and Sequencing
- Depends on: none hard. **Benefits from PLAN-23 landing first** — its named seam is the concrete instance
  D2 generalizes from — but does not block on it (D1/D4 are independent).
- **Adjacent to PLAN-23** conceptually, not by surface: PLAN-23 writes code in build/domain bundles,
  PLAN-25 writes standards/ADRs. Safe to run in parallel; PLAN-25's outline should read PLAN-23's landing
  if it exists by then.
- Surface-disjoint from PLAN-18/20/21/22/24.

## Size / split guard
**5 deliverables** — at the ~6 presumption. Mostly design-first (D1-D4) with ONE concrete fix (D5). D5 was
folded in operator-directed (2026-07-20) because it is the concept's flagship real instance and a
self-contained fix that should not wait on the ADR. **Cleanly separable if scope balloons at outline:** D5
does not depend on D1-D4 (a domain-seeded-but-unresolvable step is a standalone robustness defect) and can
be pulled into its own small plan; **D4's inventory** is the other elastic seam. Record any split as an
epic decision. Implementation of D2/D3 remains deliberately OUT — follow-up(s) gated on D1's ADR; expect
this concept to need more than one plan total.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-25-domain-conditional-loading-concept.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-25.md is recorded}
