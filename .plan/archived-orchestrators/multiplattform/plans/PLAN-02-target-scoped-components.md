# PLAN-02: Target-scoped components

epic: multiplattform
workstream: WS-02

> **HISTORICAL SPEC — this plan has LANDED.** It shipped in the standalone
> `doc/plans/multiplattform/` lane before this ledger existed. This file exists so the queue row has
> a spec and the corpus reconciles in both directions; it is a record, not a brief, and it MUST NOT
> be emitted.
>
> - Original plan: `archive/020-target-scoped-components/plan.md`
> - Run report: `archive/020-target-scoped-components/report-01.md`
> - Landing analysis (ground-truth verified at HEAD `2cd1a19c`): `landings/PLAN-02.md`

## Objective

Give a component a way to declare that it exists on only some targets, so a Claude-only component
stops being emitted to every target — a filter derived from the registry, fail-closed validation, a
first real consumer, and an authoring surface that catches a bad declaration before the build does.

## Deliverables

1. D1 — The filter mechanism (`component_targets.py`, registry-derived, consumed by both component-tree emitters; `pr-agent` inert by its own `emits_bundle_tree = False`).
2. D2 — Fail-closed validation (unknown target name, empty list, list of only non-tree targets; every message names file and value).
3. D3 — First consumer (`tools-fix-intellij-diagnostics.md` declares `targets: [claude]`).
4. D4 — Authoring surface (the `targets-scope-invalid` plugin-doctor rule, registered and wired; `frontmatter-standards.md` § Target Scoping).

## Claim Labels

- OBSERVED: all four deliverables landed as specified — re-derived at HEAD `2cd1a19c` from `component_targets.py`, both emitters, `plugin_json_gen.py`, `pr_agent/target.py`, `_analyze_target_scope.py`, `_rule_registry.py:131`, and `frontmatter-standards.md:417`. See `landings/PLAN-02.md`.
- OBSERVED: the mechanism has exactly **one** real consumer at HEAD — `tools-fix-intellij-diagnostics.md`. Confirmed by frontmatter read and by inspecting the on-disk `target/claude` and `target/opencode` trees.
- OBSERVED: the doctor rule is a deliberate approximation (stdlib-only, no PyYAML on a consumer install) with self-measured completeness of 34.5%; the limitation is disclosed in the module docstring, the rule doc, and `frontmatter-standards.md:460`.
- OBSERVED: a mid-run scope expansion added a `PyYAML>=6.0.3` runtime dependency, operator-authorized and recorded — `pyproject.toml:16`, plus install steps in `opencode-generate-check.yml:30` and `claude-distribute.yml:103`.

## Expected Surface

Historical; recorded for disjointness reads only.

- OBSERVED: `marketplace/targets/**`
- OBSERVED: `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/**`, `.../plugin-architecture/references/frontmatter-standards.md`
- OBSERVED: `pyproject.toml`, `uv.lock`, `.github/workflows/opencode-generate-check.yml`, `.github/workflows/claude-distribute.yml`
- OBSERVED: `test/marketplace/targets/**`, `test/pm-plugin-development/plugin-doctor/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-05 and PLAN-16 (all three touch `marketplace/targets/**`) — sequential
- Adjacent to: `platform-runtime/scripts/**` — untouched (WS-01's surface)

## Hand-Off Command

⛔ None. This plan has landed.

## Write-Boundary

Not applicable — historical record.
