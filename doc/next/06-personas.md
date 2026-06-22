# 06 — Personas

**Precedes [03](03-security-finalize-step.md): all three personas are modeled here,
and 03 ships as the named Security Reviewer persona. Independent of 02 — can run in
parallel.**

## Problem

Behavior is modeled as single rules (`dev-agent-behavior-rules`) + standards +
structured contracts (TOON, findings) — the right substrate for a capable model.
Role-play persona prose ("You are a Senior Security Engineer") was deliberately
dropped: for a capable model it adds little and dilutes precise instructions. Two
benefits that are *not* about model capability remain unaddressed:

- **Human anchor.** Capability bundles are scattered. A "Security Reviewer" is
  really `dev-general-security` + per-domain `skills_by_profile.security` +
  `recipe-security-audit` + `finalize-step-security-audit` + the `security` profile.
  There is no single legible name for that cluster.
- **Cross-target posture.** Weaker / non-Claude targets (OpenCode) plausibly
  benefit from role priming for *consistent posture* over long workflows (not raw
  capability). This is currently **unvalidated** — OpenCode has never been run — so
  it informs the design but does not drive it.

## Approach

Add a thin, **structured** persona layer — naming/aggregation + optional priming,
**not** prose role-play in skill bodies. Ship a complete skill shell:

```text
dev-general-persona/
├── SKILL.md            # aggregator: what a persona is + an index of all personas
├── standards/          # the design reasoning (see below) — the durable rationale
│   ├── persona-model.md          # structured-not-prose; data-declared; per-target render; no new runtime authority
│   └── persona-vs-profile-vs-role.md   # the concept-hygiene delineation
└── personas/           # one document per concrete persona — all three modeled
    ├── security-reviewer.md      # the security bundle (consumed by 03)
    ├── auditor.md                # retrospective / quality-audit surface
    └── code-reviewer.md          # on-demand code-review surface
```

- **`dev-general-persona`** (mirrors the `dev-general-*` family, e.g.
  `dev-general-code-quality`) is the aggregator: it defines what a persona is and
  indexes every persona under `personas/`.
- **`standards/`** holds the reasoning so it is durable, not folded into prose: the
  structured-not-prose discipline, the data-declared + per-target-render model, and
  the persona-vs-profile-vs-role delineation (below).
- **`personas/{key}.md`** — each concrete persona declares, as structured data: its
  kebab **key**, a one-line charter, its **foundation skills** (the `dev-general-*`
  subset it always loads), the capability skills it bundles, the entry points it
  owns (recipe / finalize step / command), and an optional priming preamble.
- **Data-declared, rendered per-target.** Persona is data, not body prose; the
  build renders it per-target (`doc/refactor/principles.md` §6 — declare as data,
  target renders): the Claude target minimizes/omits the priming, weaker targets
  may expand it into a role preamble. The cross-target benefit, if it materializes,
  is captured without changing Claude's behavior and without target-conditional
  body text.

## Key design decisions

- **Structured, not prose.** No "You are a seasoned…" paragraphs in skill bodies.
  Behavior stays in rules/standards/contracts; persona only frames, names, and
  (optionally) primes.
- **No new runtime authority.** Persona is a naming/aggregation layer over existing
  profiles, skills, and entry points — it adds no dispatch or resolution semantics.
- **Compose by flattening, not nesting.** A persona's declared skills are flattened
  into the execution-context's explicit `skills[]` at dispatch; personas never rely
  on nested skill loading (a skill loading another skill), which is unreliable. The
  unconditional `dev-agent-behavior-rules` base stays loaded by the execution-context
  itself and is never re-declared by a persona.
- **Model all three.** Author all three personas as first-class deliverables, each
  mapping its charter onto existing/planned surfaces with **no new machinery**:
  - **Security Reviewer** → the security bundle (`dev-general-security` + per-domain
    `skills_by_profile.security` + `recipe-security-audit` +
    `finalize-step-security-audit` + the `security` profile) — consumed by
    [03](03-security-finalize-step.md).
  - **Code Reviewer** → `recipe-code-review` ([02](02-audit-recipes.md)), framed
    alongside the existing automated-review + Sonar gate.
  - **Auditor** → `audit-archived-plan-retrospectives` + `recipe-plan-review` + the
    cross-plan preference sweep ([04](04-preference-learning-hints.md)).

## Concept hygiene — persona vs profile vs role/level

A deliverable in `standards/persona-vs-profile-vs-role.md`:

- **profile** — which skills resolve for a task (machine: resolution dimension).
- **role / level** — which model + effort runs a dispatch (machine: compute).
- **persona** — human-facing *name* for a capability bundle (+ optional per-target
  priming); an aggregation *over* profiles/skills/entry points, with **no** new
  control flow.

