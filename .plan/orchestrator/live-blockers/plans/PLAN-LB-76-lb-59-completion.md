# PLAN-LB-76: The module and the repository exclusions bind the skills a task actually receives

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-76-lb-59-completion.md` and is queued as one row file, `queue/PLAN-LB-76.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-59 (#1821, `779d3618f`),
> `landings/PLAN-LB-59.md` § Deliverable Fidelity (D1 partial). Priority is **medium**: PLAN-LB-59's
> resolver is correct at unit level and not bound to the path a task's skills actually come from.
> **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do
> not merge them.** A Done-when says "fails at `e1481166c`" only where the behaviour is new at that sha;
> a clause that already holds says "holds at `e1481166c`".

## Objective

PLAN-LB-59 made `manage-personas resolve --module` admit an optional skill only when the task's module
qualifies and no repository exclusion names it. But phase-4 loads a task's skills through the architecture
path first (defaults plus description-matched optionals) and that path never consults the exclusions, so a
repository that forbids `java-quarkus` can still receive it; the new `--module` call exists only in
documentation; and the tests that should prove the production path cannot fail for the reason they name.
This plan binds the exclusions and the module qualification to the skills a task finally carries, and
makes the tests honest.

## Deliverables

1. **A repository exclusion and a module's qualification bind every path a task's skills come from.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The skills a task carries after phase-4 never include a skill named by
     `skill_domains.{domain}.excluded_skills`, whichever path produced it (the architecture-resolved
     defaults and description-matched optionals, or the persona augmentation). Decide at outline whether
     phase-4 calls the resolver as a script step or the architecture path applies the exclusions itself,
     and record why; the `--module {D.module}` documentation in `phase-4-plan/SKILL.md` becomes an
     executed step or is removed.
   - A readable module whose domain extension has no `qualifies_optional` hook admits its defaults only,
     never every optional (`_module_qualified_skills` currently returns `set(optionals)` for it). The
     `ExtensionBase` default of `True` stays: a domain with no module-level signal keeps its optionals.

   *Done when:* each of these fails at `e1481166c`:
   - a repository whose `excluded_skills` names `java-quarkus` yields a task whose final `skills` list
     does not contain it, with the skill surfaced by the architecture path;
   - a readable module whose extension lacks `qualifies_optional` resolves defaults only;
   - an extension deriving `ExtensionBase` without overriding the hook still keeps its optionals (this
     clause **holds at** `e1481166c`, kept as the preservation guard).

2. **The tests of the production path can fail for the reason they name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - One test joins real discovery over a Maven POM fixture, `_resolve_module_data` and the resolver for the
     CDI-positive case, so dropping `declared_dependencies` from the discovery output turns it red.
   - `test_repository_exclusion_reads_the_real_config_reader` reads a real `marshal.json` through the real
     config reader (today it installs a fake `_config_core`); the deleted negative `java-quarkus not in`
     assertion in `test_java_module_with_cdi_admits_java_cdi` is restored.
   - The real unreadable branches (discovery raising, module absent) are exercised; today both
     unreadable tests monkeypatch `_resolve_module_data` to `(None, 'unreadable')`.

   *Done when:* each of these fails under a mutation of the production code it names, run and recorded
   (`order=mutation-after` is acceptable and must be labelled so):
   - removing `declared_dependencies` from the Maven discovery output fails the joined test;
   - replacing the real config reader with one that returns no exclusions fails the real-reader test;
   - making `_resolve_module_data` return a readable module on a discovery exception fails an
     unreadable-branch test.

3. **The exclusion match is symmetric, as the documentation says.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - A bare-name exclusion removes the full-notation skill and a full-notation exclusion removes the bare
     one, in `_is_excluded`, as `manage-personas/SKILL.md` and `skill-domains.md` state.

   *Done when:* each of these fails at `e1481166c`, if the hypothesis below is confirmed:
   - `excluded_skills: ["pm-dev-java:java-cdi"]` removes a skill the cell carries as bare `java-cdi`;
   - `excluded_skills: ["java-cdi"]` removes `pm-dev-java:java-cdi` (the form the existing test covers; this
     half **holds at** `e1481166c` and is kept as the regression guard).

## Claim Labels

- OBSERVED: phase-4 passes `--module {D.module}` in documentation only; no script calls the resolver — `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` L371-372 (landing analysis of PLAN-LB-59).
- OBSERVED: phase-4's architecture path loads defaults plus description-matched optionals and never consults `excluded_skills` — `phase-4-plan/SKILL.md` L323-326, L351-358 (landing analysis of PLAN-LB-59).
- OBSERVED: `_module_qualified_skills` returns `set(optionals)` for a readable module whose extension has no `qualifies_optional` attribute — `marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py` (landing analysis of PLAN-LB-59).
- OBSERVED: `test_repository_exclusion_reads_the_real_config_reader` installs a fake `_config_core` (`_install_config`), was written after the fix and never ran red — `test/plan-marshall/manage-personas/test_manage_personas.py`.
- OBSERVED: both unreadable-module tests monkeypatch `_resolve_module_data` to `(None, 'unreadable')` — `test/plan-marshall/manage-personas/test_manage_personas.py`.
- OBSERVED: the negative `java-quarkus not in` assertion was deleted in `137b8abff` (round-2 S5).
- OBSERVED: no test joins discovery, `_resolve_module_data` and the resolver; the CDI-positive pieces are covered separately in `test/plan-marshall/build-maven/test_discover_modules.py` and `test/pm-dev-java/plan-marshall-plugin/test_extension_applies_to_module.py`.
- HYPOTHESIS: `_is_excluded` matches one way only (a bare skill against a full-notation exclusion does not match) — confirm or refute at `manage_personas.py` § `_is_excluded` (verify-at-outline); self-review round 2 of PLAN-LB-59 reported it, and the landing does not say it was fixed.
- HYPOTHESIS: the architecture-resolved module names (`D.module`) always equal the `discover_project_modules` keys, virtual `-maven` / `-npm` names included — confirm at `manage_personas.py` § `_discovered_modules` (verify-at-outline).
- Verify-first clause: decide whether phase-4 calls the resolver or the architecture path applies the exclusions, before D1 is scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py` — `_module_qualified_skills`, `_is_excluded`, `_resolve_module_data` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — the `--module` step and the architecture path (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` — `qualifies_optional` (D1)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py` — `qualifies_optional`, `requires:` markers (D1)
- OBSERVED: `test/plan-marshall/manage-personas/` , `test/plan-marshall/build-maven/` and `test/pm-dev-java/plan-marshall-plugin/` — the fixtures of D1 to D3

## Dependencies and Sequencing

- Depends on: PLAN-LB-59 (shipped, `779d3618f`).
- Overlaps with: the staged PLAN-LB-51 on the `phase-4-plan` tree; PLAN-LB-43 on `extension-api/` only if
  D1 adds a hook there. The gate will ask.
- Adjacent to: `manage-config` `excluded_skills` (the key's write path stays as shipped).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-76-lb-59-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
