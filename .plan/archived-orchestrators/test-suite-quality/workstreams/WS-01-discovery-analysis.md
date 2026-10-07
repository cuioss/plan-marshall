# WS-01: Discovery & Analysis

epic: test-suite-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-discovery-analysis.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the up-front, read-heavy investigation that maps the test suite's quality debt before any
remediation touches source. Produces an actionable findings/design artifact — redundancy clusters,
duplicated/divergent fixtures, bootstrapping inconsistencies, and prioritized cleanup opportunities —
that the WS-02 remediation plans consume as their work map. Closes when the analysis artifact is
complete and the remediation plans can be scoped against it.

## Scope

- In scope: read-only analysis across `test/**`; enumeration and clustering of redundant assertions,
  duplicated fixtures, divergent bootstrapping (multiple `conftest.py`, ad-hoc `*_fixtures.py` /
  `*_test_helpers.py` helper modules), and general cleanup candidates; a prioritized remediation map.
- Out of scope: any mutation of test source or production source (owned by WS-02); running the
  standards-compliance recipe; propagating the parallel-plan hardening patterns.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-scrupulous-test-suite-analysis | staged | Map redundancy, fixtures, bootstrapping, cleanup; produce remediation map |

## Sequencing and Surface Notes

- PLAN-01 is the epic anchor: it is analysis-only (no source mutation) and blocks WS-02's remediation
  plans, which consume its map. Because it does not mutate the test surface, it is surface-disjoint
  from everything and could in principle run alongside unrelated work, but its OUTPUT gates WS-02.
