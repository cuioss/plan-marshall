# Landing Analysis: PLAN-03 — Propagate Parallel-Plan Test Hardening

epic: test-suite-quality
workstream: WS-02
pr: #977 — merged as `1cfa37044` (2026-07-22 09:53 UTC, merge queue)

> Landing record. Every material claim was corroborated against the real diff, the real
> tree, and the lessons store before recording. The most significant finding is against
> the orchestrator's own work, not the plan's.

## Deliverable Fidelity vs Spec

The re-scoped spec carried **5** deliverables; **7** shipped. **This is a decomposition, not
scope growth** — shipped 5/6/7 are exactly the three clauses of spec D5 (CWE-117 guards;
best-effort + error-detail-preservation guards; synchronous-seam on the residual `asyncio`
site), split for tracking. Spec D1–D4 map 1:1 onto shipped 1–4.

| Deliverable (spec) | Verdict | Corroboration |
|--------------------|---------|---------------|
| 1. `_test_env` singleton → scoped fixture | shipped-as-specified | `git grep _test_env` on the file now returns **zero** hits; `test_executor_integration.py` −131/+… net simplification; teardown via explicit `pytest.MonkeyPatch()` finalizer |
| 2. Fail-loud cwd guard + `allow_pollution` lock | **shipped-modified — better than specified** | `conftest.py:566` is now a `pytest_runtest_teardown` hook wrapper, not the fixture the spec directed. Escape hatch locked session-wide at `:484`. See "The premise correction" below |
| 3. Skip-guard hardening | shipped-as-specified | in-body `pytest.skip(` count **39 → 15**, i.e. exactly the 24 claimed (19 hard-failed + 5 reshaped). The 15 survivors are precisely the genuine environment guards (real-marketplace, `marketplace/bundles`, real-executor) the spec said to leave |
| 4. Clock-seam + real-sleep defusal | shipped-as-specified | `time.sleep(10)`, `sleep(1.1)`, `sleep(1.05)` all return **zero** hits; `_shared/_poll_until.py` (+54) is the factored helper; `test_orchestrator_store.py` pinned |
| 5. CWE-117 guards | shipped-as-specified | `_sanitize_for_log` + `_CONTROL_CHAR_PATTERN` added at the central sink in `plan_logging.py:format_log_entry`, sanitizing message AND every field key/value at assembly. Hash deliberately computed pre-sanitization so entry identity is stable — documented in-code |
| 6. Best-effort + error-detail-preservation guards | shipped-as-specified | `test_marshalld_audit.py` +61, `test_marshalld_journal.py` +23 |
| 7. Synchronous-seam on residual `asyncio` submit site | shipped-as-specified | new `test_build_server_client.py` (+173) |

**The off-limits boundary HELD.** `pyproject.toml` does not appear in the diff at all, and the
PR body states the exclusion explicitly and correctly. This is the single most important
process result of the landing — see Sequencing below.

**Surface fidelity — the spec's Expected Surface under-declared.** The plan touched three
production sources (`plan_logging.py` +37, `build_server.py` +40, `marshalld.py` +9) and two
marketplace docs (`pytest-testing` SKILL.md + `standards/testing-pytest.md` +18). The spec's
Expected Surface listed test files only. The changes are legitimate — D5 said to add a guard
"where a real injection sink lacks one", and a sink guard lives in production code — but the
spec should have said so. **A guard-propagation deliverable implies a production surface;
declare it.** No collision resulted, because nothing else was in flight.

## The premise correction (D2) — the orchestrator was wrong, the plan caught it

The escalation resolved mid-run directed a migration of ~16–17 test files to
`monkeypatch.chdir`, on the premise that raw `os.chdir` usage was widespread. **That premise
was false and the plan refuted it before paying the cost.** Re-verified here independently:
the tree carries **235** `monkeypatch.chdir` call sites against **11** raw `os.chdir` — the
population was already overwhelmingly correct, matching the plan's reported 236-of-241
pre-fix. The directed migration would have been a near-total no-op.

The real defect was in the guard's own seam: `monkeypatch.undo()` runs *after* fixture
finalizers, so an autouse-fixture guard samples cwd at the wrong instant and false-positives
on correct usage. The fix moved the check into a `pytest_runtest_teardown` hook wrapper — one
file, and the guard was **not** weakened. The final code restores the cwd first (so the next
test is not poisoned) and *then* raises with the offending nodeid.

**What was right and what was wrong, precisely.** The escalation *decision* — hold the line,
do not soften the guard — was correct and survives verbatim in the shipped fix. What was
wrong was the *scope sizing* attached to it: a file count inferred from the symptom volume
(~520 teardown errors) rather than from an enumeration of the actual call sites. One query
would have refuted it.

