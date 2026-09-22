# PLAN-TRUTH-105: Build-execution verdicts that mislead specifically on the healthy path

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-105-build-execution-verdicts-that-mislead-specifically-on-the-healthy-path.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-24 from the PLAN-TRUTH-075 inbox drain — message `-008`, items **2** (`3e095e`) and
**3** (`4fee70`). Both were **reproduced first-party during a single run** by the plan that filed them,
neither was in that plan's scope, and neither had an owner. The other three items of `-008` already
had homes (`-087` DA, `-097` F5, and a forward to `review-apparatus`); these two did not.

## Objective

Two build-execution signals are wrong, and both are wrong **specifically on the healthy path** — they
report correctly when the build fails and mislead when it succeeds. That anti-correlation is the whole
subject: a signal that degrades only when nobody is looking is worse than one that degrades always,
because the failure mode is invisible to exactly the runs that would expose it.

⭐ **Why these two and not more.** `-008` filed five defects sharing this archetype. Three of them have
owners. These two are grouped because both are **build-execution verdicts** reached through the build
wrapper / build-server / timeout-resolution path, and both were observed in the same run — not merely
because they share an archetype. ⛔ Grouping by archetype across unrelated surfaces is a staging error
this epic has recorded; if outline finds the two surfaces genuinely disjoint, **split rather than
stretch**.

## Deliverables

Three deliverables. D0 is a gate.

**D0 — GATE: establish the population of green-path-only build signals before fixing either instance.**
Both members below were found by accident during one unrelated run, and a third member of the same
archetype (`-008` item 1, `tests_run: 0` on GREEN runs — the RED path reports correctly) is already
owned by `-087` DA. ⛔ **Three accidents, zero sweeps.** Enumerate every build-execution verdict whose
value is derived differently on the success and failure paths, and **publish the swept population and
its size**. ⚠ A member found here that belongs to `-087` is recorded and deferred, not absorbed — see
Dependencies.

**D1 — `build_server wait` re-attach can return a STALE job's verdict, indistinguishable from success.**
*(finding `3e095e`)* A coverage build was reaped at the 600s Bash ceiling. Per the documented recovery
the orchestrator re-issued `build_server wait --plan-id X`, which returned `job_status: success`,
`exit_code: 0`, `duration_seconds: 79`. **That verdict belonged to a different build** — the named
`log_file` contained `./pw verify pm-plugin-development` from an earlier run, not coverage.

Root cause as filed: the build wrapper submits as `plan=NO_PLAN`, so `wait --plan-id` matched a
different, plan-scoped ledger row. ⛔ **The return carries no `command`, no `job_id`, and no
submitted-vs-resolved discriminator, so a stale re-attach is indistinguishable from the caller's own
job completing green.**

⭐⭐ **It was caught ONLY because 79s was implausible for a build already observed running past 600s** —
i.e. by the standing rule *never trust a routed build's outer status; an implausible duration is a
failure signal*. **A rule of thumb was the sole line of defence against a false green.** That is the
measure of how badly this needs a machine discriminator.

Fix direction: echo the resolved `job_id` and `command` on the return, and add an explicit
discriminator when the resolved job **predates the caller's submission**. ⚠ The `plan=NO_PLAN`
submission asymmetry is the deeper cause and D0 should establish whether it is worth closing here or
belongs with the ledger work in `-088`.

**D2 — whole-tree coverage keys its timeout off an unmeasured name, so ONLY green runs truncate.**
*(finding `4fee70`)* `architecture resolve --command coverage` returns `bash_timeout_seconds: 830`. But
`python:coverage_default` — the module-scoped key the resolver reads — is `measured: false`, while
`python:coverage` is `measured: true` at **1416s**. **The learned value for the same build is never
read.** Proven causally: writing `python:coverage_default` moved the resolved budget 830s → 1800s.

⭐ **Why this is a green-path defect and not merely a wrong number:** the RED path short-circuits — a
failing run finished in 646s, inside the 830s budget — while the GREEN path additionally generates the
coverage report and exceeded 805s. ⇒ **The budget looks adequate on every failing run and truncates
only on passing ones.**

⚠ Fix the **resolution**, not the number: writing a value into `python:coverage_default` by hand makes
the symptom disappear while leaving the resolver reading a key that nothing measures. D0's sweep should
establish whether other `*_default` keys share the shape.

**D3 — tests: each pinned on the path that lies, with a matched control on the path that does not.**
For D1, a fixture where a resolved job predates the caller's submission must be **distinguishable** from
the caller's own green — and a matched control where the resolved job IS the caller's must still return
an ordinary success. For D2, assert the resolver reads the **measured** key, with a control proving a
genuinely unmeasured key still degrades honestly rather than silently substituting. ⛔ Both controls are
load-bearing: this epic has recorded the vacuous-guard archetype being re-introduced by its own fix at
least twice, most recently inside PLAN-TRUTH-075's own guard cascade (five rounds, four of them the same
defect one level deeper).

## Expected Surface

