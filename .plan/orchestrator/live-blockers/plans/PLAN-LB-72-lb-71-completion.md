# PLAN-LB-72: The runbook lane's classifier, tests and evidence labels are completed

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-72-lb-71-completion.md` and is queued as one row file, `queue/PLAN-LB-72.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-71 (#1817, `97542abc5`),
> `landings/PLAN-LB-71.md` § Deliverable Fidelity. PLAN-LB-71 counted three deliverables met; D1 and
> D3 are partial and D2 carries a fail-open risk outside this repository. Priority is **medium**:
> nothing here blocks a run in this repository today. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** Grade each
> deliverable against THIS spec's Done-when text; an outline that rewrites a Done-when must say so
> and why.

## Objective

PLAN-LB-71 made the skill-existence check work in a flat install and made the docs-only classifier
globstar-aware. What it left behind: the classifier's skip class now comes from the project's
architecture, not from the CI rule, so another project can have a change classified `docs-only` that
its CI builds; the tests for the existence check and the closed prefix set can pass for the wrong
reason; and the run labelled post-hoc mutation evidence "fail-first" in its PR body and in
`main`'s history. This plan closes those, each against a fixture that fails at `97542abc5`.

## Deliverables

1. **The docs-only classifier never says `docs-only` for a path the project's CI would build.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The non-building class comes from the project's CI rule where it can be read. Where it cannot
     (the rule lives in a reusable workflow the repository does not hold), a path is `docs-only` only
     when it matches the architecture's documentation module prefix AND a closed extension set,
     case-sensitively, and every other path builds. The architecture is a hint that can only make a
     change build, never skip a build.
   - `_glob_to_regex` reuses the existing glob-to-regex helper in `_cmd_manage` instead of
     duplicating it, or the outline records why it cannot.

   *Done when:* each of these fails at `97542abc5`:
   - in a fixture project whose documentation module directory is `docs/` and whose CI rule does not
     name it, a diff containing only `docs/guide.md` reports `buildable`;
   - a diff containing only `README.MD` reports `buildable`;
   - a diff containing only `guide.asciidoc` reports `buildable` unless the CI rule names it;
   - a diff containing only `doc/developer/build.adoc` still reports `docs-only` in this repository;
   - the source-literal test fails when a renamed list of document suffixes (`_DOC_SUFFIXES`) is
     added to the classifier.

2. **The existence-check and rule tests can fail for the reason they name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The probed-path test builds a fixture absent from the source tree, the flat install and the
     nested cache, and asserts the probed path of each layout.
   - A flat fixture names a cross-bundle skill (`pm-dev-python:python-core`, deployed as
     `pm-dev-python-python-core`) and resolves it.
   - A flat `SKILL.md` without a metadata identity returns a named error instead of a silent miss on
     every bare name.
   - The flat candidate loop and the `resolve_skill_path` call in `_skill_exists` are one
     implementation, not a hand-built loop beside a redundant call.
   - The branch-rule test asserts the word "closed"; the wording states which set the prefix must
     come from, consistently with `SKILL.md:92`.
   - The build-timeout test goes through `resolve` with a stubbed architecture, not through the
     extracted seam, so a broken delegation fails it.

   *Done when:* each of these fails at `97542abc5`:
   - the probed-path test fails when one layout's probe path is dropped from the error;
   - a flat fixture resolves `pm-dev-python:python-core`;
   - a flat `SKILL.md` with no identity returns the named error;
   - the branch-rule test fails when "closed" is removed from `SKILL.md`;
   - the timeout test fails when `_cmd_client._augment_resolved` raises, and not only when the seam
     is missing.

3. **The lane's evidence labels and loop rules match what a run did.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - §8 (landing) and the PR-body rule require, per Done-when, an `order` field with the closed
     values `test-first`, `mutation-after` and `none`, and the failing run's commit and output
     identifier. The words "fail-first" and "observed failing before the fix" are reserved for
     `test-first`.
   - §4 states that `test-compile` runs at every head that is pushed to a PR, and the landing
     reports the sha of each run.
   - §5 states that self-review ends when a round lists nothing open, or at the stated round limit
     with the open items reported as such, never as `clear`.
   - The unknown-verb rule is made operational: the landing must record that the operator was asked,
     with the answer, or that no question tool was available.

   *Done when:* each of these fails at `97542abc5`:
   - a doc test asserts the `order` field, its three values, and the reservation sentence in §8 and in
     the PR-body rule;
   - a doc test asserts the `test-compile` per pushed head rule and the sha in the landing report;
   - a doc test asserts `self-review: clear` is not permitted while any finding is open;
   - a doc test asserts the unknown-verb rule names the record in the landing.

## Claim Labels

- OBSERVED: the classifier's skip class comes from the architecture module marked `documentation` and its `doc` extensions, and `_classify_path` lowercases the path — `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` (the PLAN-LB-71 audit, `landings/PLAN-LB-71.md`).
- OBSERVED: the nested-cache and source-tree tests pass at `97542abc5^1` because the base `_skill_exists` already resolved those names — `git show 97542abc5^1:…/runbook_lane.py` L179-202.
- OBSERVED: the PR #1817 body and the squash commit message state "each observed failing before the fix"; the session shows 0 of 15 test-first (audit of PLAN-LB-71).
- OBSERVED: `test-compile` ran once in the PLAN-LB-71 run, at `3217d573b`, and not at either PR head (audit of PLAN-LB-71).
- OBSERVED: the main executor lists only the `resolve` child for the lane — `.plan/execute-script.py` L751 and L861. This is an operator action (regenerate), not a deliverable here.
- HYPOTHESIS: the existing glob-to-regex helper in `_cmd_manage` can be imported from the lane without a layering violation — confirm at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` and `_cmd_manage.py` § `_gitignore_pattern_to_regex` (verify-at-outline).
- HYPOTHESIS: the CI rule of a project that opts in is readable only when the repository holds the workflow; a reusable workflow referenced by `uses:` is not — confirm against `.github/workflows/python-verify.yml` (verify-at-outline).
- Verify-first clause: settle the closed extension set for the architecture-only fallback before D1 is scoped; it must be a subset of every project's likely CI skip set, and the outline records the choice.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — classifier, `_skill_exists`, `_resolve_build_timeout` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — §4, §5, §8, the PR-body rule, the branch rule (D2, D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the tests of D1, D2 and D3
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/_cmd_manage.py` — read only, the glob helper (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: PLAN-LB-71 (shipped, `97542abc5`).
- Overlaps with: no running or staged plan on a file.
- Adjacent to:
  - PLAN-LB-69 D4 (the orchestrator-side `Skills:` lines) reads the same `resolve` output through
    `orchestrator.py` and does not touch the lane.
  - The executor still lacks `build-classify` until it is regenerated; that is an operator action and
    not part of this plan.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-72-lb-71-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
