envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-24T12:42:38Z

# finding (high, operator): `pre-push-quality-gate` was marked done in the same second a red build finished, and nothing ties `mark-step-done` to the recorded build verdict

**Severity:** high (operator-graded 2026-11-24). **Bundle:** `plan-marshall`, component `plan-marshall:phase-6-finalize`.

**Evidence (sender, source lesson `2026-11-22-21-004`, plugin 0.1.2184; the gate code was not traced by the orchestrator).** On the final round of PR 54 (plan-12), `finalize-step-simplify` and `pre-push-quality-gate` were logged `Completed (outcome=done)` at 20:00:47Z and 20:00:48Z, the same second `build-results/default/maven-2026-11-22-195931.log` ended in BUILD FAILURE (`git-store`, `ConcurrentWritersTest.tenWritersWithOwnClones`, 1 error in 406 tests). The branch was pushed on that verdict. A re-run at 20:01:08Z on the identical tree was green, so no broken code landed; the gate nevertheless passed on a red build. The re-fired steps logged no `Executing step` line.

**Suspected cause.** The step was closed by a chained command that did not read the build TOON `status` before marking it done; `mark-step-done` does not consult the change-ledger's build row.

**Ask of `live-blockers`.** Reproduce first at HEAD (`_push_gate.py`, `mark-step-done`). Then: `mark-step-done --step pre-push-quality-gate --outcome done` checks the last build row for the current HEAD and refuses unless it is `status: success` (an explicit operator override aside), and a re-fired step always logs its `Executing step` line. Recorded as a truthful-signals-class defect; check `truthful-signals` and the staged `live-blockers` plans for an owner before opening work.

**Source:** `libraries-initial-implementation-054`.
