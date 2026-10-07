envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:13:09Z

# Build and test infrastructure: a zero you cannot interpret

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 3 lessons. **Suggested fold target:** yours to decide. ⚠ Check
disjointness against the sibling `routed build loses tests_run` message — both touch the
build wrapper, and if you plan against that surface twice they collide.

## The three instances

| Lesson | Instance |
|--------|----------|
| `2026-08-08-22-001` | ⭐ **The routed build's `log_file` is the JOB log, not the pytest log.** The `module_testing` profile's identifier-diff sub-step naturally reaches for the `log_file` the wrapper returns; under daemon routing that names `~/.plan-marshall/marshalld/job-logs/{id}.log`, whose entire body is six lines of wrapper TOON with **no pytest node identifiers at all**. The assertion returned `passed: false, found_count: 0, missing_count: 7` for seven tests that had just run green. |
| `2026-08-23-18-001` | Coverage instrumentation pushes subprocess-invoking tests past the 30s conftest budget, turning a **fast-error assertion into a timeout**. Same tree: `module-tests` 17916 passed / 0 failed; `coverage` 40 minutes later 17904 passed / **2 failed**. Neither failure is an assertion failure — the test asserts a command fails *immediately*, and under coverage the child never reports within budget. ⚠ Not stable: a prior coverage attempt on the same tree timed out at 593s without finishing, while the one producing the two failures completed in 268s. |
| `2026-08-08-19-003` | The archived-plan audit's in-task-build churn finding. (Unresolvable — see caveat.) |

## The rule worth carrying

⭐⭐ **`2026-08-08-22-001`: calibrate the log with a control before believing a zero.**

`assert_test_identifiers` is a pure absence detector — it reports "not found on any line". It
**cannot distinguish** *the identifier is absent from a log that lists identifiers* (a real,
silently-skipped test) from *the log lists no identifiers at all* (a wrong log path). Both
render as the same `missing[]` table, and the failing shape is the alarming one — so the
natural next move is to debug a collection problem that does not exist.

⇒ **Add one identifier from a pre-existing test that certainly ran.** If the control is also
missing, the log is the wrong surface, not the test. This turns a bare zero into a
discriminating measurement and costs one line in a file you are writing anyway.

Then resolve the real log by one indirection: the job log's body names it
(`log_file: {worktree}/.plan/local/plans/NO_PLAN/build-results/{module}/python-{stamp}.log`).
On the observed run this flipped the result to `passed: true, found_count: 7`.

⭐ **Bonus signal the lesson names:** the inner log path doubles as proof of *which tree* the
routed build compiled — a brand-new test file exists only in the worktree, so finding its
node identifiers there establishes the daemon built the worktree and not the main checkout.
Worth capturing deliberately, because the inner path resolves under the main checkout's
`.plan/local/plans/NO_PLAN/` and therefore *looks* as though the build ran there.

## The coverage-vs-module-tests directive

`2026-08-23-18-001` is explicit about the wrong fix: ⛔ **do not raise the budget globally
without deciding which of the two things the test actually measures** — a bigger number hides
the same ambiguity. Either assert the structured error without a real subprocess, or scale
the budget with the instrumentation in effect. And make a budget breach **self-describing**,
so a harness `TimeoutExpired` is not read as the behaviour under test failing.

**Matched control required**: the test must still go RED when the script genuinely fails to
emit a structured error, AND stay GREEN under coverage when it behaves correctly. Running the
suite once under each command and observing agreement is the minimum evidence.

## Read-coverage caveat

⛔ `2026-08-08-19-003` is **unresolvable** — `manage-lessons list` enumerates it `active`,
`get` returns `not_found`, and its `list` title is **empty**. Its subject comes entirely from
`2026-08-08-20-002`'s second-hand description ("the in-task-build churn finding"). **This is
the weakest row in the drain**: nothing in this run read its title or its body.

## Claim labels

- **OBSERVED** — both full-body instances, with their quoted counts and the verbatim
  before/after of the log-path fix.
- **HYPOTHESIS** — that `2026-08-08-19-003` concerns in-task-build churn and belongs here.
  Second-hand from another lesson's prose. Confirm/refute by reading the lesson file once the
  corpus-integrity defect is fixed (owned by this router's PLAN-LH2-18). Verify-at-outline.
- **HYPOTHESIS** — that `2026-08-08-22-001`'s fix belongs in `execute-task/SKILL.md` §
  Profile: module_testing. That is the lesson's own placement claim, not re-derived here.
