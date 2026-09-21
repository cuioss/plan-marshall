# PLAN-TRUTH-150: Build and CI verdicts that mislead specifically on the healthy path

## Objective

Nine build and CI signals that are wrong in the direction nobody checks: they mislead on the GREEN path.
A stale job's verdict is returned on re-attach and reads as success; a coverage timeout keyed off an unmeasured
name truncates only the runs that were passing; the Maven signal lies in both directions at once — a canonical
that can never pass, and a count that cannot add up; and five confident verdicts are refuted by data already
present at the same call site. Merged because every member is verified by the same discipline: a test pinned
on the path that lies, with a matched control on the path that does not.

## Deliverables

10 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive all three populations, and per confident-verdict member decide read-a-different-field vs new-call.** The green-path-only signal population (PLAN-TRUTH-105 D0), BOTH Maven defect populations (PLAN-TRUTH-122 D0), and the confident-verdict population with a per-member remedy choice (PLAN-TRUTH-118 D0). ⛔ Publish each population and its size — a remedy chosen before the population is derived is the archetype.
2. **D1 — `build_server wait` re-attach can return a STALE job's verdict, indistinguishable from success.** (PLAN-TRUTH-105 D1.)
3. **D2 — Whole-tree coverage keys its timeout off an unmeasured name, so ONLY green runs truncate.** (PLAN-TRUTH-105 D2.)
4. **D3 — `module-tests` emits a `test`-phase reactor request that can never resolve a sibling test-jar.** (PLAN-TRUTH-122 D1.)
5. **D4 — There is no project-side override, and the generated value wins by construction.** (PLAN-TRUTH-122 D2.)
6. **D5 — The green-build parser reports one summary block where the run produced several.** (PLAN-TRUTH-122 D3.)
7. **D6 — `pre-commit-verify-freshness` corroborates a full test run from a lint run.** (PLAN-TRUTH-118 D1.)
8. **D7 — `files_exist` reports a glob absent that its sibling check expands to 431 files.** ⛔ Re-derive the 431 at HEAD; it is a carried count, not a measured one. (PLAN-TRUTH-118 D2.)
9. **D8 — `_start_daemon` returns `running: True` on both branches, and `ci pr merge-queue`'s `enqueued: true` is a claim about the branch rule, not this PR.** (PLAN-TRUTH-118 D3 + D4.)
10. **D9 — `baseline-reconcile` counts merge-tree informational lines as conflicts — plus every matched control.** Each control pinned on the path that lies, with a matched control on the path that does not. (PLAN-TRUTH-118 D5 + PLAN-TRUTH-105 D3.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-105 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-105-build-execution-verdicts-that-mislead-specifically-on-the-healthy-path.md` § `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: no | evidence: Pointer at PLAN-TRUTH-105 Claim Labels: 13 verdicts including two contradicted (indices 1,3). Not yet re-scoped.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-122 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-122-the-maven-signal-lies-in-both-directions-a-canonical-that-cannot-pass-and-a-count-that-cannot-add-up.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-122 Claim Labels: 8 verdicts, 4 corroborated + 4 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-118 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-118-a-confident-verdict-refuted-by-data-already-at-the-same-site.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-118 Claim Labels: 5 verdicts, 3 corroborated + 2 unverifiable.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` — carried from PLAN-TRUTH-105
- `marketplace/bundles/plan-marshall/skills/manage-architecture/` — carried from PLAN-TRUTH-105
- `marketplace/bundles/plan-marshall/skills/manage-build-server/` — carried from PLAN-TRUTH-105
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — carried from PLAN-TRUTH-105
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — carried from PLAN-TRUTH-105
- `test/plan-marshall/` — carried from PLAN-TRUTH-105
- `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` — carried from PLAN-TRUTH-122
- `test/plan-marshall/build-maven/test_maven_cmd_parse.py` — carried from PLAN-TRUTH-122
- `test/plan-marshall/script-shared/test_build_parse.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_parse.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_jest.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_tap.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_jvm_patterns.py` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — carried from PLAN-TRUTH-122
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/**` — carried from PLAN-TRUTH-118
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md` — carried from PLAN-TRUTH-118
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — carried from PLAN-TRUTH-118
- `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/**` — carried from PLAN-TRUTH-118
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/**` — added 2026-09-15, folded from
  `plan-truth-148-003.md` (build-time oracle blind to 96 real builds)
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — already
  listed above; also covers the `.github/**` no-module resolution folded below
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md` — added
  2026-09-15 (c), folded from `api-sheriff-deployment-configurability-013.md` (no commit-addressed CI read)
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py` — added 2026-09-15 (c),
  folded from `api-sheriff-deployment-configurability-015.md` (`files_exist` blind to `depends_on`)

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-105-build-execution-verdicts-that-mislead-specifically-on-the-healthy-path.md` (PLAN-TRUTH-105)
- `PLAN-TRUTH-122-the-maven-signal-lies-in-both-directions-a-canonical-that-cannot-pass-and-a-count-that-cannot-add-up.md` (PLAN-TRUTH-122)
- `PLAN-TRUTH-118-a-confident-verdict-refuted-by-data-already-at-the-same-site.md` (PLAN-TRUTH-118)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-150-build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path.md"
```

## ⭐ FOLDED 2026-09-13 — TEMP RESIDUE POISONS THE LEARNED BUILD DURATIONS AND SILENTLY RE-TIERS CANONICALS

Folded from a candidate-lesson filed at PLAN-TRUTH-139's landing (`inbox/plan-truth-139-004.md`, PR
#1479). Expected Surface **unchanged** — already covered by the `script-shared/scripts/build/` and
`manage-architecture/` directory entries above.

A NEW member of this plan's own subject class: `module-tests` timed out at 873s (`adaptive
timeout_used_seconds=873`) on residue-poisoned test runs (52,704 files / 450MB, `run_config cleanup
--target temp` cleared it; the same build then finished green in 529s). This is not merely a slow build —
it is a **routing** change: the adaptive timeout learns from observed durations, including poisoned ones,
and when a learned `bash_timeout_seconds` crosses the 600s leaf Bash ceiling, `architecture resolve`
re-tiers the command to `execution_tier: orchestrator`, moving it out of the leaf's runnable slice
entirely. By the run's end `quality-gate` (968s) and `module-tests` (1473s) had both re-tiered this way,
after running `per_task` earlier in the same plan at 360s/501s. Nine yields to the orchestrator on this
basis, each a dispatch boundary.

A hygiene problem in `.plan/temp` therefore propagates into the execution topology through a learned
measurement, and nothing in the resolve output says the learned figure was taken from a run with hundreds
of megabytes of residue under it. Two-part remedy proposed by the source lesson: (1) mark a recorded
duration when its run's timeout fired or its temp footprint crossed a threshold, and prefer an unmarked
observation when learning — a timeout is a non-finish, not a duration measurement; (2) surface the
hygiene state of the learned figure at `architecture resolve` time, so a caller re-tiered by a poisoned
figure can tell it apart from a genuinely long build. D0 re-grounds this alongside the plan's other
carried claims and decides which existing deliverable (or a new D10) carries the remedy.

## ⭐ FOLDED 2026-09-14 — A GATE BUILD ROW'S `worktree_sha=None` IS HARMLESS BY CONVENTION, NOT BY INVARIANT

Forwarded via `review-apparatus` (`inbox/review-apparatus-040.md`, itself transferred from `plan-pr-046`'s
own finalize, PR #1477). Expected Surface unchanged — `script-shared/scripts/build/` is already covered
above. ⚠ The sending plan filed this because `plan-pr-046` declined the finding and then carried it
nowhere — it appears in none of that plan's other inbox messages. Dropped, not routed, until now.

`_append_gate_build_row` (`_build_execute_factory.py`, ~line 492) deliberately writes `worktree_sha=None`
into a `kind=build` row, documented in its own docstring. CodeRabbit raised it as `c5db78` (Major) on PR
#1477, resolved `taken_into_account` — the code observation was never disputed. Claimed consequence: a
direct `cmd_run` build appends a row with no currency hash, so a consumer reading it for freshness sees
`stale` and blocks the pre-commit transition. That consequence was argued unreachable on two grounds, and
BOTH rest on a convention about caller behaviour, not an invariant the code enforces — so the defect is
not *shown harmless*, it is *currently unreached*, a fragile distinction: a new caller that does not
follow the convention reaches it without anything failing loudly. The disposition record reads
`taken_into_account`, which presents as settled, while what actually holds it closed is an unwritten
convention no test pins — the epic's own archetype, one layer inside a review disposition. Suggested
settlement: either make the harmlessness an invariant (assert or type-enforce that a hash-less `kind=build`
row is never read for freshness), or write the currency hash and delete the argument. ⚠ The two
unreachability grounds were not re-derived in this checkout at HEAD.

## ⭐ FOLDED 2026-09-15 — THREE MORE MISLEADING-ON-THE-HEALTHY-PATH SIGNALS

Forwarded from `plan-truth-148-003.md`, `plan-truth-148-062.md`, and `review-apparatus-041.md` § B-020.
Expected Surface extended in the same act (see above, manage-change-ledger added for the first item).

1. **Build-time oracle recorded 0 builds while the plan made 96 build-wrapper calls totalling
   41,041,370ms (73.97% of all script time, 7× the next-largest entry).** Same "blind build-recording
   surface" archetype already recorded in this epic's history. New consequence named: `default:push`
   gates on the same ledger for a `kind=build` row matching `worktree_sha`, so an empty ledger is
   indistinguishable from the `worktree_mutated` stale route — a plan whose builds never reach the ledger
   passes that gate only by exemption, or not at all.
2. **The build wrapper mislabels a 15-second internal-subprocess TIMEOUT as `argparse_rejection`.**
   `pyproject_build`'s `get-worktree-path` resolution subprocess exceeded its hardcoded 15s timeout under
   heavy concurrent build-server load (visible in the surrounding log as multi-minute-ETA long-poll jobs)
   — a correct invocation, misclassified. Three identical firings in one run is a load-dependent flake,
   not a calling mistake; the timeout is too tight for a machine running concurrent multi-minute builds.
3. **A footprint path under `.github/**` resolves to `module: null`, silently widening scoped gates to
   whole-tree.** `architecture which-module` returns the same three attributors for every marketplace
   path AND for a no-discrimination null — observed consequences in one run: `pre-push-quality-gate`
   warned twice ("proceeding whole-tree"), and the execute-exit freshness gate refused a transition with
   `build_scope_narrow`/`divergence_possible=true`, demanding a whole-tree verify at orchestrator tier
   (2157s budget). A resolver that cannot answer is silently converting scoped gates into whole-tree ones
   — a cost, not just an imprecision.

## ⭐ FOLDED 2026-09-15 (c) — A SIXTH `tests_run: 0`, TRAILER ADVICE FILED AS BLOCKING ERRORS, A POST-MERGE RUN THE ABSTRACTION CANNOT READ, AND `files_exist` BLIND TO `depends_on`

Forwarded from `lessons-handling-26-09-04-01-059.md`, `lessons-handling-26-09-04-01-060.md` (both Token-Sheriff
PR #744), `api-sheriff-deployment-configurability-013.md` and `api-sheriff-deployment-configurability-015.md`.
Expected Surface extended in the same act (`tools-integration-ci/standards/leaf-command-reference.md` and
`manage-tasks/scripts/_cmd_qgate_mechanical.py`, above); the parser files are already declared.

1. **D5 — sixth recurrence of `tests_run: 0` over a green run, on `0.1.1670`.** Whole-tree `verify -Ppre-commit`
   (15-module reactor, `-T1C`, daemon-routed) logged BUILD SUCCESS with 3,083 tests; the wrapper reported
   `tests_run: 0`. Prior chain from the same sender: `-002`, `-041` (folded to superseded PLAN-TRUTH-122 D3),
   `-018`, `-027`, `-055` (folded to superseded PLAN-TRUTH-105) — all now this spec. ⛔ **The discriminator
   trap, named by the sender:** this is the MISCOUNT shape (`-002`/`-041`), not the zero-tests shape
   (`-055`), and both produce the same `0`. A fix that adds a "no tests ran" discriminator without making a
   failed aggregation report `unknown` / `tests_population: unmeasured` inherits the false zero.
2. **The Maven parser files failure-trailer advice as blocking `deprecation_warning` errors.** After a
   failing `verify -Pcoverage`, six trailer lines (`Re-run Maven using the -X switch…`, `[Help 1] http://…`,
   `mvn <args> -rf :<module>`) became pending build-error findings with category `deprecation_warning`,
   severity `error`, each suppressed by hand. Advice text is not a diagnostic, and the wrong category
   mis-routes triage. ⚠ HYPOTHESIS: an unrecognized `[ERROR]` line defaults to `deprecation_warning` —
   confirm/refute at `script-shared/scripts/build/_build_jvm_patterns.py` § the `deprecation_warning`
   pattern set (line 53 at `7a028157e`) and the fallback in `_build_parse.py` (verify-at-outline). The
   dedup-against-Q-Gate half is `PLAN-TRUTH-146`'s subject (see the `PLAN-TRUTH-145` 2026-09-15 (c) fold for
   the fan-out figures).
3. **No CI verb reads a run by commit, so a post-merge `main` run is unverifiable through the abstraction.**
   `checks status` takes `--pr-number` / `--head` and both resolve to a PR; `--head <sha>` returns "no pull
   requests found". Re-grounded at `7a028157e`: no `--commit` / `commit-runs` token exists in
   `tools-integration-ci` or `workflow-integration-github`. The consuming repo's `deploy-snapshot` runs
   only on `push: main`, so its only verdict is unreachable from the sanctioned seat and gets recorded as
   an unverified lead (or read via raw `gh run list --commit`, which the orchestrator persona forbids).
   Remedy direction: a commit-addressed read (`checks status --commit <sha>` or `checks commit-runs`)
   returning push-event runs in the shape the PR-keyed verbs already return. Routed here, not to
   `review-apparatus`: post-merge CI verification of a merge commit is landing truthfulness, not PR review.
4. **D7 — `files_exist` fails the other way too: it flags a file a predecessor task will create.** Forwarded
   from `api-sheriff-deployment-configurability-015.md` (API-Sheriff PR #305, finding `3100f9`, accepted as
   a false positive). TASK-006's step target `doc/user/tls-scenarios.adoc` was a write-new target of TASK-001,
   and TASK-006 declares `depends_on: TASK-001`; the mechanical check reads current disk state only, so every
   task consuming a predecessor-created file raises a warning that must be hand-accepted. Re-grounded at
   `7a028157e`: in `manage-tasks/scripts/_cmd_qgate_mechanical.py`, `depends_on` is read only by the
   `acyclic` check. D7 already carries this check misreporting a glob; the remedy scope now covers both
   directions — a path produced by any task in the target's transitive `depends_on` closure is satisfied.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
