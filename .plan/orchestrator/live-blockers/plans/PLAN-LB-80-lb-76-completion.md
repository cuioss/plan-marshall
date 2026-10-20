# PLAN-LB-80: The repository's skill veto fails closed, narrows exactly and reaches every seam

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-80-lb-76-completion.md` and is queued as one row file, `queue/PLAN-LB-80.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-76 (#1824, `0cfc7d3f0`),
> `landings/PLAN-LB-76.md` § Code defects 1-6. Priority is **medium**: the exclusion now binds the paths
> PLAN-LB-76 named, but it fails open when the configuration cannot be read, a qualified exclusion removes
> another bundle's bare skill, module qualification still does not bind the architecture path, and three
> read verbs still serve an excluded skill. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** A Done-when says "fails at `0cfc7d3f0`" only
> where the behaviour is new at that sha; a clause that already holds says "holds at `0cfc7d3f0`". A clause
> whose premise this spec labels HYPOTHESIS gets no "holds at" label until the hypothesis is settled.

## Objective

A repository that writes `skill_domains.{domain}.excluded_skills` has written a prohibition. After
PLAN-LB-76 a task's final skills honour it on the paths that plan reached, but the veto degrades to "no
exclusions" on every read failure, a bundle-qualified entry removes a skill of another bundle when the
cell carries it bare, and the module qualification the same plan promised for the architecture path is
not applied there. This plan makes the veto fail closed, makes the match narrow exactly, binds
qualification to the path phase-4 reads, and closes the read verbs that still bypass it.

## Deliverables

1. **The exclusion read fails closed.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - An absent `marshal.json` or an absent `skill_domains` key still means "no exclusions". A `marshal.json`
     that exists and cannot be parsed, a `skill_domains` or `excluded_skills` value of the wrong type, and an
     unimportable config loader, are **errors** the caller sees, not an empty set. The reader returns a
     result the callers can tell apart from "none declared", and the four callers that swallow a failure today
     (`manage_personas.py` import guard, `_cmd_client_query.py`, `_cmd_enrich.py` `except Exception: pass`,
     `extension_base._build_applicable_result`) stop swallowing it. Decide at outline whether a caller blocks
     or serves the skill list with a loud warning field, and record why; a silent empty set is not an option.

   *Done when:* each of these fails at `0cfc7d3f0`:
   - a malformed `marshal.json` makes `architecture module` and `manage-personas resolve` report the error
     instead of serving an excluded skill;
   - `enrich --project-dir D` for a `D` whose configuration is unreadable reports the error instead of
     persisting an unfiltered map;
   - an absent `marshal.json` still resolves with no exclusions (this clause **holds at** `0cfc7d3f0`, kept
     as the regression guard).

2. **A qualified exclusion narrows exactly, against bare and qualified skills alike.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `is_excluded` (`extension_base.py`) removes a cell's bare skill for a qualified exclusion only when the
     skill belongs to that bundle. Decide at outline how the bare skill's bundle is known (the cell, the
     domain's extension bundle) and record why. The documentation sentence the previous plan changed in
     `skill-domains.md` and `manage-personas/SKILL.md` is brought into line with the behaviour, or the
     behaviour into line with it.

   *Done when:* each of these fails at `0cfc7d3f0`:
   - `excluded_skills: ["other-bundle:java-cdi"]` does not remove a bare `java-cdi` carried by a `pm-dev-java`
     cell;
   - `excluded_skills: ["pm-dev-java:java-cdi"]` removes the bare `java-cdi` of a `pm-dev-java` cell (this
     clause **holds at** `0cfc7d3f0` if the HYPOTHESIS below is confirmed; label it `none` then);
   - the tests of both clauses fail under a mutation of `is_excluded`, run and recorded (`order=mutation-after`
     acceptable and labelled).

3. **Module qualification binds the architecture path phase-4 reads.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_build_applicable_result` (`extension_base.py`) consults `qualifies_optional` for each optional the way the
     resolver does, so a non-CDI module no longer lists `java-quarkus` or `junit-weld-testing` as optionals for
     phase-4's description match. A module whose extension carries no hook keeps defaults only (the resolver's
     rule); the `ExtensionBase` default of `True` stays. The `--module` step in `phase-4-plan/SKILL.md` is
     either executed by a script or **removed**: documentation that names a call no script makes is not an
     executed step. Decide which at outline and record why.

   *Done when:* each of these fails at `0cfc7d3f0`:
   - a non-CDI Maven module's architecture-served optionals do not contain `java-quarkus`;
   - a CDI module's do, through the same architecture path, joined from real discovery (the test goes through
     `get_module_info`, not a union the test builds);
   - `phase-4-plan/SKILL.md` names no call that no script makes.

4. **The remaining read verbs apply the veto, and the exclusion scope is one definition.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `enrich_skills_by_profile` persists the caller's map verbatim, `manage-solution-outline get-module-context`
     returns the raw enriched map, and manage-config `resolve-domain-skills` and `get-skills-by-profile` apply no
     exclusions; they feed the recipe selection flow and the finalize code review. Each applies the repository's
     veto, or the spec's outline records why that verb is not a path to a task's skills and the documentation says
     so. The exclusion read uses one scope everywhere: the caller's `project_dir` when it has one, the execution
     context otherwise (today `extension_base._build_applicable_result` and `_cmd_enrich` differ).
   - Honest tests: `test_bundle_qualified_exclusion_*` and the two round-2 bind tests of PLAN-LB-76 are made to
     fail under a mutation, run and recorded; the "final skills" test goes through `get_module_info` or phase-4's
     own read; the restored `java-quarkus not in` assertion states the exclusion that makes it true.

   *Done when:* each of these fails at `0cfc7d3f0` (verify-at-outline for the verbs the HYPOTHESIS below
   settles):
   - `enrich_skills_by_profile` with an excluded skill in the incoming map does not persist it;
   - `get-module-context` and `resolve-domain-skills` for an excluded default do not return it, or are
     documented as not a task path with a test pinning the documentation;
   - `enrich --project-dir D` and `architecture module` read the same exclusions for the same `D`.

## Claim Labels

- OBSERVED: `_load_config_mapping` returns `{}` for an unreadable or malformed `marshal.json` and for an unimportable loader, and `_skill_domain_exclusions` returns `{}` — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` L783-798, L815-816 at `0cfc7d3f0`.
- OBSERVED: `_cmd_enrich.py` L410-422 prunes the stored map inside `try: … except Exception: pass` — `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py` at `0cfc7d3f0`.
- OBSERVED: `is_excluded` returns `any(exclusion.split(':', 1)[-1] == skill …)` for a bare skill, so a qualified exclusion of any bundle removes a same-named bare skill — `extension_base.py` L938 at `0cfc7d3f0`.
- OBSERVED: `_build_applicable_result` applies exclusions only and never calls `qualifies_optional` — `extension_base.py` L1418-1446 at `0cfc7d3f0` (landing analysis of PLAN-LB-76; read by the corroboration).
- OBSERVED: `phase-4-plan/SKILL.md` was relabelled "Run the resolver as an executed step" and no script makes the call (landing analysis of PLAN-LB-76).
- OBSERVED: `_cmd_enrich.py` L580-590 `enrich_skills_by_profile` persists the caller's map verbatim; `manage-solution-outline` L1516-1517 `get-module-context` returns the raw enriched map; manage-config `_cmd_skill_resolution.py` L81-95 and L138-213 apply no exclusions (landing analysis of PLAN-LB-76, read by the corroboration; not re-read by the orchestrator).
- OBSERVED: `test_bundle_qualified_exclusion_*` was written after the fix and never ran red — `test/plan-marshall/manage-personas/test_skill_binding.py` L293-300.
- HYPOTHESIS: a bare skill in a cell belongs to the cell's own bundle, so a qualified exclusion of the same bundle removes it and any other bundle's qualified exclusion does not — confirm at `_entry_skill_notation` and the cell shapes in `extension_base.py` before D2 is labelled (verify-at-outline).
- HYPOTHESIS: `enrich_skills_by_profile`, `get-module-context`, `resolve-domain-skills` and `get-skills-by-profile` can feed a task's skills (the recipe selection flow pre-checks defaults; finalize code review reads the map) — confirm or refute at `recipe-refactor-to-profile-standards/workflow/selection-flow.md` L84-156 and `phase-6-finalize/workflow/code-review.md` L141-144 (verify-at-outline); D4's clauses are labelled after it is settled.
- Verify-first clause: decide whether a caller blocks or warns when the exclusion read fails (D1) and whether the `--module` step is executed or removed (D3), before either deliverable is scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` — `_load_config_mapping`, `_skill_domain_exclusions`, `is_excluded`, `_build_applicable_result` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py` — the import guard and `_excluded_skills`/`_is_excluded` delegation (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py` — the swallowing `except`, `enrich_skills_by_profile` (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — the unfiltered return (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_resolution.py` — `resolve-domain-skills`, `get-skills-by-profile` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` — `get-module-context` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — the `--module` step (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md` and `marketplace/bundles/plan-marshall/skills/manage-personas/SKILL.md` — the narrowing sentence (D2)
- OBSERVED: `test/plan-marshall/manage-personas/`, `test/plan-marshall/manage-architecture/` and `test/pm-dev-java/plan-marshall-plugin/` — the fixtures of D1 to D4

## Dependencies and Sequencing

- Depends on: PLAN-LB-76 (shipped, `0cfc7d3f0`).
- Overlaps with: the staged PLAN-LB-51 on the `phase-4-plan` tree; PLAN-LB-43 on `extension-api/` only if D3 adds a hook there. The gate will ask.
- Adjacent to: `manage-config` `excluded_skills` (the key's write path stays as shipped).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-80-lb-76-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
