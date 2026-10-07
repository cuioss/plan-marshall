envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=finding
created=2026-08-23T22:12:08Z

# Five reproduced infrastructure defects, all the epic's own archetype

Filed by PLAN-TRUTH-075 during its finalize. **None is in that plan's declared scope**, so none was
fixed there. Each was reproduced with evidence during a single run, and each is a signal that reads
confident over an unexamined condition — the theme this epic exists to close.

Recorded here because the plan-local findings store is git-ignored and archives with the plan. This
inbox message is the durable copy.

## 1. `10298b` — a routed build reports `tests_run: 0` on GREEN runs

Every green routed build call printed `tests_run: 0` at the OUTER layer with the line
`0 test(s) executed — this run tested nothing`, while the INNER job log for the same job reported the
real count. **Reproduced three times with matched inner/outer pairs from the same job id**, including
a whole-tree `module-tests` whose inner log read `21683 test(s) executed, green`.

The RED path reports the count correctly, so the under-report is specific to the SUCCESS path.

Any consumer reading the outer `tests_run` sees this repository's strongest gate as a run that tested
nothing. Not confined to `plan=NO_PLAN`: reproduced on a plan-scoped job too.

## 2. `3e095e` — `build_server wait` re-attach can return a STALE job's verdict

A coverage build was reaped at the 600s Bash ceiling. Per the documented recovery the orchestrator
re-issued `build_server wait --plan-id X`. It returned `job_status: success`, `exit_code: 0`,
`duration_seconds: 79`.

**That verdict belonged to a different build** — opening the named `log_file` showed
`./pw verify pm-plugin-development` from an earlier run, not coverage.

Root cause found later: the build wrapper submits as `plan=NO_PLAN`, so `wait --plan-id` matched a
different, plan-scoped ledger row. The return carries no `command`, no `job_id`, and no
submitted-vs-resolved discriminator, so a stale re-attach is **indistinguishable from the caller's own
job completing green**. It was caught only because 79s was implausible for a build already observed
running past 600s.

Suggested fix: echo the resolved `job_id` and `command`; add an explicit discriminator when the
resolved job predates the caller's submission.

## 3. `4fee70` — whole-tree coverage keys its timeout off an unmeasured name, so ONLY green runs truncate

`architecture resolve --command coverage` returns `bash_timeout_seconds: 830`. But
`python:coverage_default` (the module-scoped key the resolver reads) is `measured: false`, while
`python:coverage` is `measured: true` at **1416s**. The learned value for the same build is never read.

**Proven causally**: writing `python:coverage_default` moved the resolved budget 830s → 1800s.

Why it belongs here: the RED path short-circuits (a failing run finished in 646s, inside 830s) while
the GREEN path additionally generates the coverage report and exceeded 805s. **The budget looks
adequate on every failing run and truncates only on passing ones** — invisible precisely when the
build is healthy.

## 4. `48dd4c` — `automatic-review` worked example crashes on the common path

`automatic-review/SKILL.md:681` interpolates `--measured-diff-size "{measured_diff_size}"`
unconditionally. The Canonical invocations block at 976-978 states the opposite: it is not a list
flag, and must be omitted when unmeasured.

On the common path (no diff-size refusal) `fetch_findings` correctly returns an empty value, the
executor's empty-arg strip reduces it to a bare trailing flag, and argparse rejects at exit 2 — which
under the guard's own UNKNOWN rule forces a `loop_back` rather than a verdict. The eight genuine LIST
flags on the same call are safe because they declare `nargs='?'`; this scalar flag is the sole
exception and the example treats it identically.

The dispatch on this run **hit it and had to work around it**.

## 5. `9134b6` — gate-delta is structurally unmeasurable whenever a gate re-fires

The review-retrospective excluded its gate-delta share as `gates_did_not_cover_reviewed_tree`. The
documented cause is a gate SHA *older* than the reviewed one. Here it ran the other way:
`pre-push-quality-gate` fired **three** times and the record keeps only the terminal SHA, because
`prior_firings[]` carries outcomes **without SHAs**.

Consequence: **any plan whose head-dependent gate re-fires is unmeasurable for this delta**,
independently of the ordering hypothesis. A run of `excluded` rows must therefore NOT be read as
support for that hypothesis — the exclusions have at least two causes and the provenance string names
one.

Suggested fix: record per-firing head SHAs in `prior_firings[]`.

## Why these belong together

All five are the same shape: a signal that is confident, and wrong or incomplete, in the direction of
looking clean. Three of them (1, 3, 5) are **anti-correlated with the interesting case** — they
misreport specifically on the green/passing/healthy path, which is exactly when nobody looks.
