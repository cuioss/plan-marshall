# PLAN-LB-22: Finalize loop control: retried steps record their outcome, loop-backs are budgeted per source, self-review can be closed, and a live CI run is not a timeout

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-22-finalize-loop-control.md` and is queued as one row file, `queue/PLAN-LB-22.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-10, PLAN-LB-02, PLAN-LB-05, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

Three faults make an ordinary finalize depend on `--force` or a hand-edited counter. `mark-step-done` refuses the retry and re-fire transitions every finalize step reaches on its normal path; one persisted counter caps every loop-back source and the pre-submission self-review has no sanctioned operator close; and a CI wait that lapses while the run is still going is filed as a `ci_timeout` finding that spends a loop-back round. This plan makes the retry transitions legal, makes `ci_verify` report what it wrote and what it saw, budgets loop-backs per source behind a logged grant verb and a recorded operator close, and declares `verdict_inputs` so settled steps stop re-firing. The three sources are one plan because they edit the same records and the same files: `manage-status/scripts/_cmd_mark_step.py`, `phase-6-finalize/scripts/ci_verify.py` and the dispatcher in `phase-6-finalize/SKILL.md`.

### Carried from PLAN-LB-10: A retried finalize step can record its outcome

`manage-status mark-step-done` refuses every write whose outcome differs from the stored one unless the caller passes `--force`. A finalize step reaches that state on its ordinary path: it records `failed` or `loop_back`, is retried, succeeds, and its `done` is refused with `error: conflict`; nothing is written, the dispatcher's completion guard then halts the phase, and the run only continues when someone adds an undocumented `--force`. The mirror case is worse: a gate that was `done` and comes back red on a re-fire cannot record `failed`, so the stale `done` stays and the pipeline carries on past a red gate. One finalize needed the override three times (sync-baseline, push, automatic-review). `ci_verify` adds a false report on top: on green it issues the mark without `--force`, ignores the answer, and returns `step_marked_done: true` while the record still says `loop_back`. This plan makes the retry and re-fire transitions legal in the tool, makes `ci_verify` report what was written, and brings the step documents and the contract text in line. Carries forward process-compliance PLAN-21 deliverable D2 including its later widening to step-record transitions, and truthful-signals PLAN-TRUTH-170's `ci_verify` fold and the missing-`--force` sweep of its D1.

### Carried from PLAN-LB-02: Pre-submission self-review can be closed, cannot starve PR review, and stops re-running settled steps

`default:pre-submission-self-review` has two exits: a clean round the verifier agrees to close, or the
finalize loop-back ceiling. Recent plans ran 4 to 14 rounds and were ended by the operator with moves no
document sanctions — `mark-step-done --force` from `loop_back` to `done`, a hand-resolved finding, and a
hand-edited `loop_back_iteration`. One persisted counter caps every loop-back source, so a self-review that
spends it leaves the first real PR-review fix with no round. The findings the step files for a refused
verdict carry no file path, so nothing can resolve them and they block the pre-merge findings gate. And each
round re-fires `finalize-step-simplify` and `finalize-step-lessons-housekeeping` in full because neither
declares which files its verdict depends on; one run measured six firings of each with zero edits every
time. Give the operator a recorded way to grant rounds or close on named residual findings, budget
loop-backs per source, make the step's own state findings resolvable, and declare `verdict_inputs` on the
two steps so a small fix commit does not re-run them. Carries forward process-compliance PLAN-20
deliverables D2–D4 and post-run-quality PLAN-PRQ-10 deliverable D1 (the `verdict_inputs` route only).

### Carried from PLAN-LB-05: Wait procedures the harness cannot run

Three finalize waits tell the agent to pace a poll with a standalone foreground `sleep`, which the
harness refuses, so the wait's budget is unreachable: the review-bot completion poll ended after a few
unpaced reads and the step was marked done while the bot was still reviewing; the merge-lock admission
wait and the merge-queue landing wait have the same shape. Two further waits mislead rather than block:
documents disagree on whether an orchestrator-tier build may run in the background, and a CI wait that
lapses while every check is still running is filed as a `ci_timeout` finding and costs a triage round.
This plan moves each short pacing wait into the script that owns the query (a bounded, script-side wait
the caller re-issues), states one runnable rule for long builds, and classifies a lapsed wait on a live
run as "still pending". Carries forward process-compliance PLAN-23 deliverable D4 (D4a, D4b) and the
remedy direction of truthful-signals PLAN-TRUTH-169 (folded recurrences) and PLAN-TRUTH-162 (D3, second
member).

