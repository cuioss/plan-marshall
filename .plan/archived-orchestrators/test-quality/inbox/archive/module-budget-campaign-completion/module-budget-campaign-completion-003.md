envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=finding
created=2026-09-23T10:56:04Z

# PLAN-182 carve 1 interim: verify running server-side under contention

Plan `module-budget-campaign-completion`, first carve
(`test_shared_harness.py` → 4 units + `test/_shared/` fixtures promotion).

- Pre-push gate went red twice and was repaired in the open: TEST_ROOT
  relocation semantics (fixed, parent.parent) and operator-approved fixture
  promotion to `test/_shared/` (mypy explicit_package_bases resolves bare
  imports only via mypy_path). test-compile green since.
- Freshness gate then refused twice on scope: `.py` footprints require
  test+compile+lint in ONE row, so module-tests-only and quality-gate-only
  rows are narrow. Full `verify` dispatched with explicit --timeout 900→1500.
- Full-suite wall time measured across the day: 372s (quiet) → 377s →
  468s daemon-kill → 600s+ client-kill → 675s green → 806s green. Daemon job
  volume rose 9x (10 → 90 jobs/15min). `ps` shows three concurrent full-tree
  pytest runs on one box (this plan 22:29 elapsed, truth-147 18:51,
  plan-06 05:07) — contention, not tree growth (population steady 27640).
- The client ceiling killed my wrapper but the daemon job SURVIVED: the
  plan's pytest is alive server-side. Waiting for its row to land rather
  than launching a fourth concurrent suite.

## Landing-facts (partial, no PR yet)

- plan: module-budget-campaign-completion (phase 6-finalize, push barrier held)
- commits: c20cc4c07 carve, 0a5004623 fixtures promotion + TEST_ROOT fix
- fidelity: 21/21 identities, lost=0, gained=1 documented presence-guard
- green evidence: module-tests 27640 (806s), quality-gate whole-tree,
  test-compile; pending: verify row at current SHA
- pr: none yet
