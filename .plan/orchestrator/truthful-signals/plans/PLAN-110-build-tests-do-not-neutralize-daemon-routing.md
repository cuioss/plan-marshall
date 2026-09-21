# PLAN-110: Build-factory tests don't neutralize daemon routing — machine state decides the branch under test

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from a PLAN-105 escalation, after the mechanism was read from source.

## Objective

`test_build_execute_factory.py` and `test_build_queue_slot.py` install their doubles as
**process-local monkeypatches**, then let a **live runtime probe** decide which branch executes. On a
machine with a registered, ready `marshalld`, the factory takes the routed branch, the daemon re-runs
the executor **in its own child process** where none of the patches exist, and roughly eight tests
fail spuriously. Make the routing branch **chosen by the test**, not by machine state.

## The mechanism — OBSERVED, read from source

Not an environment or working-directory difference. The daemon runs in the correct directory; the
divergence is a **process boundary that `monkeypatch` cannot cross**.

1. The tests patch `factory.execute_direct_base` with `_ExecRecorder`, patch `_acquire` /
   `_release_raw` on `_build_queue_slot` with `_QueueDouble`, and no-op `time.sleep` — all in the
   test's own interpreter.
2. `_route_to_daemon()` (`_build_execute_factory.py:289-303`) calls
   `client.run_preflight(...)` and proceeds when it answers `ready`. The module header states the
   rule: *"routed to the marshalld daemon when the project is registered AND the daemon answers a
   verified handshake"*. **No fixture stubs this probe**, so the real one answers inside the unit test.
3. On the routed branch **`execute_direct_base` is never called** — the build is submitted and
   long-polled. `_ExecRecorder.ran` stays `False` and the admission assertions fail.
4. The daemon child imports fresh modules, so the recorder, the queue double and the sleep no-op do
   not exist there. Per the same header, a routed build's slot is **held by the daemon child**, so
   `acquire_calls` / `release_calls` stay empty and the queue-slot assertions fail too.

⇒ **The daemon is behaving exactly as designed.** The unstated assumption belongs to the tests: they
assume the routing probe will say "no". Directory equality was never what made them deterministic —
taking the in-process branch was.

## ⭐ It is NOT a coverage problem — three conditions must coincide

The failure reads as coverage-specific and is not. **OBSERVED, verified at source.** It fires only
when all three hold, and a whole-tree coverage run is simply the first place in a plan's lifecycle
where they do:

1. **The run includes `test/plan-marshall/script-shared/`.** Whole-tree runs always do; a
   module-scoped run (`module-tests {module}`) elsewhere never loads these files at all.
2. **The build is daemon-routable.** `build-pyproject/SKILL.md` § run: *"A build carrying either flag
   [`--env` / `--working-dir`] is never daemon-routable — it falls back in-process under
   `--execution-mode auto`."* An earlier build carrying either flag passed **regardless of daemon
   state**, which is why the defect looks intermittent.
3. **The daemon is live AND registered at that instant.** ⚠ Liveness varies *within* a single run —
   on PR #1040 the daemon died at `17:36:24Z` and every later build fell back silently. **The same
   test can pass at 17:00 and fail at 17:40 with no code change.**

⛔ **Therefore a "skip the coverage step" workaround does NOT avoid it.** `resolve-test-scope` sets
`divergence_possible: true` when the footprint touches shared cross-module test infrastructure,
naming `script-shared/scripts/build/…` explicitly — which is where `_build_execute_factory.py` lives.
Any plan touching this module has its finalize `pre-push-quality-gate` **escalated to whole-tree**,
so the wall reappears later in the run rather than being dodged.

⇒ **D1's population derivation must key on these three conditions, not on "which tests fail during
coverage".** A test that happens to pass today may be passing only because condition 2 or 3 was
absent — that is the same green-for-the-wrong-reason trap D3 guards against.

## Why it matters now

⛔ **The tax is worst exactly when it matters most.** Any plan that MODIFIES `_build_execute_factory.py`
cannot distinguish this ambient failure from a real regression in its own change. PLAN-105 hit this
live and had to stop the daemon to get an unambiguous signal — a workaround for a fixture gap, paid
on every such plan.

