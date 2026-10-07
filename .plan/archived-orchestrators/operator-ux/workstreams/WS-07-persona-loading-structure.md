# WS-07: Persona loading is explicit and fixed, not conditional prose

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-07-persona-loading-structure.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Every dispatched context loads one hardcoded base persona whose internal tiers are selected by
English prose the agent must read and judge ("load as needed"), while the persona system it sits
inside resolves every other selection declaratively from `composes:` / `profiles:` frontmatter
through `manage-personas resolve`. This workstream converts the prose register into the
declarative one and splits the base by context, so what a context loads is fixed, resolvable
before dispatch, and auditable. It closes when no persona selects a standard by prose judgement
and the leaf no longer loads main-context-only material.

The workstream exists because this epic authored the surface: PLAN-06 (#1382) and PLAN-07 (#1387)
added `standards/user-communication.md` to the unconditional tier, and the operator observed the
cost at the leaf. It is machinery-shaped work admitted into an operator-UX epic as a deliberate,
recorded exception to this epic's own finalize-machinery ruling — see the Decisions entry.

## Scope

The boundary is the **selection mechanism** for persona content, plus the **audience split** of
material this epic authored. It is not a rewrite of the standards' content: a rule that binds
today still binds after this workstream, at the same strength, for the contexts it reaches.

- **In scope**: `persona-plan-marshall-agent/SKILL.md` (Steps 1–5 and the Hard Rules section);
  `persona-plan-marshall-agent/standards/user-communication.md` (audience split only);
  `manage-personas/SKILL.md` and `scripts/manage_personas.py` (the hardcoded-base edge);
  `agents/execution-context.md` and `agents/execution-context-reader.md` (the implicit base load);
  `phase-4-plan/SKILL.md` (the resolve call site); the `composes:` / `profiles:` frontmatter of the
  nine `persona-*` skills; the plugin-doctor frontmatter-contract rules that read them.
- **Out of scope**: the *content* of `agent-behavior-rules.md`, `tool-usage-patterns.md`,
  `argument-naming.md`, `thoroughness.md`, and `coverage-gathering-contract.md` — this workstream
  relocates and re-selects them, it does not rewrite them. Also out of scope: the domain-extension
  `profile × domain` resolution (WS-01's surface), and any change to which rules are *hard* rules.

## Plans

{Not yet decomposed. `decompose` has not run for this workstream — the plan specs below are the
expected shape, not staged specs. No PLAN-NN is allocated until decompose runs, so nothing here is
emittable.}

| Plan | Status | Notes |
|------|--------|-------|
| — | not decomposed | Expected: a hard-rules/context tier split; a prose-to-`composes:` conversion; an audience split of `user-communication.md`; a resolver + dispatch-site change |

## Sequencing and Surface Notes

- **The split guard bites before decompose does.** The in-scope surface spans the base persona,
  the resolver script, two agent definitions, a phase skill, nine persona frontmatters, and the
  plugin-doctor rules that read them — well past the six-deliverable presumption. Decompose MUST
  split this into sequential plans rather than staging it as one.
- **`agents/execution-context.md` is the highest-risk file in the epic.** Every dispatch in every
  plan depends on it. A plan touching it should ship alone, and its own spec should say so.
- **Hard rules must stay universal.** The unconditional base is load-bearing for safety (one Bash
  command per call, `.plan/` through scripts only, no direct `gh`/`glab`, leaves cannot dispatch),
  not for advice. Any split keeps a genuinely unconditional hard-rules tier that reaches contexts
  which never call the resolver. A design that makes the hard rules context-selected is refuted by
  construction, not merely discouraged.
- **PLAN-06's argument survives and constrains the audience split.** `user-communication.md` states
  its own unconditional placement is deliberate — an opt-in placement "reproduces the failure mode
  they exist to fix", and Rule 1a explicitly pre-empts the exemption reading. So the leaf's fixed
  persona MUST carry the `display_detail` language rule. A split that drops it from the leaf
  re-opens what PLAN-06 closed.
- **Collides with PLAN-08 (WS-05).** PLAN-08 remediates user-facing sites and its declared surface
  includes `phase-1-init/SKILL.md`, `phase-5-execute/SKILL.md`, `phase-6-finalize/SKILL.md` and the
  `plan-marshall/workflow/` docs. It does not currently declare `persona-plan-marshall-agent` or
  `agents/`, so the declared surfaces are disjoint today — but PLAN-08's own remediation may reach
  persona prose. Re-check the declaration when either is emitted.
- **No collision with the live queue's `manage-config` cluster.** PLAN-02, PLAN-03, PLAN-04 and
  PLAN-09 all serialize on `manage-config/SKILL.md`, which is not in this workstream's surface. A
  WS-07 plan is therefore a candidate second-slot partner for that cluster — the first such
  candidate in the epic that is not sequenced behind something else. Confirm through
  `corpus cross-check` at decompose, not from this note.
