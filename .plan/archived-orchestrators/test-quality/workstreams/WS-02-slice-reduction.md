# WS-02: Slice Reduction

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-slice-reduction.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Apply the house style WS-01 wrote to the test corpus itself, one disjoint slice at a time. The corpus
partitions into **six** slices, each owning a stated, non-overlapping list of `test/` directories, so
all six are mutually parallel by construction once WS-01 has landed. The workstream's outcome is not a
line target — it is a corpus that expresses the same assertions in less text: **B4** arrange in
fixtures, **B5** tables parametrized, **B6** namespaces from the real parser, **B7** one import
preamble, **B3** docstrings stating the invariant rather than its history.

## Scope

- In scope: the six disjoint slices of `test/`, one per plan, each enumerated in its own spec's
  Expected Surface.
- Out of scope: `test/conftest.py` and `test/_shared/**` (WS-01's, then shared); any
  `marketplace/bundles/**` file (WS-03's — a reduction run **records** a production defect and does
  not fix it); splitting a module for the 400-line budget (WS-04's — a reduction plan reports its
  over-budget count and does not act on it); any directory outside the plan's own list, even to fix
  something obvious there.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-030-config-and-manifest-test-reduction | landed | Two runs. Collapsed the `test_config_defaults.py` name-shape family; D3 arrange-into-fixtures never started |
| PLAN-040-delivery-pipeline-test-reduction | landed | D2 fixture corpus unstarted; D3 subprocess-layer collapse not performed at all — its gating survey licensed none |
| PLAN-050-plan-state-and-records-test-reduction | landed | Two runs. Decomposed the epic's two largest modules into 49 + 15 check-named modules with shared builders |
| PLAN-060-runtime-and-script-substrate-test-reduction | landed | Three runs. D4 parametrization beyond one family unreached; the randomised hermeticity arm unrun (no `pytest-randomly`) |
| PLAN-070-architecture-and-orchestration-test-reduction | landed | The epic's largest remaining **B6** debt — hand-built namespaces against near-zero `parse_ns` adoption |
| PLAN-080-plugin-development-and-generator-test-reduction | landed | Two runs. **B6** closed at 211 of 211 and **B7** at its structural floor; coverage measured in neither run |

## Sequencing and Surface Notes

- All six depend on WS-01 (`010` **and** `020`) having landed. That condition is met.
- The six are **mutually surface-disjoint by construction** and may run concurrently with each other,
  subject to the epic's collision matrix for the cross-slice plans (WS-04, WS-05).
- **The partition is hand-written and nothing derives it.** Every re-entry re-derives it before acting:
  an entry under `test/` claimed by two slices, or by none, is a defect that halts the run. Four
  consecutive runs each halted on `test/pm-code-intelligence/` before it was assigned to `080`.
  WS-06 exists to make this derivation mechanical.
- **The three-part done-when written into `030`–`060` is superseded** by the epic's five run
  conditions; in particular each plan's percentage line floor is retired, because three of the six
  floors exceeded their slice's entire comment-and-docstring volume.
- A follow-up run against a landed plan re-enters it with a new report ordinal and the deliverables
  unchanged. An unstarted deliverable is never read as satisfied — an empty exception list produced by
  not attempting the sweep tells the operator nothing.
