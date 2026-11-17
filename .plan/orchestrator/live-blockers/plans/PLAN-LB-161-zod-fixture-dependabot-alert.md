# PLAN-LB-161: Clear the Dependabot alert on the `zod` pin in the build-npm workspace fixture

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

GitHub reports one open, high-severity Dependabot alert on the default branch (alert 1, GHSA-mrhx-c7xc-m3w5 / CVE-2023-54404: `zod` can exhaust memory while validating oversized constrained collections; vulnerable range `< 4.6.6`, first patched `4.6.6`). The manifest it points at is a test fixture, not project code: `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json` declares `"zod": "^3.22.0"`, a range that sits entirely inside the vulnerable one. The fixture is never installed and carries no lockfile, so nothing is exposed at runtime; the alert stays open until the manifest no longer declares a vulnerable range. This plan moves the pin to the patched line and changes nothing else.

## Deliverables

1. The fixture manifest `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json` declares `zod` at a range whose lowest version is `4.6.6` or later (the outline picks the form, `^4.6.6` being the straightforward one, and records why). Every other line of the manifest, and every other fixture file in the workspace, is unchanged. The `build-npm` test suite passes unchanged: no test asserts the version string, and `test_external_dependencies_produce_neither_edges_nor_notes` and `test_full_edge_set_is_exactly_the_declared_internal_dependencies` still hold because `zod` names no workspace module.
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The change is the one manifest line. No test is edited, no lockfile is added, and no other fixture is touched; if the outline finds a test that reads the `zod` range, it hands that back as a finding instead of widening this plan.
- No dependency is installed and no network call is made by the plan: the fixture is data for the discovery and derivation tests, not a buildable package.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Not decided here: whether Dependabot should be configured to ignore, group or update test fixtures. The alert exists because the fixture is a tracked `package.json`; that is the operator's call and no part of this plan.

## Claim Labels

- OBSERVED (read via the GitHub API on 2026-11-17): alert 1 is `open`, severity `high`, ecosystem `npm`, package `zod`, scope `runtime`, vulnerable range `< 4.6.6`, first patched `4.6.6`, manifest `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json`.
- OBSERVED (re-read at `6b9a879e4`): the manifest's dependencies are `@sample/core` (`workspace:*`), `unnamed` (`^1.0.0`) and `zod` (`^3.22.0`) — `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json` lines 4-8.
- OBSERVED (searched at `6b9a879e4`, `git grep -i zod` over tracked files outside `.plan/`): `zod` appears in that manifest and in one test docstring, `test/plan-marshall/build-npm/test_npm_derivation_resolver.py` line 162; no test asserts a version for it.
- OBSERVED (listed at `6b9a879e4`): the fixture workspace tracks five files, all `package.json`; there is no lockfile to regenerate.
- HYPOTHESIS: the derivation and discovery code reads an external dependency's range only to decide it names no workspace module, never to parse or compare it — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-npm/scripts/` (the derivation resolver and `_npm_cmd_discover.py`) and by running the `build-npm` tests after the edit (verify-at-outline).
- Verify-first clause: the outline settles that no consumer of the fixture reads the `zod` range; a reader found there refutes the one-line scope and the outline hands it back.

## Expected Surface

- OBSERVED: `test/plan-marshall/build-npm/fixtures/workspace-monorepo/packages/api/package.json`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-160 (running) declares the directory `test/plan-marshall/build-npm/`, which contains this plan's one file, so the two share exactly one file by containment; a single shared file does not block the gate. PLAN-LB-160 edits npm discovery tests and `_npm_cmd_discover.py`, not this fixture manifest.
- Adjacent to: the other three fixture manifests of the same workspace (`packages/cli`, `packages/core`, `packages/unnamed`) and the root `package.json` stay untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-161-zod-fixture-dependabot-alert.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
