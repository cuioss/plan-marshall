# PLAN-04: One vocabulary for "the name of the thing I am operating on" — the decision

epic: orchestrator-refactor
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-identifier-vocabulary-decision.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Derive the full population of top-level identifying CLI parameters across the marketplace,
decide ONE vocabulary for the "name of the thing I am operating on" role, and land that
decision as an amendment to the standard that governs it plus an ADR. This plan renames
NOTHING. Its output is a settled, enforced convention and a sized execution brief. It is a
separate plan from execution (PLAN-05) because the decision contradicts a live, mechanically
enforced standard, and because the execution surface is two orders of magnitude larger than
the decision surface.

## Deliverables

1. **D0 — GATE: derive the population.** Every top-level identifying parameter across every
   registered script, from the argparse surface, not from text search. Partition into: names
   an entity the command operates on; names something else. Publish both partitions and the
   criterion. Include the occupied-spelling set (`--name`, `--id`, `--epic`, `--target`) with
   each occupant's current meaning.
2. **D1 — the decision**, stated as a rule with its rationale, covering at minimum: what the
   epic name is called; whether the plan id collapses into it; what happens to the four
   existing `--name` occupants; and how the two "orchestrator" entities (the epic-orchestration
   tier and the plan-lifecycle orchestrator) are told apart.
3. **D2 — the standard amendment.** `argument-naming.md` Rules 1 and 3 and the canonical-forms
   table are brought into agreement with D1, or D1 is narrowed to fit them. A standard that
   contradicts the decision is the defect this plan exists to prevent.
4. **D3 — an ADR**, because the decision outlives this epic and the next script author needs
   the reasoning, not the diff.
5. **D4 — the execution brief**: the sized surface, the ordering, and the survivor-sweep method
   the execution plan (PLAN-05, and its fleet-wide successor) will use, given ADR-007's
   recorded absence of a rename-survivor detector.

## Non-Goals

- No flag is renamed. No doc is swept. No script changes behaviour.

## Claim Labels

- OBSERVED — `persona-plan-marshall-agent/standards/argument-naming.md` (249 lines) is
  normative and enforced. Rule 1 (lines 19-33) prescribes `--plan-id` for a Plan and reserves
  `--id` for untyped contexts. Rule 3 (lines 57-61) prescribes `--module` over `--name` and
  reserves `--name` for "generic strings whose referent is unambiguous… (for example, naming a
  brand-new entity at creation time)".
- OBSERVED — enforcement is `ARGUMENT_NAMING_NOTATION_INVALID`, `_SUBCOMMAND_UNKNOWN`,
  `_FLAG_UNKNOWN` and `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` in
  `pm-plugin-development:plugin-doctor:doctor-marketplace` (standard lines 233-242); the last
  "cross-checks every row above against the live argparse declarations and fails on drift". A
  rename that does not amend the standard's 40-row canonical table fails `verify`.
- OBSERVED — one value, the epic name, has FOUR spellings across FOUR scripts:
  `orchestrator.py:4113` `--slug`; `platform_runtime.py:453` `--slug`; `manage-status`
  `--plan-id` with `--store orchestrator` (`manage-status.py:32-33`, `:135-136`; handlers read
  `args.plan_id`); `manage-logging` `--plan-id` (`manage-logging.py:171-177`, `:226` error
  text: "--store orchestrator requires --plan-id (the epic slug)"); and
  `epic-surface-partition.py:768,776,784,798` `--epic`.
- OBSERVED — `platform_runtime.py` declares `--plan-id` (`:439`) and `--slug` (`:453`) on the
  SAME subparser, for two different entities. A naive collapse to one spelling is an argparse
  conflict there, not merely a semantic one.
- OBSERVED — `--name` is already occupied in 4 scripts, with different meanings:
  `manage-run-config/run_config.py:1463` (a git author name, `commit-trailer set --name`),
  `doctor-marketplace.py` (component-name CSV filter, ×2),
  `script-shared/query/query-architecture.py` (module/entity name, ×3),
  `tools-input-validation/input_validation.py` (generic validated string).