Provisional — D0's sweep is expected to move it. Recorded so `corpus cross-check` has something to
reconcile, **not** as a settled boundary.

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` *(the build-server wait /
  re-attach path and its protocol module)*
- `marketplace/bundles/plan-marshall/skills/manage-architecture/` *(the `resolve --command` timeout-key
  lookup)*
- `marketplace/bundles/plan-marshall/skills/manage-build-server/`
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` *(the post-build `worktree_sha` ledger stamp — added 2026-09-11 by the fold of `api-sheriff-deployment-configurability-006`)*
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` *(the `worktree_dirty` clean-tree invariant that does not consult `mutating` — added 2026-09-11 by the fold of `-037`)*
- the corresponding test modules under `test/plan-marshall/`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.** The map below is the staging-time reading. R48
records that this orchestrator's hand-written maps missed 4 of 7 collisions on the previous pair, **all
four of them cross-epic** — so treat any hand-written entry here as a lead, not the map.

- ⛔ **`PLAN-TRUTH-087` (`build-gates-test-suite-confidence-and-ci-workflow-lint`) — RUNNING at time of
  staging; SERIALIZE.** Its Expected Surface includes
  `script-shared/scripts/build/_build_server_protocol.py`, and its **DA carries `-008` item 1** — the
  third instance of this plan's exact archetype (`tests_run: 0` on green). ⭐ **When `-087` lands, check
  whether its DA fix generalises to D1/D2 before implementing them separately**; three instances of one
  archetype in one subsystem may warrant one boundary fix rather than three point fixes. That check is
  D0's, and it cannot be made until `-087` is on `main`.
- ⚠ **`PLAN-TRUTH-088` (`metrics-ledger-readers-and-timestamp-provenance`) — RUNNING; check on landing.**
  D1's `plan=NO_PLAN` submission asymmetry is adjacent to `-088` DA's change-ledger `plan_id` work
  (R5: 424 of 433 `kind=build` rows carry `plan_id` null or `NO_PLAN`). **The same submission defect may
  be the cause of both.**
- **Depends on:** nothing hard. But D0's most valuable input is `-087`'s landed DA, so **scheduling this
  after `-087` lands is strongly preferred** over racing it.

## Claim Labels

⚠ Both defects are reported from PLAN-TRUTH-075's finalize findings `3e095e` and `4fee70`. They were
reproduced by THAT plan first-party; this orchestrator corroborated the surrounding mechanics but did
NOT re-reproduce the two failures. Labelled accordingly — the distinction is the point.

- OBSERVED (by PLAN-TRUTH-075, not re-reproduced here): `build_server wait --plan-id` returned `job_status: success`, `exit_code: 0`, `duration_seconds: 79` for a build that was not the caller's, with the named `log_file` holding a different command — finding `3e095e`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-labelled OBSERVED by a different plan (-075); historical build event, not re-reproducible
- OBSERVED (by PLAN-TRUTH-075, not re-reproduced here): `architecture resolve --command coverage` returns `bash_timeout_seconds: 830` from `python:coverage_default` (`measured: false`) while `python:coverage` is `measured: true` at 1416s; writing the `_default` key moved the budget 830 → 1800 — finding `4fee70`.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED twice over: bash_timeout_seconds is now 1626 (830 at staging, 1170 at last re-grounding) and NEITHER literal key python:coverage_default nor python:coverage exists anywhere in the tree -- _cmd_client_build.py:298-356 resolves via compute_command_key/timeout_get/timeout_measured against a computed key. Re-scoped: D2 must be re-derived against the current mechanism before this spec is emitte
- OBSERVED (by PLAN-TRUTH-075): the RED path short-circuited inside 830s (a failing run finished at 646s) while the GREEN path exceeded it — the anti-correlation this plan is named for.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Historical run measurement (RED 646s vs budget); cannot be re-observed at HEAD
- HYPOTHESIS: the return carries no `command`, `job_id`, or submitted-vs-resolved discriminator — confirm/refute at `script-shared/scripts/build/` § the `wait` return shape (verify-at-outline). **D1's whole remedy depends on this absence being real.**
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: HALF FALSE at HEAD: command is a member of REQUIRED_FIELDS (_build_result.py:226) and is stamped on every result constructor (:315 :350 :383 :434 :475); only job_id is genuinely absent. Re-scoped: D1 narrows to the job_id / submitted-vs-resolved discriminator alone.
- HYPOTHESIS: the build wrapper submits as `plan=NO_PLAN`, which is why `wait --plan-id` matched a foreign row — confirm/refute at the build submit path § the ledger write (verify-at-outline). ⚠ If true this is shared cause with `-088` DA and must be settled once, not twice.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Build submit path plan=NO_PLAN attribution not re-checked this pass
- HYPOTHESIS: other `*_default` timeout keys share the unmeasured-name shape — confirm/refute at D0's sweep (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0 sweep; the *_default key-naming scheme itself no longer exists per claim 1
- Verify-first clause: D0 must establish whether `-087`'s landed DA generalises to D1/D2 before either is implemented separately — three instances of one archetype in one subsystem may warrant one boundary fix.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause pending -087 landing
- OBSERVED: the two full-body `tests_run` observations (17916, 18083) and their named emitting sites — `script-shared/scripts/build/_build_execute_factory.py` (the build-execute routing seam) and `build-server-client` (the daemon side)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References lesson-quoted historical figures (17916, 18083); not re-derivable from current source
- OBSERVED: `2026-08-08-22-001` in full, including the verbatim before/after of the log-path fix; and `2026-08-23-18-001`'s two run comparisons
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References lesson file content verbatim; not a code-state claim
- HYPOTHESIS: the two title/unresolvable-derived rows (17888, 18123) are the same defect — confirm/refute at the lesson files once the corpus-integrity defect is fixed (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred until the corpus-integrity defect (title/unresolvable rows) is fixed
- HYPOTHESIS: the transport half is closed at HEAD — confirm/refute at `build-server-client` § `read_log_verdict` / `_daemon_result_to_direct` (verify-at-outline). ⛔ This is the FIRST thing to settle; the plan's size depends on it.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _build_execute_factory.py:439-508 _daemon_result_to_direct forwards routed_tests_run only when the inner verdict has a count, else leaves the key absent (not zero) -- transport half closed
- HYPOTHESIS: `2026-08-08-22-001`'s fix belongs in `execute-task/SKILL.md` § Profile: module_testing — the lesson's own placement claim, not re-derived
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson own unre-derived placement claim (execute-task/SKILL.md)
- ⛔ `2026-08-08-19-003` is **UNRESOLVABLE and the weakest row in the whole drain**: `manage-lessons list` says `active`, `get` says `not_found`, and its `list` title is **empty** — its subject comes entirely from another lesson's second-hand description (*"the in-task-build churn finding"*). **Nothing read its title or its body.** Do not scope on it.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-labelled UNRESOLVABLE in the spec itself (lesson list says active, get says not_found)

## Folded from the PLAN-TRUTH-088 drain (2026-08-24) — inbox `-006`

**The build oracle attributes every build to `NO_PLAN` and double-records each one.** `analyze-logs`
reported this plan's build time as `total_build_seconds: 0.0`, `build_count: 0`, `suspect_count: 0` —
a clean triple zero for a run that built repeatedly.

⛔ **Read against R5, which CORRECTED the earlier wording and must not be re-loosened.** The write IS
reached and the ledger is NOT destroyed — first-party sampling found 468 rows / 433 `kind=build`
spanning 2026-06-11→08-22. What fails is what the row **carries**: **424 of 433 have `plan_id`
null or `NO_PLAN`**. This message supplies the second half of the mechanism — **each build is also
recorded twice** — so a consumer that filters by `plan_id` sees nothing and a consumer that does not
double-counts. Both readings are wrong, in opposite directions, from one writer.

⭐ **This belongs to this spec specifically because it misleads on the HEALTHY path** — a clean triple
zero is what a plan with no builds would also produce, and nothing distinguishes them. It is the same
shape as `tests_run: 0` on green runs (R6/R57, owned by `-087` DA and still running): **the
degenerate value appears exactly when the run went well.** Sequence behind `-087`'s landing so the
two build-status readers are not changed from both ends at once.

## ⚠ RE-SCOPED at the 2026-08-26 cleanup — the coverage-timeout FIGURE is stale

Claim 1 cited `bash_timeout_seconds: 830` for `architecture resolve --command coverage`. **Measured
at `31bed3e76`: the value is now `1170`.** The number moved; the spec must not be implemented against
830.

⭐ **The anti-correlation argument survives the change and does not need re-deriving.** It rests on a
RED run short-circuiting *inside* the budget while a GREEN run exceeds it — the observed RED finish
was 646s, which is inside 1170 exactly as it was inside 830. The direction is unchanged; only the
threshold moved.

⛔ **What is now UNESTABLISHED and must be re-derived at D0**: whether the resolved value still comes
from an unmeasured `*_default` key (`python:coverage_default`, `measured: false`). The resolve output
read at this sha published the timeout but not its provenance fields, so the *shape* claim — an
unmeasured default presented as a budget — is neither confirmed nor refuted. **Re-read the provenance,
not just the number**, and treat any figure in this spec as indicative rather than current.

## ⭐⭐ FOLDED 2026-08-27 — two clusters land on this surface, and the router flagged their collision

From the `lessons-handling-26-08-26-01` drain, messages `-003` (4 lessons, *"a routed build loses
`tests_run`"*) and `-009` (3 lessons, *"build and test infrastructure: a zero you cannot interpret"*).
⚠ **The router explicitly warned these two collide with each other** — *"both touch the build wrapper,
and if you plan against that surface twice they collide"* — which is why they fold into ONE plan here.

### A — the routed build asserts "this run tested nothing", and it is false

When a build routes to the `marshalld` daemon, the outer wrapper reports `tests_run: 0` and prints
*"green build: 0 test(s) executed — this run tested nothing"*, while the daemon's own job log for the
same job records the real figure.

⛔ **A fully green run and a run that executed nothing produce BYTE-IDENTICAL outer output** — same
`status: success`, `exit_code: 0`, `tests_run: 0`, same banner. The only outer field that contradicts
the claim is `duration_seconds`, and **duration is a heuristic, not a count**. The banner makes it worse
than a missing field: it asserts a **positive** claim that is false rather than declaring the count
unknown.

| Lesson | Plan | Inner | Outer |
|---|---|---:|---:|
| `2026-08-23-13-001` | (unresolvable) | 17888 | 0 |
| `2026-08-23-17-001` | `orchestrator-inbox-and-landing-residue` | 17916 | 0 |
| `2026-08-24-16-002` | `a-refusal-nobody-recognises-is-filed-as-a-finding` | 18083 | 0 |
| `2026-08-24-18-001` | (title-only) | 18123 | 0 |

⭐ **Four plans, four different inner counts, one outer zero — the recurrence is DERIVED from the
enumeration, not asserted.** `2026-08-23-17-001` additionally records its sub-agent observing the loss
**four times inside one envelope** (inner 13, 44, 152, 7 — all reported 0 outside), so the per-plan
count **understates** the frequency.

⚠ **What is claimed closed, and by whom:** `2026-08-23-17-001`'s body states the **transport half** is
closed — `read_log_verdict` parses the job log's `tests_run:` line, `_daemon_result_to_direct` stamps
it, `cmd_run_common` prefers the propagated count. ⛔ **That is the lesson's own claim and was NOT
re-verified against HEAD. Establishing which half is live is this plan's FIRST job.** The residual is
the **unavailable-count** case: `LogVerdict.tests_run` is `None` when the routed wrapper published no
`tests_run:` line, the outer wrapper falls back to parsing the daemon job log — which carries the inner
result TOON and **no pytest output** — and publishes a measured-looking `0` plus the banner for a count
it never received.

⇒ **An unavailable count is an UNKNOWN, not a measured zero** (ADR-009 fail-closed with an explicit
unknown state). A consumer gating on `tests_run` must treat a `0` that arrived with no propagated count
on a `mechanism=daemon_longpoll` return as **indeterminate**. **Matched pair required:** a routed build
whose wrapper published no count must report unknown, AND a routed build that genuinely ran zero tests
must stay distinguishable from it. ⛔ **A fix that merely stops printing the banner satisfies neither.**

### B — a zero you cannot interpret, and the one-line control that fixes it

⭐⭐ **`2026-08-08-22-001`: the routed build's `log_file` is the JOB log, not the pytest log.** The
`module_testing` profile's identifier-diff sub-step naturally reaches for the `log_file` the wrapper
returns; under daemon routing that names `~/.plan-marshall/marshalld/job-logs/{id}.log`, whose entire
body is six lines of wrapper TOON with **no pytest node identifiers at all**. The assertion returned
`passed: false, found_count: 0, missing_count: 7` **for seven tests that had just run green.**

⛔ `assert_test_identifiers` is a pure absence detector and **cannot distinguish** *the identifier is
absent from a log that lists identifiers* (a real silently-skipped test) from *the log lists no
identifiers at all* (a wrong log path). Both render as the same `missing[]` table, and **the failing
shape is the alarming one** — so the natural next move is to debug a collection problem that does not
exist.

⇒ ⭐ **Add one identifier from a pre-existing test that certainly ran.** If the control is also missing,
the log is the wrong surface, not the test. **This turns a bare zero into a discriminating measurement
and costs one line in a file you are writing anyway.** Then resolve the real log by one indirection —
the job log's body names it (`log_file: {worktree}/.plan/local/plans/NO_PLAN/build-results/{module}/python-{stamp}.log`);
on the observed run that flipped the result to `passed: true, found_count: 7`.

⭐ **Bonus signal worth capturing deliberately:** the inner log path doubles as proof of **which tree**
the routed build compiled — a brand-new test file exists only in the worktree, so finding its node
identifiers there establishes the daemon built the worktree and not main. ⚠ Needed because the inner
path resolves under the MAIN checkout's `.plan/local/plans/NO_PLAN/` and therefore *looks* as though the
build ran there.

**`2026-08-23-18-001` — coverage turns a fast-error assertion into a timeout.** Same tree:
`module-tests` 17916 passed / 0 failed; `coverage` 40 minutes later 17904 passed / **2 failed**. Neither
is an assertion failure — the test asserts a command fails *immediately*, and under coverage the child
never reports within the 30s conftest budget. ⚠ **Not stable**: a prior coverage attempt on the same
tree timed out at 593s without finishing, while the one producing the two failures completed in 268s.
⛔ **Do NOT raise the budget globally without deciding which of the two things the test measures** — a
bigger number hides the same ambiguity. Either assert the structured error without a real subprocess, or
scale the budget with the instrumentation in effect, and make a budget breach **self-describing** so a
harness `TimeoutExpired` is not read as the behaviour under test failing. **Matched control:** RED when
the script genuinely fails to emit a structured error, GREEN under coverage when it behaves correctly.

## Claim Labels — folded 2026-08-27

> ↪ The bullets filed here on 2026-08-27 were merged into `## Claim Labels` above.
> `_parse_claims` reads ONE `## Claim Labels` section, so claims under a decorated
> second heading were structurally unstampable — the R97/R102 class, self-inflicted.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-012.md`** (relayed from Token-Sheriff, plan `refresh-path-gate-and-invariant-gaps` PR #687) — *a completeness discriminator must be DERIVED from the observation, not asserted beside it.*

  ⭐ **The rule, stated better than this spec currently states it:** *“when a payload carries both a count/verdict and a discriminator that vouches for it (`*_population: measured`, `participation_complete: true`, `store_resolution: present`), the discriminator MUST be computed from the same read that produced the count. A discriminator assembled from a different, cheaper source — a return code, the presence of a response body, a step’s own success — is not evidence; it is a second claim that happens to sit next to the first.”*

  **Site 1 folds here.** The build wrapper returned `tests_run: 0` with `tests_population: measured` while the underlying Maven log carried **465 test-result lines**. `measured` is precisely the token that tells a caller *this zero is real*; a caller trusting the TOON concludes no tests ran and that the build proved nothing, when a full suite had passed. **The failure is that `tests_population` was set from the wrapper’s own belief that it had parsed, not from the parse actually yielding rows.** The correct derivation is stated: `measured` **iff** the parser matched ≥ 1 test-result line; otherwise `unparsed`, and a zero under `unparsed` is a could-not-read zero.

  ⚠ **This is the SAME boundary R6 recorded, one field over.** `PLAN-TRUTH-027` (#1224) fixed `duration_seconds` as a field while `tests_run` is still substituted at the routed wrapper. **Fix the BOUNDARY or a third field repeats it** — this fold is the third field arriving on schedule, from a different repository.

  ⭐ **The auditing question the sender offers is worth adopting as a D-level check:** *“what read would have to fail for this discriminator to be wrong, and does the code branch on that read? If the discriminator cannot be falsified by the same failure that falsifies the count, it is decorative.”*

  ⛔ **Site 2 is NOT folded here.** *(A review bot’s rate-limit refusal classified as participation because the classifier keyed on a non-empty `review_body`.)* Already owned: shipped as `review-apparatus` **`PLAN-PR-034`**, and carried in the lessons corpus as **`2026-09-02-22-001`**. Verified before the drain declined to re-stage it.

## ⭐ FOLDED 2026-09-04 — inbox drain (2 message(s))

- **`deployment-and-refresh-gaps-022`** (relayed from Token-Sheriff, plan `plan-09-local-gate-truthfulness`, PR #699) — *an adaptive build-timeout budget learned from warm incremental runs under-budgets the cold full rebuild a parent-POM bump forces.* **Only the STRUCTURAL half folds here; the practice rule was promoted to the lessons corpus.** `pre-push-quality-gate` returned `job_status=timeout` at 1197s against a resolved `bash_timeout_seconds=1226`. ⭐⭐ **The run refused to read that as either verdict — “not a red build and not a green one”** — and log inspection established **budget, not code**: the build progressed normally to the last reactor module and was cut off mid-openrewrite, so it had not stalled. ⛔⛔ **The cause is an ORDERING correlation, not chance:** `finalize-step-sync-baseline` absorbs upstream commits and `pre-push-quality-gate` runs next **against a budget that has no knowledge of what was just absorbed**. Here the rebase pulled `cui-java-parent` 1.5.11 → 1.6.0, forcing *“Recompiling the module because of changed dependency”* across **every** module — a cold full rebuild against a warm-run budget. Re-run completed in 540s. **Structural ask:** widen or reset the adaptive budget to a cold baseline when the preceding sync-baseline reports an absorbed change to a parent POM or a dependency-management import.

- **`review-apparatus-029`** (carried-out finding `c8e4a9`, `PLAN-PR-038`, severity `error`) — *a timeout verdict kills the daemon job but ORPHANS the whole pytest process tree.* ⭐⭐ **Observed live, confirming lesson `2026-09-02-21-002` which `finalize-step-lessons-housekeeping` had JUST retained as not-covered.** A whole-tree verify hit its 3000s bound, the daemon returned `status=timeout`, **and the tree survived**: pid 21025 (`build.py verify`) alive at 58:52 elapsed, pid 33766 (`pytest -n auto`) at 46:10, plus **TEN xdist workers actively spawning fresh children at 00:02-00:05 elapsed** — still executing tests minutes after the daemon called the job dead. ⛔ **Observed consequence chain:** the orphans saturated the machine → the immediately-following retry failed `worktree_resolution_failed` because its 15s worktree probe could not complete → **that surfaced as `exit_code 2` with “no structured errors were parsed”, which reads like an argparse rejection, not like resource starvation.** ⛔⛔ **TWO-STAGE SURVIVAL: killing pytest’s master did NOT take the workers** — all ten survived and had to be signalled individually. **Remedy: the supervisor’s timeout path must kill the PROCESS GROUP and confirm the group is gone before reporting a terminal verdict — a `status=timeout` that leaves the work running is a false terminal state.** Until then a timeout MUST be followed by an explicit orphan sweep before any retry.

## ⭐⭐ FOLDED 2026-09-05 — lessons-handling drain (1 message)

- **`lessons-handling-26-09-04-01-009`** — *the maven wrapper's own `--timeout` defaults to 300s
  INDEPENDENTLY of the daemon's supervisory bound, so a long build silently times out.*

  ⭐⭐ **This is the spec's own thesis at a seam it did not name: TWO timeouts, neither aware of the
  other, and the tighter one is the invisible one.** An operator who raises the supervisory bound has
  every reason to believe the build may now run longer; the wrapper's independent 300s default cuts it
  anyway, and the resulting failure is a TIMEOUT presented where a build result belongs.

  ⛔ **It bites specifically on the healthy path — the anti-correlation this spec exists to catch.** A
  build that fails fast never reaches 300s and returns correctly; only a build that is doing real work
  long enough to matter is cut. ⇒ **A short build is not evidence the bound is adequate**, and every
  green run below the floor is silence about it.

  ⚠ **Adjacent, already recorded, and NOT the same defect**: a `marshalld` timeout abandons the WAIT and
  not the BUILD (leaving an orphaned pytest tree). ⛔ Keep them apart — that one is a supervisor giving
  up on a live job; this one is a *second, independent* ceiling nobody configured. **A fix to either
  leaves the other.**

  ⚠ **Expected Surface widened in this same act**: `marketplace/bundles/plan-marshall/skills/build-maven/**`
  — the wrapper's own `--timeout` default and its relation to the resolved envelope's
  `bash_timeout_seconds` (HYPOTHESIS, verify-at-outline).

## ⛔⛔ FOLDED 2026-09-05 — PLAN-TRUTH-093 drain (1 message). A WELL-FORMED ZERO FROM THE DESIGNATED ORACLE.

- **`preference-admissibility-...-008`** — *build rows are attributed to `NO_PLAN`, so the build-time
  oracle reports zero for a plan that built for hours.*

  The retrospective's `analyze-logs` extractor reads `build_time` from the change-ledger — **the
  designated build-time ORACLE** — and returned `total_build_seconds: 0.0`, `build_count: 0`, with every
  status bucket at zero. ⛔ **Structurally complete, internally consistent, and wrong.**

  **Three independent sources refute it**, and the sender named all three rather than asserting:
  `script-execution.log` records **103** `pyproject_build` calls totalling **31,166,590 ms** — 61.5% of
  all script time and the single largest cost line, max single call **1,930,110 ms**; the plan directory
  holds **30** build-result logs inside its own window; and the operator transcript records `verify`
  **OOM-killed twice**, which does not happen to a plan that ran no builds.

  **Root cause, first-party:** `manage-change-ledger query --kind build` returns **444 rows**, and every
  sampled row (head 6, tail 12 — ⭐ **the sender states the sampling rather than claiming exhaustion**)
  carries `plan_id: null` or `NO_PLAN`, **including rows timestamped inside this plan's own `6-finalize`
  window**, with `log_file` paths under `.plan/local/plans/NO_PLAN/build-results/`.

  ⇒ **The builds were recorded. They were recorded against the sentinel.** ⭐⭐ **This is this spec's
  thesis at the attribution layer rather than the execution layer:** *an oracle is only authoritative
  over the population it can attribute; when the attribution key is a sentinel it still answers — with a
  well-formed zero — and every downstream consumer inherits a measurement nobody made.* ⛔ **A zero from
  a designated oracle is the most expensive possible false negative**, because it is the one reading
  nobody re-derives.

  ⚠ **Expected Surface widened in this same act**:
  `marketplace/bundles/plan-marshall/skills/manage-change-ledger/**` — the build-row attribution key —
  and `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — `analyze-logs`'
  `build_time` extractor, which must publish the population it attributed (HYPOTHESIS,
  verify-at-outline). ⛔ **Memory of a matching live incident:** a `plan-marshall` finalize once
  attributed hours of build work to `NO_PLAN` while its own plan-scoped ledger read empty — same shape,
  independent occasion.

## ⛔⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d`. THIS SPEC IS HALF-SHIPPED AND ITS D2 PREMISE IS STALE TWICE OVER.

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 1 | the timeout resolves through the static keys `python:coverage_default` / `python:coverage`, and the budget is 830s | **REFUTED twice over.** `bash_timeout_seconds` is now **1626** (830 at staging, 1170 at the last re-grounding), and **neither literal key exists anywhere in the tree** — `_cmd_client_build.py:298-356` resolves via `compute_command_key` / `timeout_get` / `timeout_measured` against a **computed** key. |
| 3 | the terminal build result carries **no `command`, no `job_id`**, so a stale re-attach is indistinguishable from the caller's own job | **HALF FALSE.** `command` is now a member of `REQUIRED_FIELDS` (`_build_result.py:226`) and is stamped on **every** result constructor (`:315, :350, :383, :434, :475`). **`job_id` is genuinely still absent.** |

⭐⭐ **D1 is NARROWER than the spec states, and shipping it as written would re-build something that
exists.** Two of its three halves are closed: the `command` field (claim 3) and the `routed_tests_run`
transport, which `_daemon_result_to_direct` (`_build_execute_factory.py:439-508`) already forwards only
when the inner verdict carries a count — **leaving the key absent, never a false zero** (claim 10,
corroborated). ⇒ **What remains open is the `job_id` / submitted-vs-resolved discriminator ALONE.**

⛔⛔ **D2 must be re-derived against the CURRENT mechanism, not the one it was staged against.** A
deliverable written against `{lang}:{command}_default` string keys has no target: the resolver moved to
computed keys and a measured-timeout path. **Re-grounding D2 is a prerequisite to emitting this spec,
not a task inside it.**

⚠ **Nine of its thirteen claims are `unverifiable`** — historical build events, lesson-quoted figures,
and one the spec itself labels UNRESOLVABLE. ⛔ **That is not a refutation and must not be read as one**;
it means the spec's evidentiary base has decayed and D0 must re-measure rather than re-cite.

## ⛔⛔ FOLDED 2026-09-06 (c) — DAEMON-LOG SWEEP. THE ATTRIBUTION DEFECT IS CONFIRMED ON A SECOND SURFACE, AND QUANTIFIED.

The `-093` drain established that build rows are attributed to `NO_PLAN` from the **change-ledger**.
A first-party sweep of the **daemon's own interaction-audit log** — a different producer, a different
store — returns the same thing: **4 of 4 submits and 4 of 4 fates carry `plan_id: NO_PLAN`**, across
three separate days.

⇒ ⭐⭐ **n = 2 SURFACES, not one plan's instrumentation.** Two independent producers cannot attribute a
build to the plan that requested it.

### The quantified population, re-derived from raw JSONL (484 lines, **0 unparseable**)

| `plan_id` | rows |
|---|---:|
| `None` (JSON null) | **371** |
| `'NO_PLAN'` | **64** |
| `'none'` (literal string) | **1** |
| a real plan id | **8** |

**435 of 444 build rows — 97.97% — carry no usable attribution.**

⛔⛔ **AND THERE ARE THREE SPELLINGS OF THE SAME ABSENCE**: `null`, `NO_PLAN`, and the literal string
`'none'`. ⇒ **A consumer filtering on any ONE of them under-counts silently**, which is this spec's own
thesis (a well-formed answer over a population the caller did not intend) arriving one layer below the
oracle. ⚠ **D0 must treat the three as one class and say so**; a fix that filters `NO_PLAN` alone leaves
371 rows.

⚠ **A methodological note worth keeping**: an earlier reading of this same data through the TOON
renderer showed a field shift that looked like a data defect. It was **an artifact of the reader**, not
the ledger — the raw JSONL parses cleanly. **Re-derive from the store, not the rendering.**

## ⭐ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain (1 item)

### `freshness-gate-...-005` — run `reconcile-ledgers` at `record-metrics` and surface a non-zero `findings_count`

A reconciliation that exists and is **not invoked at the point where its result would still be
actionable**. ⇒ **A ledger divergence is discoverable and undiscovered** — this spec's family (a build
/ ledger verdict that misleads on the healthy path), here by **omission of the call** rather than by a
wrong return.

⛔ **The placement is the deliverable, not the check.** `record-metrics` is the last step that can still
act on a non-zero count before the run's state is frozen; running the same reconciliation later reports
the same number to nobody. ⚠ **And a zero must be published with its population** — a
`findings_count: 0` from a reconciliation that ran is not the same signal as one from a reconciliation
that was never invoked, which is precisely the distinction this epic exists to preserve.

## ⭐ FOLDED 2026-09-07 (b) — PLAN-TRUTH-099 drain (1 item)

`-006` (`phase-5-execute`): **check build freshness BEFORE reverting build-generated churn.**

⛔ **An ordering defect that destroys the evidence its own next step needs**: reverting generated churn
first makes the tree look fresh, so the freshness check that follows passes **on a state the revert
manufactured.** ⇒ **A green verdict caused by the step immediately before it** — this spec's
healthy-path family, and a close cousin of the `PLAN-TRUTH-128` subject it sits beside in this drain
(a gate that reports `fresh` for a tree it never examined; here the tree was examined *after* being
made to look fresh).

⚠ **The fix is an ordering swap, which is cheap — and that is precisely why it should carry a control**:
a re-ordering with no test pinning the order is one refactor away from silently reverting.

> ⛔⛔ **CORRECTED 2026-09-11 — the DIRECTION stated above is BACKWARDS for the ledger path.** Refuted by
> `api-sheriff-deployment-configurability-006` and corroborated first-party at `356973d80`:
> `tools-script-executor/templates/execute-script.py.template`:579 computes
> `compute_worktree_sha(os.getcwd())` ONCE, **after** the build subprocess returns — so the `kind=build`
> row carries the **post-churn** sha. Reverting gate-owned churn returns the tree to a **pre-build** sha
> no row carries, and `pre-commit-verify-freshness` reports **`stale` / `worktree_mutated`** — the tree
> looks STALE, not fresh. The text above is left verbatim as the audit record; the corrected statement is
> the one in the 2026-09-11 fold at the end of this spec. ⇒ **"Check freshness before reverting" is not
> the remedy** — for a project whose own rules MANDATE reverting churn (API-Sheriff `CLAUDE.md` § Pre-Commit
> Process) it is not even an available move. The remedy is on the stamp: record the pre-build sha, or
> both, or accept a sha whose only delta from a stamped one is gate-owned churn.

## ⭐ FOLDED 2026-09-07 (c) — PLAN-TRUTH-125 drain + a live-plan finding (2 items)

`-005` (`build-server-client`) and `test-suite-anti-vacuity-002`:
**the scoped build gates cannot see what the whole-tree gate sees.**

⛔⛔ **A scope that changes what a gate can OBSERVE, not merely how long it takes.** A scoped run is
treated as a cheaper approximation of the whole-tree run; it is not — **there are findings only the
whole-tree gate can reach**, so a green scoped gate is not a weaker green, it is a green over a
different question.

⇒ **This is the same shape as the `build-maven` reactor-widening item folded into `-122`** (widening
scope changes which artifacts resolve, so the wide run is a DIFFERENT run, not a superset). ⭐ **Two
independent reports, opposite directions — narrowing loses observations, widening changes them.**
⛔ **Neither direction is a safe default, and D0 must stop treating scope as a dial with a safe end.**

## ⛔⛔⛔ FOLDED 2026-09-08 — lessons-handling drain (2 items). ONE NAMES THE MECHANISM BEHIND THIS EPIC'S OWN STRANDED `uv.lock`.

### `-023` — `pre-push-quality-gate` declares `mutates_source: false` while the gate command MUTATES

> *"The dispatcher reads that declared fact FIRST and, on `false`, SKIPS ITS COMMIT INSTRUMENTATION
> ENTIRELY — no staging, no commit, no owner for any diff the step produced."*

⇒ **The step mutates tracked source · the dispatcher never instruments a commit · the dirty tree
survives to `push`, where it either blocks the push or rides along uncommitted and unattributed.**

⭐⭐⭐ **THIS IS THE MECHANISM BEHIND THIS EPIC'S OWN OPEN DEFECT.** `uv.lock` has been dirty on main
since 2026-09-05, produced by a `mutates_source: false` step, **with nothing owning the commit** — and
we recorded that as *"nothing owns committing it"* without knowing why. **Now we know: the declaration
is read as a fact, and on `false` the owning code path is never created.**

⇒ **n = 2, two projects, one harness defect.** ⛔ **And it is not a per-project misconfiguration:** the
reporting project's own gate profile writes to the tree, ours relocks `uv.lock`, and in both cases
**the harness believed the command was non-mutating because the step SAID SO.**

⚠ **The sender states the split precisely and it must survive the fold**: the project half (their
`-Ppre-commit` running `rewrite:run` before its own dryRun assertion, so the gate cannot fail by
construction) **is being fixed separately as their PLAN-12, and fixing only that leaves the harness
still believing the command is non-mutating.** ⇒ **This is the HARNESS half and is not superseded.**

⛔ **The remedy cannot be "re-declare the step as mutating"** — the declaration is per-step and the
mutation is per-PROJECT, since the gate command is project-resolved. **A declared fact about a
project-resolved command is unknowable at declaration time**, which is the real defect.

### `-018` — a measured zero must be MEASURED: the build wrapper reported `tests_run=0`

⭐ Same family as the `routed_tests_run` transport half already folded here — **but that one was
already closed** (`_daemon_result_to_direct` leaves the key ABSENT when the inner verdict has no
count). ⇒ **This is a different producer reaching the same wrong answer**, so D0 must enumerate the
`tests_run` producers rather than assume the transport fix covered them.

## ⛔⛔ FOLDED 2026-09-11 — cross-repo lessons drain (7 items). THE `-023` HARNESS HALF SHIPPED; THE LEDGER HALF DID NOT.

Items: API-Sheriff `-006`; Token-Sheriff `-025`, `-027`, `-037`, `-042`, `-051`, `-055`. Verified
read-only at HEAD `356973d80` (= `origin/main`).

### `-023` is ANSWERED at HEAD — by the remedy the 2026-09-08 fold above ruled out

⛔ **#1454 (`f24b19a51`, 2026-09-08) flipped `pre-push-quality-gate.md`:8 to `mutates_source: true`**, gave
Branch A a purpose-authored `commit_message` so item 5f commits the gate's own edits, and moved the
`push.md` re-stale discriminator to `order >=`. OBSERVED at `356973d80`. ⇒ The fold above says *"the remedy
cannot be 're-declare the step as mutating' — a declared fact about a project-resolved command is
unknowable at declaration time"*. **#1454 dissolved that objection rather than answering it**: declaring
`true` is safe for a non-mutating project too, because 5f commits only what is dirty. **Drop the `-023`
harness limb at outline**; re-verify against #1454 rather than re-implementing it.

- `-025` then `-042` (a correction chain from the same sender): Token-Sheriff first made its gate
  non-mutating (PR #720), then **reversed** that (#728 restored the org-norm auto-fixer; #729 declared
  `"build.maven.profiles.mutating": "pre-commit"`). ⇒ The project now declares the truth, and the harness
  honouring it is load-bearing. OBSERVED: the authored `mutating` signal exists —
  `manage-architecture/standards/resolve-command.md` § "Authored `mutating` signal" and
  `build-maven/scripts/_maven_cmd_discover.py`:179 `EXT_KEY_PROFILES_MUTATING`. ⚠ The resume anchor's
  "Open Defect MECHANISM half still live, owned by `-105`" is therefore STALE for the pre-push instance.

### The LEDGER half is live — the stamp is post-churn (API-Sheriff `-006`)

- OBSERVED: `execute-script.py.template`:579 stamps the post-build sha (see the CORRECTED note on fold (b)
  above). A mandated revert of gate churn makes a demonstrably-passing verify permanently `stale`, and
  `phase-6-finalize/standards/push.md`'s reconciliation covers finalize-internal commits only — not reverted
  churn. **Both operator exits are wrong**: keep the churn (ship unrelated diffs) or revert it (freshness
  can never be satisfied). ⇒ New D-candidate for D0: **stamp the pre-build sha (or both) on `kind=build`
  rows**, or teach freshness to accept a gate-owned-churn-only delta.

### Clean-tree assertions cannot tell a mutating gate from interference (`-037`)

With the gate declared mutating and mutating correctly, every clean-tree checkpoint still reads the dirt
as a violation — the post-refine/post-outline `git status --porcelain` assertions, `manage-status
transition`'s `worktree_dirty_at_boundary`, phase-5's commit-ownership invariant, `phase_handshake
worktree_dirty`. The observed cost: an orchestrator blamed the user's IDE, **reverted the mandated
formatting twice**, and turned `assert-no-rewrite-changes` red. The tell it missed: `target/rewrite/rewrite.patch`
was byte-identical to the "mystery" diff. ⇒ The authored `mutating` field exists on the resolve result;
whether any clean-tree assertion CONSULTS it is the open question.

### A measured zero that is not a measurement — third relay (`-027`, `-055`)

- `-027` (**third** relay after `-006`/`-018`): every green `verify -Ppre-commit` returned `tests_run: 0` +
  `tests_population: measured` while surefire reports were written. Fold onto `-018` above — D0's producer
  enumeration.
- `-055`, **new limb, OBSERVED**: `script-shared/scripts/build/_build_shared.py`:870-873 derives
  `analyses_examined` from the command's analyses **independently of `tests_run`**, so a green build
  reports `analyses examined: compile, lint, test; 0 test(s) executed` — the two adjacent fields
  contradict each other. Measured at the sender: 2 of 3 "green" orchestrator-tier gates executed no test
  (one by construction, one because a Keycloak fixture was absent), and the summary line was identical
  for both. Remedy: omit `test` from `analyses_examined` when `tests_run == 0` is measured; add a
  `test_verification: none | partial | full` discriminator; distinguish "runs no tests by construction"
  from "configured tests were prevented". ⚠ **Do NOT make a zero-test build fail** — some commands
  legitimately run none.

### The `NO_PLAN` attribution — a producer site named (`-051`)

The architecture-resolved build `executable` carries no `--plan-id`, so `kind=build` rows stamp
`plan=NO_PLAN` and `pre-commit-verify-freshness` reports stale for a build that ran. This names a
concrete producer for the `plan=NO_PLAN` HYPOTHESIS already in § Claim Labels (R5: 424 of 433 rows
`NO_PLAN`/null). ⚠ The sender's "fix the composer, not the check" is right in direction.

### Claim labels for this fold

- OBSERVED: `pre-push-quality-gate.md`:8 reads `mutates_source: true` at `356973d80` (#1454, `f24b19a51`).
- OBSERVED: `execute-script.py.template`:579 computes the ledger `worktree_sha` after the build subprocess.
- OBSERVED: `_build_shared.py`:870-873 builds `analyses_examined` without reference to `tests_run`.
- HYPOTHESIS: no clean-tree assertion consults the resolved `mutating` field — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § the `worktree_dirty` invariant (verify-at-outline).
- HYPOTHESIS: the architecture-resolved `executable` omits `--plan-id` — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` § the `executable` composition (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-150-build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path.md` (PLAN-TRUTH-150)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