If persona ever starts gaining its own dispatch or resolution semantics, it
collides with profile/role — that is the line not to cross.

## Relationship to the `dev-general-*` family (composition, not absorption)

`dev-general-persona` is the same archetype as the rest of the family
(`dev-agent-behavior-rules`, `dev-general-code-quality`, `dev-general-module-testing`)
— `mode: knowledge`, REFERENCE MODE, language-agnostic, standards loaded on demand.
It joins the family as the aggregator; it does **not** absorb the others.

Those skills are shared substrate — many activities load them (e.g.
`finalize-step-simplify` already loads `dev-agent-behavior-rules` +
`dev-general-code-quality`). Absorbing their content into a persona would couple
shared knowledge to one role and break reuse. Instead a persona **composes** the
relevant foundation skills by reference.

**`dev-agent-behavior-rules` is out of scope for personas.** The execution-context
already loads it unconditionally for every dispatch — its agent contract is "loads
`dev-agent-behavior-rules` and any caller-specified skills." It is the universal
base every agent always has, not an optional role layer, so a persona never
re-declares or "inherits" it. Reframing it as an `agent-persona` is **rejected** for
the same reason: something loaded unconditionally and critically must not be modeled
as a swappable persona.

Each persona declares only the **additional** role foundation skills, on top of that
base:

- **Code Reviewer** → `dev-general-code-quality`.
- **Auditor** → `dev-general-code-quality` + `dev-general-module-testing` (+ the
  retrospective audit checks).
- **Security Reviewer** → `dev-general-security`.

These are **not** pulled in by **nested skill loading** (one skill loading another)
— that path is unreliable and must not be leaned on. A persona's `foundation_skills`
is a declaration the **dispatcher flattens into the execution-context's explicit,
flat `skills[]` list** (the same reliable channel that already carries
`dev-agent-behavior-rules` + the caller-specified skills), deduped against the
always-loaded base. The aggregator and persona docs are *read* for their declared
data; they never nest-load the skills they name. The win: a persona becomes the
declarative home for "which role skills this entry point dispatches with," replacing
the ad-hoc per-dispatch-site skill lists. Substrate stays in the `dev-general-*`
skills; the persona names and composes it.

## Addressing a persona

Personas are documents under one aggregator skill, not separate skills, so they are
**not** `bundle:skill`-addressable. Model them like recipes / profiles:

- **Identifier:** a kebab **persona key** — `security-reviewer`, `auditor`,
  `code-reviewer`.
- **Index:** the `dev-general-persona` `SKILL.md` lists every key → its
  `personas/{key}.md` document (the aggregator is the registry).
- **Binding:** an entry point (recipe / finalize step / command) declares
  `persona: {key}` in its frontmatter to bind itself to a persona.
- **Human reference:** "the Security Reviewer persona."
- **Resolution stays doc-driven** (read the aggregator index + `personas/{key}.md`)
  — no new runtime authority. A `manage-personas resolve --persona-key {key}` CLI
  verb (a separate script-executor skill, per the `manage-*` convention and the
  typed-ID-suffix rule in `argument-naming.md`) is added only if a script ever needs
  structured resolution.

## Affected surface

- New `plan-marshall:dev-general-persona` skill — complete shell: `SKILL.md` +
  `standards/` (reasoning) + `personas/` with all three authored:
  `security-reviewer.md`, `auditor.md`, `code-reviewer.md`.
- Build-target render support (`marketplace/targets/`) for the persona data —
  Claude minimal, other targets expandable.
- `03` consumes the Security Reviewer persona: the bundle it assembles gains the
  persona name + charter, and `finalize-step-security-audit` declares
  `persona: security-reviewer` in its frontmatter.
- Entry points that belong to a persona (recipes / finalize steps / commands) gain
  the `persona: {key}` frontmatter binding; the `plugin-doctor` could later validate
  the key resolves against the aggregator index.

## Documentation to update (deliverables of this plan)

- New `doc/concepts/personas.adoc` — what a persona is, the aggregator + `personas/`
  structure, the per-target render, and the persona/profile/role delineation.
- `doc/concepts/extension-architecture.adoc` — persona vs profile vs role.
- `doc/user/commands.adoc` — how personas surface to users (a name over entry points).

## On completion

Delete this document and remove the `06` row from [`README.md`](README.md); this is
part of the plan's finalize.

## Scope

Medium — concept + aggregator skill shell + all three personas (each mapping onto
existing/planned surfaces, no new machinery) + build-render support. Precedes 03;
independent of 02.
