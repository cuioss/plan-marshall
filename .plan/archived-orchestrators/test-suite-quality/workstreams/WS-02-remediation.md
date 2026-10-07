# WS-02: Remediation

epic: test-suite-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-remediation.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the source-mutating remediation of the test suite, driven by WS-01's map. Two remediation efforts:
bring test packages into `pm-dev-python:pytest-testing` standards compliance (including unified
bootstrapping and shared fixtures), and propagate the test-hardening patterns already landed by a
parallel effort across the whole suite. Closes when the targeted packages comply with standards and the
hardening patterns are consistently applied wherever the same failure modes exist.

## Scope

- In scope: mutation of `test/**` source; running the refactor-to-profile-standards recipe
  package-by-package; unifying `conftest.py` / shared-fixture helpers; auditing and propagating the
  parallel-plan hardening patterns (timeout backstop coverage, synchronous-seam-over-`asyncio.run`,
  CWE-117 control-char log-injection guards, best-effort attribution, gc-format round-trip guards).
- Out of scope: the discovery/analysis pass itself (owned by WS-01); production-source behavior changes
  beyond what a test refactor legitimately requires.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-test-standards-compliance | staged | Refactor test packages to pytest-testing standards; unify bootstrapping/fixtures |
| PLAN-03-propagate-parallel-plan-hardening | staged | Adapt landed timeout/hang-fix/log-injection/time-bomb hardening patterns suite-wide |
| PLAN-04-runtime-dependency-modernization | staged | Bump+pin capped deps; resolve local-vs-CI Python-floor divergence; warnings-as-errors + strict-markers gates (later plan) |
| PLAN-05-duration-coverage-remediation | staged | Capstone: act on baseline hotspots + coverage-gap map for demonstrable duration+coverage gains (final toolchain) |

## Sequencing and Surface Notes

- Both WS-02 plans depend on PLAN-01's map and both MUTATE `test/**`, so they are NOT surface-disjoint
  by default and must be sequenced — unless PLAN-01's map assigns them provably disjoint test packages,
  in which case `next` may pair them. The disjointness verdict is deferred to a `next`-time decision
  informed by PLAN-01's output.
- PLAN-03's natural surface is the async/subprocess/log-emitting test subset (anchored on
  `test/plan-marshall/build-server/`); PLAN-02's recipe runs package-by-package across the broader tree.