## Deliverables

1. **D1 — GATE (mutates nothing): pick the neutralization seam and derive the affected population.**
   Two known-viable options, both already supported by production code:
   (a) patch the routing seam directly (`_route_to_daemon`, or `client.run_preflight`) to return the
   fallback; (b) set the `MARSHALLD_JOB_ENV` re-entrancy guard in an autouse fixture —
   `_build_execute_factory.py:291` short-circuits to `in_daemon_job` **unconditionally**, an
   already-tested path. ⚠ Prefer the seam that neutralizes routing **without asserting daemon
   internals**. ⛔ **Derive the affected test population rather than trusting the two modules named
   here** — any test that reaches the factory or the queue slot without stubbing the probe has the
   same latent dependency.
2. **D2 — apply the neutralization at the shared fixture level**, so a newly-written test in this
   tree inherits it rather than having to remember it. A per-test opt-in repeats the defect.
3. **D3 — a test that fails pre-fix, and is honest about its own precondition.** ⚠ **This is the
   subtle deliverable.** The regression must prove the routing branch is chosen by the test —
   e.g. assert `execute_direct_base` ran even when a preflight-`ready` response is simulated.
   ⛔ A test that merely passes on a machine with no daemon proves nothing: **it is green for the
   same reason the bug is invisible.** Verify the new test FAILS with the fixture removed AND a
   ready probe simulated.
4. **D4 — record the routing dependency where the next author will see it.** A short note in the
   test module docstring stating that these tests neutralize daemon routing and why, so the fixture
   is not deleted as apparent dead weight.

Four deliverables, well under the split guard.

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-28, read at source): the `_ExecRecorder` /`_QueueDouble` /
  `_no_sleep` patch sites in `test_build_execute_factory.py`; the `run_preflight`-gated routing at
  `_build_execute_factory.py` § `_route_to_daemon`; the `MARSHALLD_JOB_ENV` re-entrancy guard; the
  header's "slot held by the daemon child" statement.
- OBSERVED: daemon status at escalation time — `running: true`, `registered: true`, `version: 1`.
- HYPOTHESIS: the failing count is ~8 — **operator-reported, not orchestrator-verified**.
  Confirm/refute by running the two modules with a ready daemon (verify-at-outline). ⚠ **Report the
  measured count, and report it separately from the number of tests examined.**
- HYPOTHESIS: the affected population is exactly these two modules — confirm/refute at D1's
  derivation (verify-at-outline). An asserted ABSENCE of other affected tests is verified exactly
  like an asserted presence.
- Verify-first clause: re-read `_route_to_daemon` at HEAD before scoping. ⛔ **PLAN-105 is modifying
  `_build_execute_factory.py` right now** — if it lands first and moves the routing seam, re-baseline
  rather than proceeding against the line references above. **Verify by SYMBOL, not line number.**

## Expected Surface

- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py`
- OBSERVED: `test/plan-marshall/script-shared/test_build_queue_slot.py`
- HYPOTHESIS: a shared `conftest.py` under `test/plan-marshall/script-shared/` (verify-at-outline)
- ⚠ **Tests only.** No production change is expected — if D1 concludes production code must become
  injectable to neutralize the seam cleanly, that is a scope change to surface, not to absorb.

## Dependencies and Sequencing

- Depends on: ⛔ **PLAN-105 (launched)** — it modifies `_build_execute_factory.py`, the module under
  test here. **Sequence after it lands; never pair.**
- Overlaps with: ⚠ **PLAN-82** also edits the test tree / conftest and is flagged low-compatibility
  for pairing. **Sequence, do not pair.**
- Adjacent to: PLAN-58 (`manage-build-server`) — the daemon lifecycle, deliberately untouched here.
  **This is a test-isolation fix, not a daemon fix**, and must not drift into changing routing
  behaviour to make a test pass.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-110-build-tests-do-not-neutralize-daemon-routing.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
