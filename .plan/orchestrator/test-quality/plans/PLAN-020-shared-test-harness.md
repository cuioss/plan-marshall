# PLAN-020: The Shared Test Harness

epic: test-quality
workstream: WS-01

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the
> queue reconciles both ways; the **authoritative verdict** is [`landings/PLAN-020.md`](../landings/PLAN-020.md),
> and the full original brief is [`archive/020-shared-test-harness/plan.md`](../archive/020-shared-test-harness/plan.md).

## Objective

The corpus keeps re-implementing the same harness: ~197 modules carry their own
`spec_from_file_location` preamble against ~401 uses of the `load_script_module` helper that replaces
them, ~2,900 argument namespaces are hand-built rather than produced by the real parser, and one shared
`create_marshal_json` fixture is defined three times, incompatibly. Build the harness once, in
`test/conftest.py` and `test/_shared/`, so the house style **B4**, **B6** and **B7** are cheap to adopt —
and prove it with a bounded set of conversions rather than by assertion.

## Deliverables

1. `parse_ns(bundle, skill, script, *argv)` — build an argument namespace through the script's **own**
   parser, so it carries the parser's defaults; raise a named error where no seam exists.
2. Collapse the three incompatible `create_marshal_json` definitions into one builder with named presets.
3. Retire `test_helpers.py` to `_manage_config_fixtures.py` per **B10**, repointing every importer.
4. `test/README.md` — the tree's navigation and ownership document.
5. `test/test_shared_harness.py` — meta-tests for `parse_ns`, the presets, and a whole-tree guard that
   the retired name does not come back.
6. Convert **up to** 10 modules across at least 4 subtrees as proof of use, reporting the line delta.

## Claim Labels

- OBSERVED: one shared marshal fixture is defined three times, incompatibly — read across the three
  defining modules at authoring time
  - verdict: corroborated | checked_at: 00b92fca | by: test-quality/cleanup | rescoped: n/a | evidence: re-run at HEAD 00b92fca: grep -rn 'def create_marshal_json' test --include=*.py returns exactly one hit, at test/conftest.py:1916 - same file and same line as the prior check
- HYPOTHESIS: every target script exposes a parser seam `parse_ns` can call — confirm/refute at the
  scripts' own `main()` / `build_parser()` symbols (verify-at-outline)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/cleanup | rescoped: yes | evidence: re-stamped at HEAD 00b92fca, verdict unchanged: the landed run refuted the stated mechanism and shipped main() interception instead; the spec records the contract being met a different way. The re-scope holds

## Expected Surface

- OBSERVED: `test/conftest.py` — `parse_ns`, `create_marshal_json`
- OBSERVED: `test/_shared/**`
- OBSERVED: `test/README.md`
- OBSERVED: `test/test_shared_harness.py`
- OBSERVED: `test/plan-marshall/manage-config/_manage_config_fixtures.py` and its importers
- OBSERVED: ≤10 modules across ≥4 subtrees, chosen at run time as proof of use

## Dependencies and Sequencing

- Depends on: none — this and PLAN-010 are the epic's two roots.
- Overlaps with: none. May run concurrently with PLAN-010 only.
- Adjacent to: every reduction slice, which **consumes** `test/conftest.py` and `test/_shared/**`
  read-only and never edits them.

## Hand-Off Command

Not emittable — this plan has landed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
