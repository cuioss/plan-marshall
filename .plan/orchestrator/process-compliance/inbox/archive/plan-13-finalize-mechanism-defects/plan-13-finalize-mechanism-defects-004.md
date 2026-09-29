envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=finding
created=2026-09-28T16:03:15Z

# Process-rule issues observed during execute + finalize (plan-13-finalize-mechanism-defects)

## 1. Orchestrator-tier per-deliverable builds cost a full module-test run + a triage dispatch per deliverable

`module-tests plan-marshall` resolves to `execution_tier: orchestrator` (745–1437s), so every per-deliverable
Step 10b build yields out of the execute envelope. This run paid SIX 7–17-minute module-test runs (one per
deliverable, one timeout re-run, one for the fix task) plus FIVE `verification-feedback` dispatches, all
re-triaging the same single known failure (`test_lessons_pipeline_regression.py:60`) that was already mapped
to pending fix task TASK-11. Two structural causes:

- The fix task TASK-11 created by verification-feedback got `envelope_id: null` and was never scheduled
  before the remaining deliverables, so every later deliverable's build re-hit the known failure.
- `execution.md` has no "known failure already owned by a pending fix task" short-circuit: each build error
  must be routed through a fresh triage dispatch even when the finding is byte-identical.

## 2. Fix tasks created by verification-feedback have no envelope

TASK-11 carried `envelope_id: null`. The executor "runs only tasks whose envelope_id equals {E}", so no
envelope dispatch would ever run it; the orchestrator had to dispatch it with `envelope_id: null`, which no
document describes. `manage-tasks get` also does not surface `envelope_id` at all (only `next` does).

## 3. The orchestrator re-dispatch rules contradict each other at the end of execute

`execution.md` § orchestrator-tier table: a green orchestrator-tier build → "Re-dispatch phase-5-execute so the
leaf resumes; the freshness gate (Step 12a) now sees the stamp". The pre-dispatch queue peek in the same file:
"MUST NOT re-dispatch" when `loop-exit-guard` reports pending=0/in_progress=0. After the end-of-phase builds
went green the queue was empty, so the leaf's Step 12a freshness gate was never re-entered. This run followed
the MUST NOT.

## 4. Build errors are auto-persisted as findings twice; the orchestrator was told to route them anyway

The build wrapper persists each failing test as a plan finding — twice per run (once for the inner `./pw`
command, once for the outer executor command). `execution.md` never says so, so on the first failure the
orchestrator hand-filed a third, qgate-scoped copy (`8ffb06`) before dispatching triage. The documented path
for an orchestrator-run failing build should say the findings already exist.

## 5. The 10-minute Bash ceiling vs. "do not background the daemon wait"

`await-long-running.md` says the build consumer must not `run_in_background` or `sleep` the daemon wait.
Every orchestrator-tier build here exceeded the harness's 600s per-call ceiling (resolved budgets 745–1437s),
so the harness moved each call to the background anyway. The rule cannot be honoured as written; the build
client needs a bounded wait shorter than the harness ceiling with an explicit re-poll.

## 6. The first-yield leaf marks module_testing tasks `done` before any test ran

`finalize-step` auto-closes a task when its last step closes, so TASK-2/4/6/8/10 all showed `done` before the
orchestrator-tier module-tests run that is their only verification. A test failure then has no task to reopen.

## 7. Two phase-6 step bodies do their own dispatch but are rostered "dispatched"

`dispatch-inline-split.md` lists `default:finalize-step-simplify` and `default:pre-submission-self-review` as
DISPATCHED steps, yet both step documents contain their own `Task:` dispatches (simplify Step 3; self-review
Steps 2 and 3b, which must be issued "from the inline dispatcher context"). A dispatched leaf cannot dispatch,
so both must actually run in the main context. The roster is wrong for them.

## 8. pre-submission-self-review loop_back (target 6-finalize) names no fixer

Branch B says the findings "are amendments to the diff in hand" and the step loop is re-entered, but no
document says who amends the diff. Replaying without a fixer re-surfaces the same findings until the
`max_iterations` ceiling refuses. The operator had to choose "fix inline" by hand. Also ambiguous: whether an
ordinary findings-bearing round (accepted + may_close: no) must ALSO file the `further_round_owed` qgate
finding Step 3b describes.

## 9. The candidates envelope cannot be forwarded verbatim

The self-review surfacer returned 80.6 KB of TOON, over the harness inline tool-output limit, so the output was
persisted to a file. `requires_prompt_fields: candidates` demands the verbatim TOON in the prompt; the run
forwarded the byte-identical persisted file by path instead (logged). The contract needs a file-reference form.

## 10. A `--no-completion-log` re-stamp counts as a second firing

The item-5f `head_at_completion` re-stamp for `finalize-step-simplify` bumped `firing_count` to 2 and added a
`prior_firings` entry, so the record now claims the step fired twice when it fired once. Firing accounting
should ignore the re-stamp path.

## 11. No finalize step declares `verdict_inputs`, so every HEAD advance re-fires everything

`verdict_currency classify` returned `invalidated / verdict_inputs_undeclared` for lessons-housekeeping,
simplify and plugin-doctor after a docs-only 9-file fix commit, re-running all three in full (including a
~10-minute plugin-doctor pass). The preservation mechanism exists but no step opts in.

## 12. Stale `.plan/plans/` paths remain in ~45 marketplace files

The inline fix swept `.plan/plans/` → `.plan/local/plans/` only inside this plan's 9 in-scope files. The
fixer reported ~45 further inventoried docs/scripts still naming the pre-ADR-002 live-plan path (manage-files,
manage-findings, manage-logging, manage-metrics, manage-references, phase-5-execute, tools-script-executor,
ref-workflow-architecture, plugin-doctor rule-catalog, …). That is the same defect class as this plan's D2
(archive path) and needs its own plan with a doc-vs-resolver parity test for the live-plan path.

