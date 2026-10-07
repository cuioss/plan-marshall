# PLAN-090: Harness and Rule Gaps

epic: test-quality
workstream: WS-03

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-090.md`](../landings/PLAN-090.md),
> and the full original brief plus every run report is under
> [`archive/090-harness-and-rule-gaps/`](../archive/090-harness-and-rule-gaps/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Own the production and harness surface every reduction plan is forbidden to touch. Four consecutive
reduction runs each found the same blockers — a script with no parser seam, a loader that cannot address a
bundle skill's root-level `extension.py`, an analyzer whose regexes miss the spellings the tree actually
uses — recorded them, and could not close them. Close them here. Two runs.

## Deliverables

1. D1 — publish a `build_parser()` seam on the `script-shared` build CLI and on `credentials.py`.
2. D2 — add `load_skill_module` / `get_skill_dir`, addressing a skill-root `extension.py`.
3. D3 — a `register=False` escape plus a growth-check guard for `sys.modules` registration collisions.
4. D4 — widen `_PLAN_DELIVERABLE_ID_RE` and `_PR_REFERENCE_RE` to the spellings the tree uses.
5. D5 — measure the `no-lesson-id-in-skill-prose` false-positive rate and decide on importing the sibling
   rule's literal-span exemption.
6. D6 — name the helper by role rather than by path in `conftest.py`'s `_routing_namespaces` docstring.
7. D7 — report the per-rule deltas and the severity ladder.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/credentials.py` — D1
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/` — D4, D5
- OBSERVED: `test/conftest.py` — D2's accessors, D3's escape, D6's docstring. ⛔ **loader mechanics only**
- OBSERVED: `test/plan-marshall/script-shared/test_conftest_loader_contract.py` — D3's guard
- OBSERVED: the tests for this plan's own production changes, only where a change requires one

## Dependencies and Sequencing

- Depends on: nothing. It was a blocking prerequisite for the **B6**/**B7** halves of PLAN-070 and PLAN-080,
  both of which have landed, so that sequencing is spent.
- Overlaps with: PLAN-110 (`test/conftest.py`, different halves — this plan owns the loader mechanics,
  PLAN-110 the session preflight and skip guard); PLAN-105 § D3 and § D7, PLAN-145, PLAN-160 and possibly
  PLAN-120, all of which reach into `marketplace/bundles/**`.
- Adjacent to: every reduction slice, which records a defect here and never fixes one.

## Hand-Off Command

Not emittable — this plan has landed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
