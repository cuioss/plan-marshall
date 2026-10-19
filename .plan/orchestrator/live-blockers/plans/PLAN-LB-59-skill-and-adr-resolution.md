# PLAN-LB-59: Skill and ADR resolution respect the module

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-59-skill-and-adr-resolution.md` and is queued as one row file,
> `queue/PLAN-LB-59.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 by operator instruction from the lessons ingest `lessons-routing-039` and
> `-036` (pm-mcp-core `-224`, `-232`, `-242`, `-252`, graded high by the operator at that ingest),
> re-checked read-only at `d17ac5bef`. Priority: after the OpenCode plans. **Each deliverable is its
> own outline deliverable, and each Done-when is its own success criterion. Do not merge them.**

## Objective

Two resolvers ignore the module they act on:

- Task skill resolution merges every optional skill of a domain into every task, so each Java task
  is told to apply Quarkus, CDI and Weld rules whether or not its module uses them — including
  repositories that forbid them. The Java extension already knows which modules use CDI or Lombok;
  the merge bypasses it.
- ADR numbering and scanning read only `doc/adr/*.adoc`, so a repository that keeps ADRs per
  package (`doc/adr/{package}/`) gets colliding numbers that no scan or gate sees.

## Deliverables

1. **Task skills are resolved for the task's module.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `manage_personas` `_resolve_profile_domain_skills` keeps a domain×profile cell's `defaults`
     and admits an `optional` only when the task's module qualifies for it — through the domain
     extension's existing module-level applicability (`pm-dev-java/.../extension.py` L178-185, the
     CDI/Lombok dependency demotion) — and never when a repository-level exclusion names it.
   - `phase-4-plan` passes the task's module to the resolver.
   - A module whose frameworks cannot be read keeps the defaults only and says so in the resolver's
     return; it never falls back to all optionals.

   *Done when:* tests: a Java module without CDI dependencies resolves no `java-cdi` /
   `java-quarkus` / `junit-weld-testing`; a module with CDI resolves `java-cdi`; a repository
   exclusion removes a skill the module would otherwise get; an unreadable module yields defaults
   only. The first and fourth fail at `d17ac5bef`.

2. **ADR numbering and the scan see every ADR directory.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc
   - Persona: plan-marshall:persona-implementer
   - `manage-adr` reads ADRs recursively under `doc/adr/` (L29 `ADR_DIR`; non-recursive globs at
     L129, L139, L163, L233, L502). Numbering is unique across the whole tree, or per directory if
     the project declares per-package numbering — choose at outline and record the choice.
   - The scan reports duplicate numbers across directories, and the finalize step that runs the
     scan (or the pre-merge gate) refuses on a duplicate.

   *Done when:* tests: with `doc/adr/a/0001-x.adoc` and `doc/adr/b/0001-y.adoc` the scan reports the
   duplicate; next-number in a tree whose highest ADR is in a subdirectory returns the next number
   after it. Both fail at `d17ac5bef`.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: `manage-personas/scripts/manage_personas.py` ~L145-152 iterates `('defaults', 'optionals')` and appends both, with no module argument — orchestrator-read at `d17ac5bef`.
- OBSERVED: the `java` cell's optionals include `java-quarkus`, `java-cdi`, `junit-integration`, `junit-weld-testing` (`pm-dev-java/skills/plan-marshall-plugin/extension.py` L40-103); the module-level CDI/Lombok demotion sits at L178-185 (delegated agent).
- OBSERVED: pm-mcp-core `-224`, `-232`: Quarkus/CDI skills attached to tasks of a repository that forbids them; stripped by the operator (`lessons-routing-039`).
- OBSERVED: `manage-adr/scripts/manage-adr.py` L29 `ADR_DIR = Path('doc/adr')`; `ADR_DIR.glob('*.adoc')` at L129, L139, L163, L233, L502 — orchestrator-read.
- OBSERVED: pm-mcp-core `-242`, `-252`: per-package ADR numbers collided twice and were renumbered at landing (`lessons-routing-036`).
- HYPOTHESIS: a repository-level skill exclusion has a home in `marshal.json` (`skill_domains` or the persona config) — confirm before adding a key (verify-at-outline).
- HYPOTHESIS: the finalize ADR step (`adr-propose.md`) is where a duplicate refusal belongs — confirm at outline (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py` (D1)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — resolver call with module (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/` — module applicability hook, only if none exists (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/manage-personas/` (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-adr/scripts/manage-adr.py` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md` (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md` (verify-at-outline) (D2)
- HYPOTHESIS: `test/plan-marshall/manage-adr/` (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: none. Priority: after the OpenCode plans (operator instruction, 2026-10-15).
- Overlaps with: PLAN-LB-51 (staged) on the `phase-4-plan` tree; PLAN-LB-43 (staged) on the
  `extension-api/` tree, only if D1 adds a hook there. The gate will ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-59-skill-and-adr-resolution.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