## 14. pre-submission-self-review cannot converge inside max_iterations on a doc-migration diff

This run spent all 5 finalize loop-back iterations on the self-review alone and was stopped by the
ceiling with 2 trivial, already-understood findings open. Each round's fixes surfaced the same defect class
one layer further out (stale paths in the edited file → in its sibling contract sources → in files the fix
itself touched), and every round forces a full re-fire of lessons-housekeeping, simplify and plugin-doctor
(no `verdict_inputs` declared, see 11). There is no disposition that lets the operator accept a residual
finding and close the step, and no documented fixer for its inline-fixable findings (see 8).

## 15. The verifier refused a clean round on the orchestrator's framing

The Step 3b prompt template requires the orchestrator to render `findings_detail`; for a clean round the
orchestrator passed per-list candidate counts, which the verifier summed (161) against `counts.total` (122)
and refused. `counts.total` excludes review-anchor lists by contract, but nothing in the verifier template
says so. The verifier template should carry the `in_total` membership, or forbid restating per-list counts.

## 16. plugin-doctor gates the declared footprint, not the realized one

After the operator-approved sweep added 35 files in ~12 further skills, plugin-doctor kept gating only the 8
skills derivable from `references.affected_files` (27 entries). `sync-affected-files` re-derives from the
solution outline only, so a finalize-time scope widening is never gated structurally.

## 17. A `verdict_refused` qgate finding has no resolution path

Step 3b files `verdict_refused` / `further_round_owed` findings with no file path, so `resolve-evidenced`
(keyed on changed paths) can never resolve them, and they stay pending — blocking the pre-merge findings gate.

## 18. The orchestrator recorded a dispatch's usage before its <usage> arrived

In iteration 5 the orchestrator issued accumulate/record-dispatch-boundary/record-step with an estimated
verifier share before the verifier's notification delivered its `<usage>`; the accumulator could only be
topped up (+620 tokens), and the recorded duration for that row stays overstated by 15622 ms. The workflow
should forbid recording a boundary before every dispatch in it has reported.

## 19. Re-entering finalize after a ceiling refusal cannot converge either

The operator chose "fix the 2 lines, accept the verdict_refused record, re-run finalize". The persisted
`loop_back_iteration` stays at 5/5, so the re-entry gets no new round; the closing full pass then found 4
MORE members of the adjacent `.plan/logs/` class (in contract sources of files the last fix touched), the
verifier refused again, and the ceiling refused again. A contract-source-radius review over a partial path
migration is structurally non-terminating: every fix moves the contradiction one contract hop outward. The
workflow needs either (a) a residual-acceptance disposition for the self-review, or (b) a rule that a path
migration must be completed repo-wide (with a resolver parity test) before finalize, not discovered by it.

## 20. An operator "no more review rounds" waiver has no documented mechanism

After the second ceiling refusal the operator said "fix the found issues but no more review round, just
continue". No document describes how to honour that: the run had to (a) `mark-step-done --force` the
self-review from `loop_back` to `done`, (b) resolve the `verdict_refused` finding as `accepted` by hand,
and (c) skip the head-dependent re-fires of lessons-housekeeping / simplify / plugin-doctor that the fix
commit triggers, recording the skip only as a free-text decision-log WARNING. None of these three moves is
a sanctioned disposition, so a later audit cannot tell a waived re-fire from a missed one.

## 21. pre-push-quality-gate's own builds can never satisfy the push freshness gate it anchors

The gate doc claims its just-completed builds are what make `default:push`'s freshness precondition pass
("only this gate's just-completed builds can have written [the ledger row] for the settled tree"). In
this run all four arms went green on the exact tree (quality-gate ×2, test-compile, 28128-test
module-tests), yet `pre-commit-verify-freshness` refused with `stale: build_scope_narrow` — every row is
`canonical_performs_too_few_analyses`, because the gate accepts only a single `verify` row. The finalize
pipeline therefore always pays a second full `verify` (~40 min) after the gate, or the push halts. Either
the gate should run `verify` (it already runs its three arms) or freshness should accept the union of
rows at one sha that together cover compile+lint+test.

## 22. The ci-complete wait clamps at 569s, so every CI run here needs 3+ blind re-waits

`ci_complete_precondition resolve` clamps its timeout to 569s (below the Bash ceiling), but this repo's
`verify` CI job takes ~25 min. The first two waits returned `wait_failed / ci_final_status: timeout`
with every check still IN_PROGRESS and none failed. ci-verify's contract would classify that as
`ci_timeout` findings and route them to LLM triage. The orchestrator had to re-run the wait by hand,
which no document describes. A non-terminal in-progress run should resolve as "pending, re-wait", not
as a timeout verdict.

## 23. Triage fix tasks cannot use `deliverable: 0` and the loop-back ceiling blocks PR fixes

The triage workflow prescribes `deliverable: 0` for fix tasks, but `manage-tasks commit-add` rejects it
("Missing required field: deliverable"), so the triager guessed owning deliverables (D4, D1). Separately,
the self-review loop spent all 5 `loop_back_iteration`s, so the first genuine PR-review loop-back
(2 CodeRabbit fixes) hit the ceiling and needed an operator override. The ceiling is shared across
unrelated loop-back sources; a runaway self-review can starve the PR-review loop entirely.

## 13. lessons-housekeeping Step 1 reads a retired field

`manage-references get --field modified_files` returns `field_retired`; the step fell back to
`compute-footprint` (lesson 2026-09-27-08-001 already records this).