## Deliverables

1. **[PLAN-LB-10 D1]** **Retry and re-fire transitions are legal without `--force`.** In `cmd_mark_step_done`, replace the blanket "different outcome ⇒ `conflict`" rule with an explicit transition table. Legal without `--force`: from `failed` or `loop_back` to any outcome (a retry or a later round reporting its own result), and from `done` to `failed` or `loop_back` (a re-fired gate that is now red or has new findings). Every legal transition goes through the existing `_extend_firing_history` path, so the superseded firing stays in `prior_firings` and `firing_count` rises; nothing is lost by dropping the flag. All existing refusals that are about well-formedness stay exactly as they are and are evaluated first (`missing_head_at_completion`, `unknown_head_at_completion`, `unknown_yield_name`, the `--loop-back-target` pairing, the display-detail checks). `--force` keeps working for every transition, so callers that still pass it see no change. The transitions that remain refused without `--force` are settled by the verify-first clause below. *Done when:* a test walks `failed → done` through the documented call with no `--force` and asserts `status: success`, `changed: true`, `previous_outcome: failed`, `firing_count: 2` (red before the change: `error: conflict`); companion tests cover `loop_back → done`, `failed → skipped`, `failed → loop_back`, `done → failed` and `done → loop_back`; a test asserts that a transition left outside the table still returns `conflict` and writes nothing.

2. **[PLAN-LB-10 D2]** **`ci_verify` reports the write, not the path taken.** `_run_mark_step_done` returns the proxy result and the green branch of `verify` reads it: `step_marked_done` is `true` only when the mark returned `status: success`; otherwise it is `false`, the result carries the mark's `error` and `message` (for example `step_mark_error: conflict`), and the top-level result is not a clean green — the caller must be able to tell "CI is green and the step is recorded" from "CI is green and the record was refused". After D1 the green mark over a stored `loop_back` or `failed` succeeds by itself; this deliverable covers every other refusal (`missing_head_at_completion` when HEAD could not be resolved, `unknown_yield_name`, an unreachable executor). *Done when:* a test injects a `mark_done_runner` that returns `{status: error, error: conflict}` and asserts `step_marked_done is False` and the error is surfaced (red before the change: `True`); the existing green-path tests still assert `True` with a succeeding stub; an end-to-end test over a real status file with a stored `loop_back` record shows the record reads `done` after a green `ci_verify` run.

3. **[PLAN-LB-10 D3]** **The dispatcher's own `failed` records land.** The finalize dispatcher writes `--outcome failed` itself in three places (per-agent timeout, the missing-terminal-record guard, the `wait_failed` precondition). Each can land on a record that already says `done` or `loop_back` from an earlier firing. With D1 these writes succeed; this deliverable adds the missing instruction to parse the result of each such call and to stop with the tool's message when it is still refused, instead of continuing as if the failure had been recorded. *Done when:* each dispatcher-side `mark-step-done … --outcome failed` block in `phase-6-finalize/SKILL.md` is followed by a `status` parse, and a doc-contract test pins that.

4. **[PLAN-LB-10 D4]** **The contract text and the step documents match the tool.** Rewrite the `--force` paragraphs in `phase-6-finalize/standards/external-step-contract.md` (today: "`--force` is REQUIRED whenever the outcome being written DIFFERS from the one already stored") and the `conflict` / `--force` text in `manage-status/SKILL.md` and the module docstring of `_cmd_mark_step.py` to state the transition table. Then sweep every finalize step document's terminal `mark-step-done` calls and publish the population in the PR body: for each re-fireable step, each terminal branch, whether it carries `--force`, and whether it still needs it after D1. Flags that are now redundant may stay; a branch that performs a transition the table does not allow without `--force` and lacks the flag is fixed. *Done when:* a derived test enumerates the terminal `mark-step-done` invocations in the step documents the finalize registry discovers and asserts that none performs a transition outside the unforced table without `--force`; the population table is in the PR body with its size.

