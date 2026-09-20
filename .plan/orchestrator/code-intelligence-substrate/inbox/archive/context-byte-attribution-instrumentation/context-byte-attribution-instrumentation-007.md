envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=landing
created=2026-08-03T16:49:50Z

## What landed

**PLAN-CIS `context-byte-attribution-instrumentation` — Context-Byte Attribution Instrumentation.**

PR [#1086](https://github.com/cuioss/plan-marshall/pull/1086), merged through the queue as squash `9b689d65bc9c77c1f84f053c468f1bbfa51bc623`. Title: `feat(manage-metrics): add per-phase cache_read byte attribution`. 4 deliverables, 7 tasks, deploy-target stamped `0.1.1292`.

This is the epic's first instrumentation landing: it makes the *composition* of context spend measurable rather than inferred.

- **D1 — `billing-composition` is now a first-party audit check.** `audit-archived-plan-retrospectives` gains a 24th check that re-derives the billing formula and the payload-byte composition from the persisted corpus and reconciles them against the dispatch-boundary ledger. Every emitted figure carries its own population, and a figure any metrics-blind or partial plan contributed to is labelled `floor` rather than presented as a total.
- **D2 — per-phase `cache_read` weight is attributed to entering byte sources.** `Runtime.metrics_normalized_tokens.__doc__` in `runtime_base.py` is the authoritative cross-process contract (`contract.md` and `data-format.md` are its mirrors, never ahead of it); the attribution group is emitted unconditionally inside every emitted phase bucket, so a zero there is a MEASURED zero and `0 == 0` reconciles.
- **D3 — index-answerable exploration is separated from doc-residency.** Three new sub-source fields (`exploration_index_answerable_bytes`, `exploration_doc_residency_bytes`, `exploration_unattributed_bytes`) ride a separate `_EXPLORATION_SUBSOURCE_FIELDS` tuple, deliberately suffixed `_bytes` and not `_result_bytes` so they are excluded from the counter-key drift guards by construction rather than by exception.
- **D4 — every emitted figure names its population.**

## Residue the epic should track

**1. The retrospective withheld 4 medium-confidence proposals; 2 of them are routed by this message, 2 are not.**

`work/fragment-lessons-proposal.toon` carries a `medium_confidence_reported_not_recorded` block that the finalize-step confidence bar kept out of the inbox. Two of those four sit inside this step's own signal population and ride as `candidate-lesson` messages alongside this landing (the argparse-rejection cluster, and `.claude/skills/` being unregistered in the architecture inventory). The other two are recorded here so they are not lost with the plan directory:

- `plan-marshall:manage-execution-manifest` — `sonar-roundtrip` was mis-pruned for `execution_profile=standard` even though the realized footprint touched 4 production `.py` files, so Sonar new-code analysis never ran on this change.
- `plan-marshall:plan-marshall` — `config_hash` drift fired at 4 of 4 phase boundaries. A warning that fires at 100% of boundaries is not a detector.

**2. This plan's own metrics are under-reported, which matters because this plan is the instrumentation.**

Four of the six routed candidate-lessons are defects in the very measurement substrate this epic exists to build: the four per-dispatch context-load columns have no producer anywhere in the tree; `6-finalize` never closes so ~1.16M tokens never fold into `metrics.toon` (a ~34% under-report); `2-refine` and the `q-gate-validation` spawns record no dispatch boundary at all; and `plan-retrospective`'s session capture overwrote the execution `session_id`. Read together: **the first measurement this epic shipped cannot yet measure itself.** Any figure this epic quotes from a pre-fix plan is a floor, not a total.

**3. Verification band.** Whole-tree `module-tests` timed out locally at 462s (daemon budget) at HEAD `4e2b7a59` — reached 95% with zero failures before the kill. Recorded as a timeout, NOT as a local pass; CI verify is green at exactly that SHA and runs the same whole-tree chain, which is the covering evidence for the untimed remainder. The scoped `module-tests plan-marshall` arm passed 14826 at the same tree.

**4. Interruption.** Finalize halted once at step 2/22 on a weekly API usage limit and resumed cleanly; branch-cleanup classified `overlap_with_content_conflict` with `conflict_count=7` and went to the operator rather than auto-reconciling.