- OBSERVED — scope floor: the literal `'--plan-id'` appears in 38 source files; `--plan-id`
  appears in 215 distinct documentation files, with `phase-6-finalize/standards/branch-cleanup.md`
  at 113 occurrences, `phase-6-finalize/SKILL.md` at 99, `phase-5-execute/SKILL.md` at 86,
  `manage-status/SKILL.md` at 83, `workflow-integration-git/SKILL.md` at 77, and
  `argument-naming.md` itself at 36. `--slug` appears in 2 source files and 19 doc files.
- OBSERVED — `truthful-signals/epic.md:3397-3405` records a LIVE, still-open watch that
  "orchestrator" already names two entities confusably, with dated operator evidence
  (2026-07-29: the operator asked which entity was meant), asking the renaming plan to either
  avoid the tier vocabulary or rename the tier in the same change. PLAN-TRUTH-015 shipped as
  PR #1162; the watch did not close.
- OBSERVED — ADR-007 classifies a rename as "a deletion plus an addition; the stale references
  to the old name are exactly the deleted-symbol case", and records that the deleted-symbol and
  deleted-path classes have NO dedicated whole-surface detector. A rename of this size has no
  automated survivor sweep behind it.
- HYPOTHESIS — the 38-source-file figure is a FLOOR, not the population: `manage-tasks`,
  `manage-references`, `manage-execution-manifest`, `manage-metrics`, `manage-plan-documents`
  and `manage-solution-outline` all take `--plan-id` per the canonical table but do not contain
  the literal `'--plan-id'` string. Confirm/refute by deriving the surface from
  `script-shared/scripts/argparse_surface.py` rather than by text search (verify-at-outline;
  this IS D0).
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Floor re-confirmed at HEAD: architecture search --content --pattern '--plan-id' --literal --category source returns count:39/file_count:39/files_scanned:478. Of the six scripts the claim names as declaring --plan-id without the literal, five are absent from that set; only manage-execution-manifest appears. ADR-023:35-36 records the authoritative D0 method -- driving --help recursively through argparse_surface yields 503 distinct long flags across 111 notations, not text search.
- HYPOTHESIS — the epic name and the plan id are genuinely different entities and should NOT
  collapse to one spelling even under a unified vocabulary; confirm/refute at
  `platform_runtime.py` § the `push-title-token` subparser, where both are required together
  (verify-at-outline).
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Settled affirmatively and re-derived live. ADR-023:147-152 (b) The plan does NOT collapse into that spelling -- --plan-id stays, at all 282 of its sites. Cited live site survives with a +39 shift: platform_runtime.py:482 builds session push-title-token parser, --plan-id at :483 (default=None), --slug at :497 (default=None), with a --store-keyed post-parse mutual-exclusion check at :499-510 -- not jointly argparse-required, per ADR-023:144-145.
- Verify-first clause: do NOT treat `truthful-signals` PLAN-TRUTH-124 (superseded, never
  shipped) as prior art for this plan. Its subject is VERDICT vocabularies (58 declared
  constants across 24 skills), not identifier argument names. Its live successor is
  PLAN-TRUTH-146. Confirm this boundary at outline rather than folding the two.
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Boundary holds exactly. git ls-files truthful-signals/plans returns 46 specs (up from 45). PLAN-TRUTH-124 absent. PLAN-TRUTH-146 present -- its subject is findings-ledger verdict vocabulary, not identifier argument names; do not fold the two.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md`
- OBSERVED: `doc/adr/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-05 (`argument-naming.md` — PLAN-04 amends the standard, PLAN-05 amends
  the canonical-forms table rows against it; sequential by construction, PLAN-05 depends on
  PLAN-04's decision, but the file is shared so never run concurrently); PLAN-03
  (`plugin-doctor/references/rule-catalog.md` — not caught by the automated disjointness
  matcher, see WS-02's charter note; sequence rather than parallelize).
- Adjacent to: none beyond the above.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-04-identifier-vocabulary-decision.md"
```

## Write-Boundary

The plan implementing this spec touches only repository standards, ADRs, and (read-only) the
argparse surface. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message — the orchestrator owns every other ledger write — and reports its outcome through its
PR and its inbox message. The inbox exception's qualifiers and the sole sanctioned write
mechanism are stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
