envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:03Z

component=plan-marshall:phase-6-finalize
category=improvement
title=phase-6-finalize: loop-backs re-fire every step; scope re-firing to the changed files and run the coverage build before the first push
source_lesson=2026-11-18-07-007
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase-6-finalize: loop-backs re-fire every step; scope re-firing to the changed files and run the coverage build before the first push

# Candidate lesson: finalize loop-backs re-fired every step and pushed a multi_module feature past the 2.5M-token error anchor

- Source signal: plan-retrospective, plan-efficiency aspect ([BUDGET] error)
- Metrics: 3,871,880 dispatched tokens (floor: 1-init unmeasured, 6-finalize not yet closed) against the multi_module+feature error anchor of 2.5M. 5-execute 1.68M (6 closes), 6-finalize 1.41M. Worked time 71m (under the 120m anchor); wall 12h59m, mostly an overnight operator wait.
- Firing counts from status.metadata.phase_steps: finalize-step-simplify 7, pre-push-quality-gate 5, ci-verify 3, automatic-review 2, sonar-roundtrip 2. Loop-back budget `wait-region-unified-triage`: spent 4, one extra round granted by the operator.

## What happened

The original plan had 5 tasks. Finalize triage of CodeRabbit and Sonar findings added TASK-7 to TASK-10 over four unified-triage rounds (review fixes, the S5443 fix, coverage tests for the Sonar coverage gate, and a one-line S3415 fix). Each round looped back to 5-execute and then re-ran the finalize chain from the top. `finalize-step-simplify` ran 7 times and applied 3 edits in total; `pre-push-quality-gate` ran 5 times. Two of the rounds came from Sonar gates (new-code coverage, then an assertion-argument issue in the new coverage tests) that a coverage run before the first push would have shown.

## Candidate rule

Two separate levers: (1) a finalize loop-back whose fix task touched only test files, or one line, should not re-fire finalize-step-simplify over the whole footprint again; re-firing should be scoped to the files the fix task changed. (2) When the project's CI enforces a Sonar new-code coverage gate, the pre-push quality gate (or 5-execute exit) should run the coverage build once before the first push, so coverage and coverage-test findings arrive in one round instead of two.


## Recurrence in a later plan (plan-07-store-module-registry-spi, inbox plan-07-store-module-registry-spi-003 and -008)

- Source signal: the work log. `finalize-step-simplify` and `pre-push-quality-gate` completed at 09:51/09:54, again at 10:34/10:36 after the rebase onto origin/main, again at 11:31/11:33 after loop-back 1, and again after loop-back 2: four firings of each. Each pre-push gate is a full `verify -Ppre-commit` of about 1.5 to 2.5 minutes, each simplify is a dispatched agent.
- The automatic-review signal: 15 pr-comment findings and 10 Sonar findings were fixed over two loop-back rounds (18 findings, then 7 new CodeRabbit findings raised on the pushed fix head). CodeRabbit re-reviews every pushed head, so each loop-back can invite a further review round.

Two further levers on top of the two above: (3) order the rebase onto origin/main before the first simplify and pre-push run, so the rebase does not cost a firing of its own; (4) batch review fixes into fewer loop-backs, or budget one extra review round per loop-back, because a push re-triggers the bot. A further option from the message: skip simplify on a re-fire when the new head only adds commits already covered by a fresh simplify pass of the fix diff.



## Recurrence in a later plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-003 and -004)

- Message -003, source signal: phase-6-finalize sonar-roundtrip. The plan moved `git-worktrees` into `git-core` as a package with no behaviour change; Sonar analysed the moved file as new code and reported `java:S4449` (MAJOR) at `JGitWorktreeOperations.java:500` (a possibly-null `getObjectId()` passed to `StartPoint.of`). The operator chose to fix it in the PR: this added TASK-006 and loop-back iteration 1/3 (commit 6b45edb), which re-ran simplify, the pre-push quality gate, push, CI and the review-bot round, and the bot round then waited out a CodeRabbit rate window of 2100 s.
- Message -004, source signal: the work log after that loop-back. The commit was a behaviour-neutral three-line null-check in one file, yet `finalize-step-simplify` re-fired because its verdict was invalidated (`verdict_currency=invalidated, verdict_inputs_undeclared`, 16:43:51Z) and `pre-push-quality-gate` re-ran as four whole-tree Maven builds (16:44:27Z to 16:47:26Z), on top of the two builds 5-execute had just run for the same commit (16:38:22Z to 16:42:34Z, `verify:quality-gate` and `verify:module-tests`).

Same root cause as above, with two further levers: (5) a move or rename makes every relocated line new code to Sonar, so a plan that moves source files checks the moved files for open Sonar issues (or runs the equivalent static check) before the PR is opened and fixes them in the move deliverable or records a decision to accept them, instead of finding them first in the post-PR sonar-roundtrip; (6) steps that re-fire after a loop-back declare their verdict inputs, so a commit outside those inputs or below a size threshold keeps the earlier verdict, and the pre-push quality gate reuses a green 5-execute verify on the same HEAD instead of rebuilding. Owning components: phase-6-finalize (sonar-roundtrip timing, `finalize-step-simplify` verdict currency, `pre-push-quality-gate` reuse).


## Recurrence in a later plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-007)

- Source signal: orchestrator observation in the run's work log (re-fire lines at 2026-11-21T16:17:44Z, 16:18:39Z, 16:21:26Z, round-2 completions at 16:51-16:56). The finalize loop went back to 5-execute twice (TASK-10..15, then TASK-16..18); after each small round, and once more for the first pass, `finalize-step-simplify`, `pre-push-quality-gate` and `ci-verify` ran again in full, three times in total; the simplify re-fire was triggered only because "HEAD advanced, verdict_inputs undeclared".
- Same rule, with one lever more: batch the fix rounds. Collect the Sonar and review findings from one CI run before going back, instead of one go-back per source (here the second round found five `java:S1135` and a second `S6539` that the first round's fixes created).


## Recurrence in a later plan (plan-11-store-anchoring-signed, inbox plan-11-store-anchoring-signed-009)

PLAN-11 used 7.4M tokens (about 3x the 2.5M anchor for multi_module + feature) and 183 minutes of worked time; 6-finalize took 4.63M tokens (63%). Four loop-backs (PR re-open, two triage rounds, one inline Sonar fix) re-ran the same steps: finalize-step-simplify fired 7 times, pre-push-quality-gate, ci-verify and sonar-roundtrip 5 times each, automatic-review 6 times; the last two simplify rounds reviewed one-line test deltas and returned 0 edits. Concrete rule: on replay compare each step's `head_at_completion` with HEAD and the diff in between; skip, and record as a fact, a step whose input is unchanged; let `finalize-step-simplify` short-circuit when the delta touches no main-code file.
