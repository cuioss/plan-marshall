# PLAN-TRUTH-072: The test suite's false-confidence patterns — a runner that reports pass for zero tests

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from `doc/review-26-07-04.md`, which is being retired. Re-verified at HEAD.
> ⭐ **This is the epic's thesis inside the safety net itself.**

## Objective

`test/run-tests.py` executes each test file as a script and treats exit 0 as a pass. Only ~10 of ~545
`test_*.py` files have a `__main__` block that invokes pytest; **the rest import, run zero test
functions, exit 0, and print `✓ passed`.** Pure false-green. Four smaller integrity defects sit
alongside it. This plan removes the false-confidence patterns so the suite's green means something.

## Deliverables

1. **[T1] Kill the false-green runner — *High*.** ✅ **Re-verified: `test/run-tests.py` still exists
   at HEAD.** ⭐ The canonical CI path is pytest via `build.py`, so this is a **developer trap, not a
   CI hole** — which is exactly why it survives: nothing that gates a merge ever notices it.
   ⛔ **Preferred remedy: DELETE it** in favour of the `module-tests` build command. If it is kept, it
   must shell out to `pytest <file>` per file. **A runner that cannot fail is worse than no runner**,
   because it is consulted.
2. **[T6] Delete the dead `sys.modules.setdefault` mocks — *Low*.** ✅ **Re-verified: all 5 files still
   carry them.** `conftest.py` pre-imports the real `plan_logging` / `run_config` first, so every
   `setdefault` is **a guaranteed no-op** — the tests run against the real modules **while implying an
   isolation they do not have.** ⭐ On-theme: the mock is a claim the code does not honour.
   Delete them, or switch to an explicit fixture if stubbing is genuinely intended.
3. **[T7] Normalize developer paths out of fixtures — *Low*.** ✅ **Re-verified: 3 files under
   `test/pm-dev-java/fixtures/` contain `/Users/oliver/…` and 4 under `build-npm/fixtures/` contain
   `/Users/dev/…`.** Leaks a real username and couples any future path-relative assertion to one
   machine. Normalize to a placeholder root.
4. **[T8] Scope the autouse pollution guard — *Low*.** ✅ Re-verified present. It snapshots the real
   credentials dir (`rglob('*')`) and `.plan/local/` **before and after every test**, as a backstop to
   sandbox fixtures that already make those writes structurally impossible — real cost, low marginal
   value, and it reads real developer state. Scope it to credential/plan-touching tests via a marker.
   ⚠ **It was already narrowed once for an O(100k+) regression** (per its own docstring) — so treat
   "it is cheap now" as a claim to measure, not to assume.
5. **[T9] Retire the manual `PlanContext` env save/restore — *Low*.** ✅ Re-verified present.
   `PlanContext.__exit__` mutates process-global `os.environ` and `_config_core` attributes **while a
   newer autouse monkeypatch sandbox does the same thing auto-reverted**. Two overlapping mechanisms
   on one set of globals: an exception between enter/exit, or interleaving with the autouse fixture,
   can leave `PLAN_BASE_DIR` pointing at a torn-down temp dir **for later tests in the same worker**.
   Migrate remaining users to the `plan_context` fixture and delete the manual path.
6. **D6 — a control that proves T1 is closed.** After the fix, a file containing a deliberately
   failing test **must** make the runner (or its replacement) fail. ⛔ **Without this the remedy is
   unfalsifiable** — and an unfalsifiable fix for a false-green is the same defect wearing a fix's
   clothes.

Six deliverables — under the raised cap of 12.

## Claim Labels

- **OBSERVED, re-verified at HEAD 2026-08-09**: T1 (`run-tests.py` present), T6 (5/5 files),
  T7 (3 + 4 fixture files), T8 (`_pollution_guard` present), T9 (`PlanContext` present).
- ✅ **FIXED SINCE THE REVIEW and NOT in this plan** — recorded so nobody re-files them:
  **[T2]** the config-content assertions no longer skip (0 `pytest.skip` at HEAD);
  **[T3]** the plugin-doctor `test_analyze.py` fixture-presence skips are gone (0 at HEAD);
  **[T4]** the `time.sleep` wall-clock dependencies are gone from both named files.
  ⭐ **Three of nine test-integrity findings closed themselves in five weeks** — evidence the suite is
  actively maintained, and the reason each remaining item was re-checked rather than inherited.
- **DROPPED — [T5] "17 helper modules lack direct unit tests"**: not re-derived, and the review itself
  notes **no whole skill directory is untested** and the modules are reachable transitively. A
  coverage-shaped aspiration with a stale population is not a deliverable. ⛔ **If it matters, it needs
  a fresh population and a stated threshold** — file it then, not now.

## Expected Surface

- **OBSERVED**: `test/run-tests.py`, `test/conftest.py`, `test/pm-dev-java/fixtures/**`,
  `test/plan-marshall/build-npm/fixtures/**`, and the five `sys.modules.setdefault` test modules
- ⛔ NOT `marketplace/bundles/**` — this plan changes the harness, never the code under test.

## Dependencies and Sequencing

- Depends on: none. **Disjoint from every currently-running plan.**
- ⚠ `test/conftest.py` is touched by T8 and T9 and is the **highest-traffic shared file in the repo** —
  any plan adding tests concurrently will conflict there. **Do not pair this with a test-heavy plan;
  serialize.**
- ⭐ The review recommends landing test-integrity **first**, so the correctness plans (`-070`, `-071`)
  inherit a trustworthy safety net. **That ordering is endorsed and is the reason this plan is small.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-072-test-suite-false-confidence.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.


---

## ⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 1 message, and it closes the loop on T1

**`daemon-...-009` (candidate-lesson).** *A green build **clears test-failure findings** even when the
command it ran **executes no tests**.*

⇒ ⛔⛔ **This is T1's consequence, observed live and from a different plan.** This spec already carries
the cause — `test/run-tests.py` treats `exit 0` as a pass, so ~535 of ~545 files run **zero** tests and
print `PASSED`. The message supplies what the cause alone does not prove: **the vacuous green is
CONSUMED**, and consuming it **retires real findings**.

⭐ **That changes the severity argument, not just the evidence.** A harness that reports a vacuous pass
is a measurement defect; a harness whose vacuous pass **clears findings** is a mechanism that
**destroys signal that already existed**. The finding was true, was recorded, and was cleared by a
command that tested nothing.

⇒ **Add to this plan's scope: the clearing path must require evidence that tests actually RAN** — a
non-zero executed-test count, not a zero exit. ⛔ And per this spec's own standing rule, **the check
must publish the population it counted**, or it reproduces the defect in its own fix.
