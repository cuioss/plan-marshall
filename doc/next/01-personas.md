# 01 — Personas (the persona / ref / profile identity model)

**Implemented first — it establishes the identity model and reframes the
`dev-general-*` foundation family that the other workstreams build on. The security
audit ([05](05-security-finalize-step.md)) ships as the named `persona-security-expert`.
Independent of [03](03-audit-recipes.md). Carries the widest "adapt the clients"
surface in the set.**

## Problem

Behavior is modeled as single rules (`dev-agent-behavior-rules`) + standards +
structured contracts. Role-play prose ("You are a Senior Security Engineer") was
dropped: for a capable model it adds little and dilutes precise instructions. Two
benefits remain unaddressed, and neither is about model capability:

- **Human anchor.** Capability bundles are scattered and unnamed (a "Security
  Reviewer" is a five-part cluster of skills + entry points + a profile).
- **Cross-target posture.** Weaker / non-Claude targets (OpenCode) plausibly benefit
  from role priming for *consistent posture* over long workflows — unvalidated
  (OpenCode unrun), so it informs the design but does not drive it.

Addressing them surfaces a deeper win: a coherent **identity model** that unifies the
`dev-general-*` family, the profile system, and the notion of a "role."

## The model — three kinds

A **persona** is the *action-general identity* you dispatch a task **as**. A **ref**
is a *cross-cutting concern* woven into actions. A **profile** is the
*domain-specific resolution axis* combined at runtime on top of the persona.

These are layers, not rivals: a runtime context = **persona** (action-general
identity) **+** `profile × domain` (domain-specific skills) **+** the **refs** the
persona composes. The original design intent — "general rules for an action,
combined with domain-specific info at runtime" — is exactly this, with the
action-general half given a name.

### Personas (`persona-*`)

- **Base:** `persona-plan-marshall-agent` — the default identity every agent has,
  loaded **unconditionally** by the execution-context (same guarantee as the
  current `dev-agent-behavior-rules` load). Composed by every other persona.
- **Work-activity personas** — each owns a unique **primary** work profile: they
  carry action-general knowledge and resolve domain skills via their profile(s).
- **Meta / evaluator personas** — no profile; they **compose** other personas as
  evaluation lenses (multi-persona by design) and emit findings rather than acting.

### Reference skills (`ref-*`)

Universal baseline concerns applied within *every* relevant action, with no
specialist identity. Composed by personas; never worn. They join the existing
`ref-*` family (`ref-documentation`, `ref-workflow-architecture`, …) and carry no
role priming.

## Persona ↔ profile matrix

| Profile | Identity | Kind |
|---|---|---|
| `core` (special, always-merged) | `persona-plan-marshall-agent` | base, always loaded |
| `implementation` | `persona-implementer` | work activity |
| `module_testing` | `persona-module-tester` | work activity |
| `integration_testing` | `persona-integration-tester` | work activity |
| `documentation` | `persona-documenter` | work activity |
| `security` *(profile added by [05](05-security-finalize-step.md))* | `persona-security-expert` | work activity (resolution-only profile) |
| `quality` | `ref-code-quality` | ⚠ concern (`ref`, **not** a persona) |
| — (no profile) | `persona-code-reviewer` | meta / evaluator |
| — (no profile) | `persona-auditor` | meta / evaluator |

Two deliberate, accepted asymmetries:

- **`quality` is a profile that maps to a `ref`.** Quality is a baseline woven into
  all coding — there is no "do quality" dispatch — so its action-general half is
  `ref-code-quality`. The `quality` *profile* still exists to resolve domain quality
  skills, and is carried as a **secondary `profiles:` entry** by the work personas
  that apply it (e.g. `persona-implementer` → `profiles: [implementation, quality]`).
  The multi-capable `profiles:` field (see *Persona owns its profiles* below) is
  exactly what makes this clean — no standalone quality persona needed.
- **`code-reviewer` / `auditor` are personas with no profile.** A profile exists to
  resolve *domain-specific* skills; review and audit own no domain skill set — they
  compose the other personas' resolutions. So they are profile-less by design.

`integration_testing` and `documentation` profiles **already exist**; only the
`security` profile is added. `verification` is not a profile (derived for write-only
deliverables), so it gets no persona.

## Naming map (old → new)

| New name | Replaces | Status |
|---|---|---|
| `persona-plan-marshall-agent` | `dev-agent-behavior-rules` | reframe (exists today) |
| `persona-module-tester` | `dev-general-module-testing` | reframe (exists today) |
| `ref-code-quality` | `dev-general-code-quality` | reframe (exists today) |
| `persona-security-expert` | — | new |
| `persona-implementer` | — | new |
| `persona-integration-tester` | — | new (profile already exists) |
| `persona-documenter` | — | new (spelling: `documenter`; flip to `documentor` if preferred) |
| `persona-code-reviewer` | — | new |
| `persona-auditor` | — | new |

Personas are first-class skills (`implements: persona`), discovered via the
frontmatter-archetype machinery + `plugin.json` — there is no aggregator skill and
no `personas/` sub-document container.

## Composition — flatten, never nest

A persona declares its **direct** composition only (the `ref-*` it applies and, for
meta personas, the personas it composes). It is **never** loaded by nested skill
loading (a skill pulling in another skill — unreliable).

Instead, **`manage-personas resolve --persona-key {key} [--domains a,b]`** computes
the **transitive closure** of the composition DAG and emits one flat, deduped
`skills[]`:

- include the base (`persona-plan-marshall-agent`),
- the persona's direct `ref-*`,
- recursively, any composed personas' refs/personas (meta personas),
- and, for **each profile in the persona's frontmatter `profiles:` list**, the
  `profile × {domains}` domain skills (the resolver reads the persona's frontmatter —
  it is the binding's source of truth, not a hardcoded table).

The dispatcher passes that flat list as the execution-context's explicit `skills[]`
— the same reliable channel that carries skills today. The composition graph must be
a **DAG** (base is a leaf composed by all; meta personas compose work personas; no
cycles). This is deterministic *resolution*, not new runtime authority — analogous
to `resolve-recipe` / `architecture resolve`.

## Addressing & binding

- **Identifier:** `bundle:skill` notation — personas are first-class skills, e.g.
  `plan-marshall:persona-security-expert`. No kebab-key registry, no aggregator.
- **The persona owns its profiles.** Each `persona-*` skill declares a
  **multi-capable `profiles:` frontmatter list** — the *single source of truth* for
  which profile(s) it loads (`persona-module-tester` → `profiles: [module_testing]`;
  `persona-implementer` → `profiles: [implementation, quality]`). Later dispatch code
  is then trivial: *read the persona's `profiles:`, load the matching `profile ×
  domain` skills* — no hardcoded persona↔profile table. The reverse `profile →
  persona` map is **derived** by scanning persona frontmatter. The **first** listed
  profile is the primary (identity) profile; the rest are *applied* profiles.
- **Work tasks resolve their persona from their (primary) profile** — derived from
  the frontmatter above; a `module_testing` task loads `persona-module-tester`
  automatically. The **primary** (identity) profile is unique per work persona so the
  reverse lookup is unambiguous (`plugin-doctor` enforces uniqueness); additional
  `profiles:` entries are *applied* profiles (e.g. `quality`).
- **Entry points (recipes / finalize steps / commands) declare `persona:`
  explicitly** — they have no task profile to derive from — and **exactly one**. The
  declared persona may be a *work-activity* persona (`finalize-step-security-audit` →
  `persona: persona-security-expert`) or a *meta* persona that encapsulates a
  multi-lens composition internally (`audit-archived-plan-retrospectives` →
  `persona: persona-auditor`).
- **Human reference:** "the Security Expert persona."

## Extensibility

The model is **open** — new personas are added later by the same pattern, with no
core change:

- A new **work-activity** persona = a `persona-*` skill (`implements: persona`) that
  declares its profile(s) in its `profiles:` frontmatter + a matching profile in
  `APPLICABLE_PROFILES` + per-domain `skills_by_profile.{profile}` declarations; it
  composes `ref-*` concerns. The `profiles:` field is the binding's source of truth.
- A new **meta / evaluator** persona = a `persona-*` skill that composes other
  personas as lenses; no profile.
- A new **concern** = a `ref-*` skill, composed by whichever personas apply it.

Discovery is by frontmatter archetype (`implements: persona` / `ref`) + `plugin.json`
— adding one touches neither the resolver, the dispatcher, nor other personas. Likely
future additions (**not in scope now**): `persona-architect`, `persona-planner`,
`persona-release-manager`, … each slotting in by this rule.

## Concept hygiene

- **persona** — the *identity* you dispatch as (action-general). NOT the
  execution-context **role/level** (which selects model + effort — a *compute*
  resolution); keep these two senses of "role" distinct in all prose.
- **profile** — the *domain-specific resolution axis*, composed on top of a persona
  at runtime.
- **ref** — a *concern* composed by personas; not an identity.
- A persona adds **no new control flow** — it is a named, resolvable bundle.

## Per-target render

A persona-skill may carry an optional **priming preamble** rendered per-target
(`doc/refactor/principles.md` §6 — declare as data, target renders): minimal/omitted
on Claude, expandable into a role frame on weaker targets. `ref-*` skills carry no
priming.

## Affected surface

- **Rename three current skills** and reclassify: `dev-agent-behavior-rules` →
  `persona-plan-marshall-agent`, `dev-general-module-testing` →
  `persona-module-tester`, `dev-general-code-quality` → `ref-code-quality`.
- **New personas:** `persona-implementer`, `persona-integration-tester`,
  `persona-documenter`, `persona-security-expert`, `persona-code-reviewer`,
  `persona-auditor`.
- **Profiles are added by their owning workstream.** 01 provides the `profiles:`
  field + the resolver mechanism and creates the `persona-*` skill *shells* (incl.
  `persona-security-expert`); the `security` profile itself, its per-domain
  `skills_by_profile.security`, and `persona-security-expert`'s security content are
  [05](05-security-finalize-step.md)'s deliverables.
- **`manage-personas` script-executor skill** — the `resolve` verb (transitive
  flatten + `profile × domains`), per the `manage-*` convention and the typed-ID flag
  (`--persona-key`).
- **`profiles:` frontmatter field** on `persona-*` skills (multi-capable list; the
  owner of the persona↔profile binding). The reverse `profile → persona` map is
  derived by scanning frontmatter; `plugin-doctor` validates that each profile has a
  unique primary-owning persona.
- **Dispatch integration:** work-task dispatch derives persona from profile; the
  resolver output populates the explicit `skills[]`. `persona-plan-marshall-agent`
  stays the unconditional execution-context base.
- **Per-target render** support in `marketplace/targets/` for persona priming.
- **Frontmatter archetype:** `implements: persona` / `ref` markers; `plugin-doctor`
  validates each profile's unique primary-owning persona and that `persona:` bindings
  resolve.
- **Adapt the clients (migration).** Every consumer of the three renamed skills
  migrates: dispatch sites that hand-list them in `skills[]` (e.g.
  `finalize-step-simplify` → `persona-plan-marshall-agent` + `ref-code-quality`),
  per-phase dispatch skill lists, and consumer projects. Grep `dev-general-`,
  `dev-agent-behavior-rules`, and `skills:` to inventory.
- **[05](05-security-finalize-step.md) consumes `persona-security-expert`** (its
  two-layer model becomes: `persona-security-expert` action-general + `security
  profile × domain` skills).

## Documentation to update (deliverables of this plan)

- New `doc/concepts/personas.adoc` — the persona/ref/profile model, the matrix, the
  composition-by-flattening resolver, addressing, and the per-target render.
- `doc/concepts/extension-architecture.adoc` — persona vs profile vs role/level.
- `doc/user/commands.adoc` — how personas surface to users.

## On completion

Delete this document and remove the `01` row from [`README.md`](README.md); this is
part of the plan's finalize.

## Scope

Large — touches the foundation skill family, the profile set, dispatch-time
resolution (new `manage-personas` resolver), the build-target render, and every
consumer of the renamed skills. Implemented first; independent of 03.