5. **[PLAN-LB-02 D1]** **A logged verb grants further rounds.** A plan-scoped `manage-status` verb grants N additional
   loop-back rounds to a named source, records who granted it and why (reason required), and is the only
   sanctioned way past a ceiling refusal. The ceiling's STOP display in `phase-6-finalize/SKILL.md` Step 3
   item 7b names that verb instead of telling the operator to "re-run finalize", which the persisted counter
   defeats. Setting `loop_back_iteration` through `manage-status metadata --set` stops being the way to do
   it.
   Done when: a test drives the counter to the ceiling, shows the admission gate refusing, runs the grant
   verb with a reason, and shows the next loop-back admitted and the grant present in the plan's status
   record; a grant without a reason is refused.

6. **[PLAN-LB-02 D2]** **A recorded operator close on named residual findings.** One sanctioned disposition closes
   `pre-submission-self-review` without a further round: it names the residual findings it accepts (by
   `hash_id`), resolves exactly those as `accepted` with the operator's rationale, and records the step
   `done` with facts that say the close was an operator override and not a verifier `may_close: yes`
   (for example `may_close=operator_override`, plus the accepted count). Head-dependent settle steps the
   operator chooses not to re-fire after the last fix commit are recorded on their own step records as
   skipped with that basis, not as a free-text WARNING. `pre-submission-self-review.md` § "Round-loop
   termination" names this as the *out of budget* close's mechanism.
   Done when: a test closes a step holding a live `loop_back` record through the disposition and reads back
   `outcome: done`, the override fact, and the named findings as `accepted`; an unnamed pending finding
   stays `pending`; the documented flow contains no bare `mark-step-done --force` for this case. A later
   audit can tell the override close from a verifier close by reading the step record alone.

7. **[PLAN-LB-02 D3]** **Loop-back budgets are per source.** The single `status.metadata.loop_back_iteration` counter becomes
   one count per requesting step (the `step_ref` that recorded `loop_back`), each compared against
   `phase-6-finalize.max_iterations`. A self-review that has spent its budget no longer causes the
   admission gate to refuse a loop-back requested by `automatic-review`, `sonar-roundtrip` or any other
   step. How a plan already in finalize, whose status still carries the old scalar, is read is decided at
   outline and stated in the SKILL; the scalar is not silently attributed to one source.
   Done when: a test spends `max_iterations` rounds under `default:pre-submission-self-review`, then shows a
   loop-back from a different step admitted at iteration 1 of its own budget, while a further self-review
   loop-back is still refused; `execution.md` and `execution-recovery.md` no longer say the cap is one count
   across both tiers.

8. **[PLAN-LB-02 D4]** **The step's own state findings can resolve.** The findings Step 3b files for a non-closing verifier
   state (`verdict_refused`, `further_round_owed`, `verifier_unavailable`) get a resolution path: they are
   filed with a stable key that identifies them as this step's state findings, and the round that closes
   the step — a Branch A close or the Deliverable 2 operator close — resolves every pending one, citing the
   closing HEAD. Where a refusal rationale names a specific file the finding also carries `--file-path`, so
   `qgate resolve-evidenced` can resolve it when a fix touches that file.
   Done when: a test files one of each state finding, closes the step, and `qgate list --phase 6-finalize
   --resolution pending` returns none of them; a state finding filed in a round that did not close stays
   `pending`.

9. **[PLAN-LB-02 D5]** **`finalize-step-simplify` and `finalize-step-lessons-housekeeping` declare `verdict_inputs`.** Each
   step's frontmatter declares the fnmatch globs naming the tracked paths its verdict reads, so the existing
   verdict-currency classifier returns `preserved` and the dispatcher skips the step when a loop-back fix
   commit touches none of them. The admissibility bar is the one `ext-point-finalize-step.md` already
   states: the globs must be a superset of everything the verdict reads. If the outline finds that no
   admissible superset narrower than "every file" exists for one of the two steps, that step instead gets
   the recorded refusal-on-evidence paragraph `finalize-step-plugin-doctor` already carries, and the plan
   says so in its PR.
   Done when: for each step that gains a declaration, a test runs `verdict_currency classify` over a
   two-commit fixture whose second commit touches only a path outside the declared globs and gets
   `preserved` / `disjoint_from_verdict_inputs`, and over one whose second commit touches a declared path
   and gets `invalidated` / `verdict_inputs_matched`. A skipped firing is recorded as skipped with its
   basis, never as a firing that ran and found nothing.