**This recurrence is recorded against `marshall-orchestrator` itself** — lesson
`2026-07-21-22-001`, now carrying its 5th occurrence and "Widening 3": an escalation
resolution is a staged brief and inherits the verify-before-design obligation. Companion
lesson `2026-07-22-11-001` (`pm-dev-python:pytest-testing`) records the fixture-vs-hook seam.

**And the same defect is present in this epic's own re-scope.** When PLAN-03 was re-scoped
before emission, each scout finding was verified *for existence* ("does `_restore_cwd` still
repair silently?" — yes) but the scout's **population** claim was carried through unchecked:
the emitted spec asserts cwd leakage "has been unattributable across 14 raw `os.chdir()`
sites", which framed a near-clean population as a dirty one. Verification of existence is not
verification of magnitude. The re-scope reported itself as ground-truth-verified while
propagating an unverified count — which is exactly the lesson's signature.

## Metrics and Anomalies

- Tokens **3.2 M**; **4 h 0 m worked / 13 h 17 m wall** — ~7 h of that wall was the D2
  escalation waiting on the operator, plus ~30 min queued behind
  `consumer-upgrade-cache-freshness` on the merge mutex.
- Suite: **14,620 pass / 0 skip / 0 teardown errors**. The 0-skip figure is now *enforced*
  rather than incidental (D3 added the reference-platform assertion).
- Diff: 28 files, **+741 / −249**.
- Review: 3 bots, **0 actionable comments**. Second consecutive plan in this epic with near-zero
  bot yield on a substantial diff (PLAN-02: 2 reviewers, 3 comments, 0 fixes) — the reviewers
  are not finding anything in this epic's test-refactor shape. The value came from the
  retrospective and from the plan's own ground-truth checks instead.
- Self-review found 1 finding, fixed inline; `simplify` made 0 edits.

## Routing and Merge Behavior

- Merge-queue merged; main up-to-date, worktree removed, tree clean. Rebased onto 4 upstream
  commits during `sync-baseline`.
- **No collision.** Main moved several commits during the window (#971, #973, #974, #975, #976)
  and the rebase was clean — consistent with the sequencing call that kept PLAN-04/05 parked.
- **Freshness gate handled honestly.** A docs commit advanced HEAD past the last build,
  staling the push freshness gate. The contract offers a reconciliation record for exactly
  that case; the plan re-ran a 7-minute build instead of back-filling a waiver to unblock
  itself. That is the right call — a waiver written after the fact to clear one's own gate is
  laundering, and the ledger should observe the tree as it is. Recorded as a positive
  precedent, not an anomaly.

## Two process defects the retrospective surfaced (NOT this epic's to fix)

1. **Zero `[DISPATCH]` lines across finalize's 10 dispatched steps** — 4th recurrence of
   `2026-06-24-10-001`. PLAN-02's landing recorded the identical gap ("zero `[DISPATCH]` log
   lines across nine dispatch boundaries"), so this epic has now observed it twice in
   consecutive plans. It makes the dispatch-audit's inverse-coverage check inoperative for the
   phase it guards.
2. **Those 10 error-severity findings were then silently dropped from the report** by a
   registry-key piggyback bug — 26th recurrence of `2026-06-20-17-003`.

Both are finalize/retrospective machinery, not test-suite quality. Recorded as an out-of-epic
watch. The operator's judgment that these need a **fix plan rather than another lesson** is
endorsed: a 26th recurrence is not a knowledge gap.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-03 → `shipped`
- [x] epic.md queue row reconciled
- [x] Baselines & Trend § — CI row added (coverage/duration NOT re-measured; see Watches)
- [x] Watch retired: none of the surviving watches were satisfied by this landing
- [x] Watch added: spec Expected-Surface under-declaration for guard-propagation work
- [x] Watch added (out-of-epic): finalize `[DISPATCH]` gap + dropped-findings piggyback bug
- [x] Decision recorded: the off-limits boundary held; tight specs work
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **Duration STILL not re-measured** — two consecutive plans have now moved the tree
  substantially (PLAN-02 net −1099 lines, PLAN-03 net +492 with ~13.2 s of unconditional
  sleeping removed) without re-taking the 137 s yardstick. PLAN-03 alone should have *lowered*
  it measurably. This is now the epic's largest unobserved quantity and PLAN-05 must close it.
- **Coverage not reported for this landing** — the trend table has no coverage figure for
  #977. PLAN-05 must re-baseline both axes together.
- The sleep reduction is **~13.2 s** of the 137 s baseline (10 s child + 3.2 s
  timestamp-separation), i.e. a predicted ~9–10 % suite-duration win that remains unverified.
