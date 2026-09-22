# PLAN-CIS-004: Python and npm Consumer Projects Get a Zero-Edge Graph

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The zero-edge graph is **not** a self-hosting curiosity. Because edge derivation joins on Maven
coordinates and neither `build-pyproject` nor `build-npm` produces them, every Python and npm
consumer project running plan-marshall gets `graph`, `path`, `neighbors`, and `impact` structurally
vacuous — and the `phase-2-refine` feasibility guard dead — while every verb reports success.

Implement native coordinate resolvers for the non-Maven build systems against PLAN-02's seam. This
is the **consumer-facing half** of the derivation fix: plan-marshall targets development projects
generally, not only itself.

## Deliverables

1. A Python resolver deriving internal edges from `pyproject.toml` project names rather than Maven
   coordinates, registered against PLAN-02's seam.
2. An npm resolver deriving internal edges from `package.json` names (including workspace members).
3. Tests proving a multi-module Python project and a multi-package npm workspace both yield non-empty
   `graph` edges and non-empty `impact`.
4. **Documentation.** `doc/concepts/extension-architecture.adoc` — register the native resolvers
   alongside the build-system extension implementations. ⭐ **`doc/user/` matters most for this
   plan**: it is the consumer-facing half of the epic, so a Python or npm consumer must be able to
   read what dependency intelligence they now get without configuring anything. ⛔ Ship docs **in
   this plan**.

## Claim Labels

- **OBSERVED (mechanism)**: `_cmd_client_query.py` derives internal edges by
  `dep.split(':')` → `f'{parts[0]}:{parts[1]}'` joined against `artifact_to_module`, which is keyed
  on `f'{group_id}:{artifact_id}'`.
- **OBSERVED**: `_pyproject_cmd_discover.py` populates metadata with `name`, `version`,
  `description`, `requires_python` — **no `group_id`, no `artifact_id`** — and emits dependencies as
  `f'{dep_name}:runtime'` / `f'{dep_name}:dev'`. ⇒ the join key can never match, so
  `internal_dependencies` stays empty for every Python project.
- **OBSERVED**: `build-npm`'s `_npm_cmd_discover.py` likewise extracts `dependencies` /
  `devDependencies` as compact strings with no Maven coordinate pair.
- **HYPOTHESIS (derived claim)**: the same failure therefore applies to **every** Python and npm
  consumer project, not only to a locally-observed one. This orchestrator verified the *mechanism*
  in both discoverers but has NOT run the graph verb against a real Python or npm consumer repo —
  confirm/refute by running `architecture graph` in one of the known consumer repos
  (`nifi-extensions` for the JS/npm side) and recording `edge_count` (verify-at-outline).
  ⚠ **Do not scope the consumer-facing claim until one real consumer repo has been measured.**
- **HYPOTHESIS**: Gradle may or may not be affected — it emits `group:artifact` coordinates and may
  already work. Confirm/refute at
  `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_discover.py` § the
  dependency-extraction function (verify-at-outline). **If Gradle works, it is a second reference
  implementation, not a third defect** — do not "fix" a working path.
- **Verify-first clause**: the asserted absence — "no non-Maven build system derives internal edges"
  — is an absence claim and carries the higher verification burden. Verify Gradle explicitly rather
  than assuming it patterns with Python and npm.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py`:259-305 — metadata and dependency extraction
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py`:257-300 — dependency extraction
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_discover.py` — verify-only, may need no change (verify-at-outline)
- **OBSERVED**: `test/plan-marshall/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-02 (the seam). Cannot start before it lands.
- ✅ **Surface-disjoint from PLAN-CIS-003** (`build-*` bundles vs `pm-plugin-development`) — MAY run
  concurrently with it once PLAN-02 has landed. This is the epic's best natural pairing.
- ✅ Disjoint from PLAN-01, PLAN-CIS-001, PLAN-CIS-006, PLAN-CIS-007.
- **Adjacent to**: `build_map` oracle consolidation (`plan-optimization` PLAN-35, pending in a third
  epic) touches build-system discovery. ⚠ Not a hard collision, but check that epic's state at
  outline before editing the discoverers.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-004-native-coordinate-resolvers.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
