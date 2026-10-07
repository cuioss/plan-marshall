# WS-05: Suite Integrity

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-suite-integrity.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Two properties of the suite went unmeasured by every plan in the epic's executed half, and one of them
is quietly false: **tests are skipped**, and **nothing measured how long the suite takes**. A skipped
test is a contract nothing checks while the build keeps reporting success — the same false-clean signal
the epic exists to remove, turned on the suite's own reporting. This workstream makes both properties
measurable and then holds them: zero skipped tests on the CI runner with a small, named, guarded
exception set, and a wall-clock figure that a run producing a regression is the run that catches it.

## Scope

- In scope: every skip site under `test/` and its classification; `test/conftest.py`'s session-scoped
  preflight and the guard that fails when a skip appears outside the exception list; the literal
  commands the epic's run conditions 3 and 4 need; and the reverse-order hermeticity arm that needs no
  third-party plugin.
- Out of scope: making CI **faster** — the subject is *not getting slower*, a different and far cheaper
  commitment; any `marketplace/bundles/**` file (WS-03's); splitting a module for the budget (WS-04's);
  adding `pyright-langserver`, `pytest-randomly`, `hypothesis` or any third-party dependency, which is
  a user-approval step a cloud run may not take — the proposal is recorded, the decision is not made;
  deleting a test because making it run is awkward.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-110-every-test-runs-and-the-suite-does-not-slow-down | staged | Seven deliverables; D1 is gating and halting. Builds the instruments the epic's run conditions 3 and 4 rely on |

## Sequencing and Surface Notes

- **`110`'s surface crosses several reduction slices deliberately** — skip sites do not respect the
  epic's partition. It concentrates in `test/sync-plugin-cache/` (~32 sites gated on `git` and `rsync`)
  and `test/pm-plugin-development/` (~12), with scattered others in four more slices. It carries a
  halting concurrency check rather than a claim of disjointness.
- Shares `test/conftest.py` with `090` (WS-03) and `105` (WS-04): `090` owns the loader mechanics,
  `110` the session preflight and skip guard, `105` places instruments in the adjacent `test/_shared/`.
- **Run `110` before the module-budget campaign continues.** The campaign is the change most likely to
  move the wall-clock, and `070`'s outstanding **B6** conversion — roughly 2.3× `080`'s by namespace
  count — is the other. Neither is currently measured.
- **`110` has the epic's only non-git-reachable confirm/refute artifact.** Its CI-timing figures live in
  the GitHub Actions API. A run without API access reports that re-derivation **unavailable** rather
  than substituting a local measurement whose population is not comparable.
- **There is no regression to fix.** Across the epic's entire executed half the suite cost about two
  seconds more while the collected count rose ~1.3%. The instrument is the deliverable; the risk it
  catches is ahead, not behind.
