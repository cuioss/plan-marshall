# Landing Analysis: PLAN-02 — Target-scoped components

epic: multiplattform
workstream: WS-02
pr: #1313 (squash `66b686bf`, "feat(targets): per-component `targets:` frontmatter scoping, read with yaml.safe_load")

> Landing record for one shipped plan. Lives at `landings/PLAN-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Ingestion note.** This plan shipped in the standalone `doc/plans/multiplattform/` lane before this
epic ledger existed. This record was written at ingestion from a ground-truth verification against
HEAD `2cd1a19c` — the run report (`report-01.md`, 1019 lines, archived at
`archive/020-target-scoped-components/`) was treated as a claim set, and every deliverable was
re-derived from the implementing source and from the on-disk generated trees.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Filter mechanism | shipped-as-specified | `marketplace/targets/component_targets.py` (571 lines) implements `read_target_scope`, `emits_to`, `excluded_emission_roots`, `is_under_any`, `registered_target_names`, `component_tree_target_names` — all derived from `TARGET_REGISTRY` × `emits_bundle_tree`, no target enumeration. Consumers confirmed: `claude/emitter.py:145` → `excluded_emission_roots`; `claude/plugin_json_gen.py:101,132` → `emits_to`; `opencode/emitter.py:509,514,529` → `emits_to` for skills/agents/commands; `claude/target.py:143` → `validate_component_scopes`. `pr_agent/target.py:622` declares `emits_bundle_tree = False` and makes no scoping call — inert by construction, as specified. |
| D2 — Fail-closed validation | shipped-as-specified | `component_targets.py::_validate()` (354–380) rejects an unknown target name, an empty list, and a list of only non-tree targets; every message carries file path and offending value. `test_component_targets.py` (34 test functions) covers all four rejection paths by name. |
| D3 — First consumer | shipped-as-specified | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md:5` reads `targets: [claude]`. On-disk generated trees agree: `target/claude/plan-marshall/commands/tools-fix-intellij-diagnostics.md` exists; `target/opencode/command/` carries no such file. |
| D4 — Authoring surface | shipped-as-specified | `_analyze_target_scope.py` (542 lines) exists and is registered in `_rule_registry.py:131`. `frontmatter-standards.md:417` carries the `## Target Scoping` section with format, a validation table (450–458), the doctor-rule soundness/completeness caveat (460), and the three-condition admission test (464+); cross-referenced from the Agent (99) and Command (151) frontmatter sections and from `## Quality Rules` (688). |

**Mechanism completeness, end to end.** All three legs exist and are wired: **declare** (`targets:`
frontmatter, parsed with `yaml.safe_load` in `component_targets.py::_declared_value`), **generate**
(consumed by both component-tree-emitting targets; `pr-agent` exempt by its own declared capability),
**validate** (the `targets-scope-invalid` doctor rule). The doctor leg is a deliberate approximation —
stdlib-only, because a consumer install has no PyYAML — so it line-scans and stays silent on shapes it
cannot read with certainty. That limitation is disclosed in three places (module docstring, rule doc,
`frontmatter-standards.md:460`), not hidden.

**Descoped: none.** All four deliverables landed as specified. One scope expansion happened mid-run and
was **operator-authorized, not silent**: the hand-rolled line-scanning parser was replaced with
`yaml.safe_load` after verification round 12, adding a `PyYAML>=6.0.3` runtime dependency not
contemplated by `plan.md`. Its consequences are present in the tree — `pyproject.toml:16`,
`types-PyYAML` dev dep, and install steps in both `opencode-generate-check.yml:30` and
`claude-distribute.yml:103`.

## Metrics and Anomalies

- Tokens: not available — standalone cloud plan lane, no `metrics.toon`.
- Duration: not instrumented in that lane.
- Anomalies: **15 verification rounds** — an outlier. The report is unusually transparent about the
  churn; multiple fail-open defects in `component_targets.py` were found and fixed across rounds
  6/10/11, which is itself evidence the module's own degradation default was contested internally.

## Routing and Merge Behavior

- Review: findings dispositioned in-run; the mid-run PyYAML decision was escalated to the operator and
  recorded rather than absorbed.
- CI/merge: merged as squash `66b686bf`. No surface collision observed (nothing ran concurrently).

## Reconciliation Actions

- [x] row `status` → `landed` — seeded at `decompose` (ingestion)
- [x] row `pr` stamped — `#1313`
- [x] row `landing` stamped — `landings/PLAN-02.md`
- [x] row `plan_marshall_plan_id` — `n/a` (standalone lane)
- [x] epic.md queue reconciled from status.json
- [x] Open Defects opened for the residual gaps below
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

1. **`marketplace/targets/` is outside the ruff/quality-gate lint scope.** `pyproject.toml:98` reads
   `lint = "uv run ruff check marketplace/bundles/ test/ .claude/"` — `marketplace/targets/` is absent,
   so a branch-introduced `ruff I001` there passed every check (found by round 15). Left OPEN in the
   report because widening the scope surfaces pre-existing violations outside that plan's ownership.
   → **PLAN-10** (new).
2. **The `targets-scope-invalid` doctor rule's completeness is 34.5%** at HEAD (the report's own final
   self-measurement) — roughly two-thirds of otherwise-invalid `targets:` declarations pass the doctor
   silently and are caught only at build time. Architecturally intentional (soundness over
   completeness under the stdlib constraint) and disclosed in three places, but a real authoring-time
   gap. → **Watch** (revisit if the stdlib constraint changes).
3. **The `marshall-steward` terminal-title and enforcement-hook target-specific candidates remain
   unscoped.** Both are marked in the coupling inventory §D as `Scoped: no — needs the steward skill
   split, which plan 020 left out of scope`. Declared out of scope in `plan.md`, so not a broken
   promise, but the mechanism now exists and its intended consumers do not use it. → **PLAN-11** (new).
4. **Open architecture question, unresolved by design:** is `targets:` the right mechanism, versus a
   per-target ignore manifest? Recorded in the report's § Residue as genuinely open and untouched by
   all 15 rounds. → **Watch**.
5. **The mechanism has exactly one real consumer** (`tools-fix-intellij-diagnostics.md`). That matches
   D3's scope, but it means the mechanism is close to a capability with no users. Folded into the
   PLAN-11 framing above.