10. **[PLAN-LB-05 D5]** **A wait lapse on a live CI run is "pending", not a finding.** In `consume-failures` mode the
   precondition returns `wait_failed` / `ci_final_status: timeout` when its clamped wait ends, and
   `ci_verify.py` then retains every still-running check and classifies it `ci_timeout`
   (`wait_outcome == deadline_exceeded` routes any check without a definitive conclusion to the
   timeout row). On a repository whose verify job outlasts the clamped wait this files findings on
   every first read and spends a loop-back round on a run nothing has failed in. Change the
   classification: a check that is pending, queued or in progress when the wait deadline passes
   produces no finding; the executor returns a distinct pending outcome and the dispatcher re-issues
   the precondition, up to a documented bound of re-waits, before anything is filed. `ci_timeout`
   stays for a check whose own conclusion is `timed_out`, and for a run still not terminal after the
   re-wait bound. Done when: a test feeding `deadline_exceeded` with only in-progress checks gets
   zero findings and the pending outcome; a test with a `timed_out` conclusion still gets one
   `ci_timeout` finding; a test past the re-wait bound gets the finding; and `ci-verify.md` row (h)
   and the precondition table in `phase-6-finalize/SKILL.md` describe the same behaviour.

## Claim Labels

Carried in source order: bullets 1 to 14 from PLAN-LB-10; bullets 15 to 33 from PLAN-LB-02; bullets 34 to 37 from PLAN-LB-05.

