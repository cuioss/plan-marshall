# PLAN-LB-71: The runbook lane's skill check, build classifier and weakened rules are completed

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-71-lb-67-completion.md` and is queued as one row file, `queue/PLAN-LB-71.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-67 (#1813, `f4b4ebd59`),
> `landings/PLAN-LB-67.md` § Deliverable Fidelity. PLAN-LB-67 counted six deliverables met; three
> are partial. **Each deliverable is its own outline deliverable, and each Done-when is its own
> success criterion. Do not merge them.** Grade each deliverable against THIS spec's Done-when
> text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-67 put the standing review authorization, the per-deliverable skills and persona, the
docs-only build path and the ten restored rules into the `runbook-lane` skill. Three of its six
deliverables are partial, and one defect would stop every OpenCode run once the install is synced:
the skill-existence check cannot find a skill in a flat deployment, so any spec that names
`Skills:` or a `Persona:` fails closed with `named_skill_not_found` outside this repository and the
nested Claude cache. The docs-only classifier fails open on a file that exists, and the rule
restoration left two contradictions and a softened rule behind. This plan fixes those, each
against a fixture that fails at `f4b4ebd59`.

## Deliverables

1. **The skill-existence check resolves a named skill in every deployed layout.** Graded **high**.
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_skill_exists` and `_declared_persona` (`runbook_lane.py:167-202`, `:258`) resolve a bare name,
     and a persona with its bundle prefix dropped, against the lane's own `skills/` directory. In
     the flat OpenCode and Antigravity installs the deployed directory is
     `{bundle}-{skill}` (for example `plan-marshall-persona-implementer`), so every name misses.
   - A name carrying its bundle (`plan-marshall:persona-implementer`) is resolved through the
     existing bundle resolvers (`marketplace_bundles.resolve_bundle_path` and the flat
     `deployed_layout.resolve_skill_path`), never through a path assembled by hand. A bare name
     resolves in the lane's own bundle through the same resolvers. The persona keeps its bundle
     instead of dropping it.
   - No new path logic is written.

   *Done when:* each of these fails at `f4b4ebd59`:
   - a fixture flat install (`{root}/skills/plan-marshall-persona-implementer/SKILL.md`, the lane at
     `{root}/skills/plan-marshall-runbook-lane/scripts/`) resolves `plan-marshall:persona-implementer`
     and the bare `persona-implementer` for a spec naming both;
   - a fixture nested, versioned cache resolves a skill from ANOTHER bundle
     (`pm-dev-python:python-core`);
   - the source tree resolves the same names;
   - a name present in none of the three layouts returns `named_skill_not_found`, naming every probed
     path;
   - the pass-case test names skills in at least two bundles, not only the lane's own.

2. **The docs-only classifier derives its rule from the project and never fails open.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `fnmatch` matching treats `**` as a globstar: `test/**/*.md` matches `test/README.md`. A path the
     classifier cannot match against the project's rule is `buildable`, so an unreadable or
     unmatched rule costs a local build and never skips one the CI would run.
   - The footprint source is the project's CI opt-in that `resolve` already reads; the workflow
     filename and the non-building classes are not repeated as literals in the script. Where the
     project declares no opt-in, the architecture's module directories decide, as today.
   - The tests read the real workflow file of this repository for the matching cases.

   *Done when:* each of these fails at `f4b4ebd59`:
   - `build-classify` on a diff containing only `test/README.md` reports `buildable`;
   - a diff containing only `marketplace/README.md` reports `buildable` when the rule's glob is
     `marketplace/**/*.md` and the file sits directly under `marketplace/`;
   - a diff containing only `doc/developer/build.adoc` still reports `docs-only`;
   - a rule that cannot be read reports `buildable`, with the reason;
   - the classifier source contains neither the workflow filename nor a hard-coded list of
     non-building suffixes (a test greps the module).

3. **The rules PLAN-LB-67 D6 restored read the same everywhere and the parity tests can fail.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `SKILL.md` §1 (`:215-216`) says the guard state rides the facts block; §8 says it travels as
     prose beside the fence. Both say the §8 form.
   - The branch rule names the closed prefix set again (`feature/`, `fix/`, `chore/`) with the
     project's configured prefix as the only extension the resolve result returns, not "the project's
     own set wins" over the canonical three.
   - §6 step 6 ("for ANY required reviewer that refuses on quota") names the §7 condition: the
     10×90-minute loop applies only while no qualifying review exists.
   - The parity keywords can fail: the `never sleep` keyword is the qualifier-free sentence, and the
     build-timeout test fails on the 1800 fallback by proving the value came from the architecture's
     stamp.

   *Done when:* each of these fails at `f4b4ebd59`:
   - a test asserts that §1 and §8 give one location for the guard state;
   - a test asserts the branch rule lists the three canonical prefixes as a closed set;
   - a test asserts §6 step 6 names the "no qualifying review" condition;
   - the `sleep` parity test fails when "bare" is put back in front of it;
   - the timeout test fails when `resolve` returns the fallback while the architecture stamp holds a
     different value.

## Claim Labels

- OBSERVED: the existence check resolves a bare name only against the lane's own `skills/` directory, and a bundle-qualified name through the bundle resolver — `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` L167-202.
- OBSERVED: the flat OpenCode install names skills `plan-marshall-{skill}`, with no bare directory — `/home/oliver/.config/opencode/skills/plan-marshall-persona-implementer` exists and `…/skills/persona-implementer` does not (live check at this checkout).
- OBSERVED: `test/README.md` exists at `f4b4ebd59` (`git ls-tree`), and `fnmatch` does not match it against `test/**/*.md`, so the classifier calls it docs-only.
- OBSERVED: `SKILL.md` §1 (`:216`) says the facts block reports `guard: none on this harness (unenforced)`, while §8 (`:488`) says the state travels as prose beside the fence — landing audit of PLAN-LB-67.
- OBSERVED: the pass-case test for the existence check names only skills in the lane's own bundle, so the cross-bundle path is untested — `test/plan-marshall/runbook-lane/test_runbook_lane.py`.
- HYPOTHESIS: `deployed_layout.resolve_skill_path` resolves the flat `{bundle}-{skill}` names, so D1 reuses it with no new path logic — confirm at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` § `resolve_skill_path` (verify-at-outline).
- HYPOTHESIS: the classifier's workflow filename and non-building classes can be derived from the `resolve` footprint source, so the script holds no literal — confirm at `runbook_lane.py` § `_FOOTPRINT_WORKFLOW`, `_NON_BUILDING_PREFIXES` (verify-at-outline).
- Verify-first clause: the Antigravity flat layout. Confirm its skill directory naming before the D1 fixture is written; do not assume it equals OpenCode's.
- Verify-first clause: decide whether D2's "unreadable rule → buildable" reuses an existing fail-closed helper or adds a reason field to the verb's output. Record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_skill_exists`, `_declared_persona`, `build-classify` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — §1, §4, §6 step 6, §8, the branch rule (D2, D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — fixtures for the layouts, the classifier and the parity tests (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` — reused, read only (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: PLAN-LB-67 (shipped, `f4b4ebd59`).
- Emit **before** any `/sync-harnesses` of the OpenCode install is followed by an emit of a spec that
  carries `Skills:` lines: until D1 lands, the lane stops on `named_skill_not_found` in a flat install.
- Overlaps with: no running or staged plan on a file. PLAN-LB-48 D2 owns the `Task` → `subagent`
  alignment that PLAN-LB-67 left unfinished, so it is not repeated here.
- Adjacent to:
  - `marketplace/bundles/plan-marshall/skills/runbook-lane/` is the surface of PLAN-LB-69 D4 only
    through the orchestrator template lines, which this plan does not touch.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-71-lb-67-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