- OBSERVED: any write whose outcome differs from the stored one returns `{status: error, error: conflict, existing_outcome, requested_outcome}` and writes nothing unless `args.force` is set; there is no per-transition distinction — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` § `cmd_mark_step_done` lines 655-668, at HEAD `6edefac32`
- OBSERVED: the comment directly below that check describes "the outcome-changing re-fire path (loop_back → done, and the --force overwrite)" as if `loop_back → done` reached it unforced; it does not, the conflict return above it fires first — read at `_cmd_mark_step.py` lines 684-686
- OBSERVED: an outcome-changing write already preserves the superseded firing (`prior_firings`, `firing_count`), so allowing a transition without `--force` discards no history — read at `_cmd_mark_step.py` § `_extend_firing_history` (lines 742-791) and its call at line 687
- OBSERVED: `_run_mark_step_done` issues `mark-step-done --outcome done --display-detail … --head-at-completion …` with no `--force` — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` lines 389-417
- OBSERVED: the green branch calls `mark_done_fn(...)`, discards its return value, and returns `'step_marked_done': True` unconditionally — read at `ci_verify.py` § `verify` lines 629-648
- OBSERVED: the contract document tells every external step that `--force` is required whenever the written outcome differs from the stored one, and names "a re-fireable step's clean branch overwriting the `loop_back` its own previous round stored" as the canonical case — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` lines 37-45 and 59
- OBSERVED: most step documents do not follow that instruction. Counting lines that contain `--outcome done` against lines that contain `--force` per document: `workflow/sonar-roundtrip.md` 6/0, `workflow/lessons-capture.md` 6/0, `automatic-review/SKILL.md` 5/0, `workflow/create-pr.md` 4/0, `standards/finalize-step-sync-baseline.md` 3/0, `workflow/adr-propose.md` 3/0, `standards/record-metrics.md` 3/0, `.claude/skills/finalize-step-plugin-doctor/SKILL.md` 6/0, `.claude/skills/finalize-step-review-retrospective/SKILL.md` 6/0; `standards/branch-cleanup.md` 10/11 and `workflow/pre-submission-self-review.md` 6/12 do carry it — counted by text search at HEAD; a line count, not a per-branch reading
- OBSERVED: the dispatcher writes `--outcome failed` without `--force` at the per-agent timeout, at the missing-terminal-record guard and at the `wait_failed` precondition — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` lines 995-998, 1159-1162 and 502
- OBSERVED: the existing `ci_verify` tests assert `step_marked_done is True` with a stub runner that cannot refuse — read at `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py` lines 264-270
- HYPOTHESIS: `sync-baseline`, `push` and `automatic-review` are the steps whose `failed → done` retry was refused in one finalize, forcing `--force` three times — reported by a run, not reproduced; confirm/refute by driving `cmd_mark_step_done` over a stored `failed` record with each step's documented terminal call from `standards/finalize-step-sync-baseline.md`, `standards/push.md` and `automatic-review/SKILL.md` (verify-at-outline)
- HYPOTHESIS: a `ci_verify` green run left a `loop_back` record unchanged across two invocations while returning `step_marked_done: true` — observed in a consumer repository run, consistent with the two OBSERVED code facts above; confirm/refute with the end-to-end test of D2 (verify-at-outline)
- HYPOTHESIS: no reader of `status.metadata.phase_steps` depends on a `conflict` refusal to detect a re-fire — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_assert_step_recorded.py` and the item-1 re-entry check in `phase-6-finalize/SKILL.md` (verify-at-outline)
- Verify-first clause: before scoping D1, settle the residual refusals. Proposed table: `failed → *` and `loop_back → *` legal; `done → failed` and `done → loop_back` legal; `done → skipped`, `skipped → *` and the legacy bare-string entry stay refused without `--force`. Check each proposed-legal transition against the readers of the record (`_cmd_assert_step_recorded.py`, `plan-marshall/scripts/_invariants.py` § `_capture_phase_steps_complete`, `phase-6-finalize/scripts/verdict_currency.py`) for one that would mis-read a now-silent overwrite; a transition a reader cannot tolerate stays refused and the plan records why
- Verify-first clause: before scoping D4's sweep, derive the re-fireable population from the finalize step registry (the discovery path `_cmd_mark_step.py` § `_derive_phase_roster` uses) rather than from the file list above, so project-local steps under `.claude/skills/finalize-step-*` and bundle steps are both covered
- OBSERVED: one persisted counter caps every loop-back source — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1475-1502` (item 7b (i): reads `status.metadata.loop_back_iteration`, refuses when `{loop_back_iteration} + 1 > max_iterations`, otherwise persists the increment); no `step_ref` participates in the comparison.
- OBSERVED: the ceiling's STOP display ends "Then re-run finalize when you are ready to give it another round" and names no way to obtain a round — `phase-6-finalize/SKILL.md:1490`; the same section states the count is persisted so a re-run "resumes against it instead of resetting" (`:1631`, `:1635`).
- OBSERVED: `max_iterations` defaults to 3 and both tiers share it — `phase-6-finalize/SKILL.md:109`; `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:652` ("counted across both tiers"); `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md:77`.
- OBSERVED: `manage-status` has no grant-rounds or waiver verb — the `add_parser(...)` roster in `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` (:117-875) holds `metadata`, `mark-step-done`, `assert-step-recorded`, `merge-authorization grant|check` and no loop-back verb.
- OBSERVED: the self-review has no close other than Branch A (verifier `may_close: yes`) and the ceiling — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` § "Step 4" (Branch A preconditions :528-553; Branch B always records `loop_back` :604-647) and § "Round-loop termination" (:694 "no new outcome", :700 *out of budget* closes "on a recorded WARNING DEVIATION").
- OBSERVED: Step 3b files its state findings without a file path — `pre-submission-self-review.md:513-518` (`qgate add ... --title "{state} at pre-submission-self-review" --detail "{rationale}" --component ... --severity warning`, no `--file-path`), while the per-finding call in Branch B does pass `--file-path` (:613-618).
- OBSERVED: a finding with no `file_path` is never resolved by evidence — `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:1254-1259` (docstring: a finding "that carries no `file_path` at all — is LEFT `pending`") and the test at `:1291` (`if file_path and file_path in changed`).
- OBSERVED: `qgate add` accepts `--rule`, which is folded into the dedup discriminator — `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py:463`; a candidate carrier for the stable key in Deliverable 4.
- OBSERVED: a head-dependent step that declares no `verdict_inputs` re-fires on every real HEAD advance — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py:139` (`REASON_UNDECLARED`), `:200` (`if not verdict_inputs:` returns invalidated); the dispatcher consults it at `phase-6-finalize/SKILL.md:565-578`.
- OBSERVED: no finalize step declares `verdict_inputs` — a search for a line starting `verdict_inputs` under `marketplace/bundles/` and `.claude/skills/` returns nothing; `finalize-step-plugin-doctor` (`.claude/skills/finalize-step-plugin-doctor/SKILL.md:50`) and `pre-push-quality-gate` (`standards/pre-push-quality-gate.md:445-447`) record a deliberate refusal to declare.
- OBSERVED: both target steps are `head_dependent: true` and `mutates_source: true` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md:9-10` (order 5) and `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:13-14` (order 4).
- OBSERVED: `verdict_inputs` is an optional implementor frontmatter key meaningful only with `head_dependent: true` — `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:56`.
- HYPOTHESIS: the lessons-housekeeping verdict also reads state outside the tracked tree (the lessons corpus, resolved main-anchored, and the plan outcome), so a path-glob declaration over tracked files may not be a superset of its inputs — confirm/refute at `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` § Step 3 classification inputs (verify-at-outline).
- HYPOTHESIS: the simplify verdict reads only the plan's changed code files, so a documentation-only fix commit cannot change it — confirm/refute at `phase-6-finalize/standards/finalize-step-simplify.md` § Workflow (what the review reads, and whether it reviews Markdown) (verify-at-outline).
- HYPOTHESIS: `mark-step-done --fact` accepts an arbitrary `may_close` value and the step's `records_facts` obligation admits `operator_override` — confirm at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` § fact validation and the `records_facts` frontmatter of `pre-submission-self-review.md` (verify-at-outline).
- HYPOTHESIS: run-reported scale — one plan fired the self-review 13 times with 10 loop-backs and closed by operator override with finalize at 59% of 19.85M tokens; another re-fired lessons-housekeeping, simplify and plugin-doctor six times each with zero edits at 56K–154K tokens per firing. Not reproduced here; the archived plans' `metadata.phase_steps` would confirm (verify-at-outline).
- Verify-first clause: read the contract shipped by PR #1488 ("a self-review that decides its own close") before designing Deliverable 2, so the operator close extends the verifier-owned stop decision instead of bypassing it.
- Verify-first clause: enumerate every reader and writer of `loop_back_iteration` (SKILL.md Step 3 pre-loop read at :701-711, item 7b, the declared-footprint refresh message, archive handling in `manage-status/scripts/_cmd_lifecycle.py`, tests) before changing its shape in Deliverable 3.
- Verify-first clause: for Deliverable 5, list what each step's verdict actually reads before writing a glob; a declaration that is not a superset buys a false skip, which is worse than the re-fire.
- OBSERVED: the ci-arm precondition returns `wait_failed` / `ci_final_status: timeout` / `wait_outcome: deadline_exceeded` when the clamped wait ends, while only the per-signal arms map the same condition to `arm_pending` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py:741-787`, `:864-876`
- OBSERVED: `ci_verify.py` retains pending checks under `deadline_exceeded` and classifies any check without a definitive conclusion as `ci_timeout` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py:193-194`, `:731-751`; the documented contract says the same at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md:189`, `:195-203` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:503`, `:505`
- HYPOTHESIS: the clamped wait is about 569 s against a verify job of about 25 minutes in this repository, so the first reads of a normal run always lapse — confirm/refute at `ci_complete_precondition.py` § `_clamp_wait_ceiling` and `_MAX_INNER_WAIT_SECONDS` plus the recorded duration of recent `verify` runs (verify-at-outline)
- Verify-first clause: for deliverable 5, read how the dispatcher consumes `consume-failures` at `phase-6-finalize/SKILL.md` § "Precondition resolution" and decide whether the re-wait is driven by the precondition (returning a pending status the dispatcher loops on) or by the executor; one owner only.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — transition table in `cmd_mark_step_done`, module docstring (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — `mark-step-done --force` help text (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — § mark-step-done: conflict rule, `--force`, error table (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — `_run_mark_step_done` result read, `step_marked_done` derivation, module docstring (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — dispatcher-side `--outcome failed` blocks get a result parse (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` — `--force` paragraphs (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — how the step reads `step_marked_done` and the new error field (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` — step documents whose terminal branch the sweep finds outside the unforced table; expected to be few or none after D1 (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/` — same sweep, workflow-form step documents (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — same sweep, the review step's terminal branches (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — same sweep, project-local step (six `--outcome done` lines, no `--force`) (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — same sweep, project-local step (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — same sweep, project-local step (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — only if it restates the `--force` rule (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-status/test_mark_step_done_mark_step_force.py` — existing forced-overwrite tests stay green; conflict-residue test added here or beside it (D1)
- HYPOTHESIS: `test/plan-marshall/manage-status/test_mark_step_done_retry_transitions.py` — new transition-table tests (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_core.py` — refused-mark test and end-to-end record test (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py` — `step_marked_done` assertions follow the derived value (D2)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_step_terminal_mark_transitions.py` — new derived sweep test over the registry's step documents (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — Step 3 pre-loop counter read and item 7b admission gate, STOP display (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Step 3b" state-finding filing, § "Step 4" Branch B and the closing paragraph, § "Round-loop termination" (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — new grant / operator-close verbs (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — override fact and skipped-with-basis record (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — verb documentation (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — new command module for the per-source counter and grant (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — archive-time handling of the loop-back record, only if the counter's shape change reaches it (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — resolution of the step's state findings (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — CLI surface for that resolution (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — documented resolution path (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — "counted across both tiers" (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` — § Loop-back continuation cap (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — `verdict_inputs` frontmatter and the re-fire paragraph (D5)
- OBSERVED: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — `verdict_inputs` frontmatter or recorded refusal (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` — adopter list / model text (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — only if a declared step needs a discovery or matching fix; the classifier is expected to work unchanged (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — ceiling, grant, operator-close and verdict-currency cases beside `test_loop_back_outcome_*.py` and `test_verdict_currency_*.py`
- OBSERVED: `test/plan-marshall/manage-status/` — grant verb, per-source counter, override record
- OBSERVED: `test/plan-marshall/manage-findings/` — state-finding resolution beside `test_findings_store_resolution.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — `classify_check` and the failing-check filter (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py` — ci-arm lapse resolution (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — taxonomy row (h) and its note (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — § "Precondition resolution" table only (D5)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_core.py` — pending-versus-timeout classification (D5)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_complete_precondition_checks.py` — lapse resolution (D5)

## Dependencies and Sequencing

- Depends on: none.
- Suggested order inside the plan: the PLAN-LB-10 deliverables first. Once `failed -> done` and `done -> failed` are legal without `--force`, the operator close of PLAN-LB-02 D2 and the dispatcher-side `failed` records need no override of their own.
- Overlaps with: PLAN-LB-24, PLAN-LB-25 and PLAN-LB-27 on `phase-6-finalize/SKILL.md`; PLAN-LB-25 on `manage-status/scripts/manage-status.py` and `manage-status/SKILL.md`; PLAN-LB-26 and PLAN-LB-27 on `plan-marshall/workflow/execution.md`; PLAN-LB-26 and PLAN-LB-28 on `phase-6-finalize/workflow/pre-submission-self-review.md`; PLAN-LB-26 on `manage-findings/scripts/_findings_core.py`; PLAN-LB-23 through the directory-level entries this spec declares under `phase-6-finalize/standards/`. This plan is the hub of the finalize work: sequence it against every one of those and run it first.
- May run together with: PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31, which share no file with it.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-10:

- Depends on: none.
- Overlaps with: PLAN-LB-09 (`manage-status/scripts/`, `phase-6-finalize/standards/archive-plan.md` via the sweep, `phase-6-finalize/SKILL.md`; if this plan lands first, LB-09 can record `failed` over `done` on a refused archive without `--force`); PLAN-LB-02 (`phase-6-finalize/SKILL.md`, `workflow/pre-submission-self-review.md` if the sweep touches it, `.claude/skills/finalize-step-*`); PLAN-LB-05 (`standards/ci-verify.md`, `standards/branch-cleanup.md`, `automatic-review/SKILL.md`); PLAN-LB-11 (`phase-6-finalize/SKILL.md`, a different item); PLAN-LB-18 (`automatic-review/SKILL.md`). All are document-section overlaps except LB-09's; sequence with LB-09 and LB-02, and re-run the sweep after whichever lands second.
- Adjacent to: `manage-status/scripts/_cmd_assert_step_recorded.py` is read for the verify-first clause and not edited; the firing-history shape (`prior_firings`, `firing_count`) is reused unchanged.
- Left out on purpose (the rest of the two source specs): process-compliance PLAN-21 D1 (dispatch roster), the re-stamp firing-count part of D2, D3 (`verdict_inputs`), D4 (plugin-doctor realized footprint), D5 (dispatch-boundary records); truthful-signals PLAN-TRUTH-170 D0, D2 (`[OUTCOME]` emission), D3 (`display_detail` ceiling), D4a (derived `head_at_completion`), D4b (`assert-step-recorded --require-terminal` on a stale record), D5 (staging allowlist — that is PLAN-LB-11) and the `pr_number` fold.

From PLAN-LB-02:

- Depends on: none.
- Overlaps with: PLAN-LB-03 (`PLAN-LB-03-self-review-consumer-repos.md`) — both edit `phase-6-finalize/workflow/pre-submission-self-review.md`. Section ownership: THIS plan owns § "Step 3b" from the non-closing state table through the `qgate add` block and the unverified-dispatch paragraph, § "Step 4" Branch B and the paragraph that closes Step 4, and § "Round-loop termination". PLAN-LB-03 owns § "Domain-Aware Candidate Surfacing", § "Step 1" (implementor selection and the zero-generator fallback), the non-finding verdict vocabulary in § "Dispatched-envelope output", the boundary lines of the Step 3b verifier prompt, and the new not-covered branch in § "Step 4". Neither plan edits the other's sections. Sequence the two, never run them together; the second to start rebases onto the first. PLAN-LB-03 is the smaller plan and is suggested first.
- Overlaps with: PLAN-LB-11 (`PLAN-LB-11-finalize-staging-allowlist.md`) — `phase-6-finalize/SKILL.md` (it edits the commit seam, this plan edits Step 3 item 7b). Sequence.
- Overlaps with: PLAN-LB-10 (`PLAN-LB-10-retried-step-outcome.md`) — `manage-status/scripts/_cmd_mark_step.py`. Sequence.
- Overlaps with: PLAN-LB-09 (`PLAN-LB-09-pending-findings-gate.md`) — `manage-status/scripts/manage-status.py` and possibly `_cmd_lifecycle.py`. Sequence. Its pending-findings gate is also the consumer that Deliverable 4's unresolved state findings block today.
- Overlaps with: PLAN-LB-08 (`PLAN-LB-08-triage-survives-recheck.md`) — `manage-findings/scripts/_findings_core.py`. Sequence.
- Overlaps with: PLAN-LB-05 (`PLAN-LB-05-unrunnable-waits.md`) and PLAN-LB-06 (`PLAN-LB-06-triage-fix-task-loop.md`) — `plan-marshall/workflow/execution.md`; this plan changes one sentence there. Sequence or coordinate at the gate.
- Adjacent to: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — its refusal to declare `verdict_inputs` is recorded on evidence and stays; it keeps re-firing on every HEAD advance.
- Left out on purpose: process-compliance PLAN-20 D1 (naming a fixer for an inline `6-finalize` loop-back, and the per-round convergence measure) and D5 (the verifier's candidate-count contract and a file-reference form for oversized candidate envelopes).
- Left out on purpose: post-run-quality PLAN-PRQ-10 D0 and D2–D5 (corpus re-fire census, retiring `further_round_owed` as a finding, per-class detector coverage, an AsciiDoc detector, their controls), and its D1 shapes other than the `verdict_inputs` declaration. Deliverable 4 here keeps the state findings and makes them resolvable; it does not decide whether they should be findings at all.
- Left out on purpose: the shared surfacing envelope and all detector work.

From PLAN-LB-05:

- Overlaps with: PLAN-LB-09 (`branch-cleanup.md`, pre-merge check), PLAN-LB-10 (`ci_verify.py`), PLAN-LB-06 (`execution.md`), PLAN-LB-12 (`script-shared/scripts/build/*`), PLAN-LB-19 (`github_pr.py`), PLAN-LB-02 and PLAN-LB-11 (`phase-6-finalize/SKILL.md`). Each touches a different section; sequence rather than pair.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-22-finalize-loop-control.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
