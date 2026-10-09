# PLAN-LB-26: Execute loop: triage creates fix tasks that run, a triage decision survives a re-check, and long builds have one runnable wait rule

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-26-execute-loop-triage.md` and is queued as one row file, `queue/PLAN-LB-26.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-06, PLAN-LB-05, PLAN-LB-08, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

When a build fails during execute, the loop that should fix it does not close. The fix task triage is told to write is refused by the validator and, once created, is never scheduled; the documents disagree on whether the orchestrator may background the build it is waiting for; and re-running a deterministic check sets every finding it re-observes back to `pending`, erasing the triage already done. This plan makes a triage-created fix task valid, schedulable and scheduled first, stops a known failure from being triaged again, states one runnable rule for an orchestrator-tier build wait, and makes an unchanged re-emission leave a recorded resolution alone. The sources are one plan because they meet in `plan-marshall/workflow/execution.md` § "Orchestrator-tier phase-5 verification" and at the findings store.

### Carried from PLAN-LB-06: Triage can create and schedule its own fix tasks

When a build fails during execute, triage is supposed to create a fix task and the executor is
supposed to run it. Neither half works as documented: the triage document tells the agent to write
`deliverable: 0`, which the task validator refuses, and a fix task that does get created carries no
envelope number, so no envelope dispatch ever selects it. In one run a single failing test was
re-triaged once per deliverable — five triage dispatches and six 7–17-minute test runs — while the fix
task that owned it sat unrunnable. This plan makes a triage-created fix task valid, schedulable and
scheduled first, stops a known failure from being triaged again, and closes two contract gaps that
keep the loop from terminating. Carries forward process-compliance PLAN-19 deliverables D1–D5.

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

### Carried from PLAN-LB-08: Triage survives a re-run of the check that produced it

When a checker files a Q-Gate finding that is already in the store with a resolution, the store sets
it back to `pending` and erases the resolution text and timestamp. The match that triggers this is
title plus a hash of the finding's content, so it fires exactly when nothing about the finding has
changed. Re-running a deterministic check — the normal way to confirm a fix — therefore undoes every
triage decision on the findings it re-observes, re-arms the pending-findings gate, and reports
`findings_emitted: 0` while doing so. Six findings an operator had accepted were reverted this way by
one verification re-run, and a later plan was told not to re-run the check at all. This plan makes an
unchanged re-emission leave a recorded resolution alone, keeps reopening as an explicit request for
the one consumer that depends on it, and makes the re-observation visible instead of destructive.
No earlier spec covers this; the evidence is two lessons, `2026-09-02-19-001` and `2026-09-05-17-001`.

## Deliverables

1. **[PLAN-LB-06 D1]** **Triage's documented fix task is accepted.** `triage.md` § FIX says to write the task with
   `deliverable: 0` and names no `origin`; the validator defaults `origin` to `plan` and refuses
   `deliverable == 0` unless `origin == 'holistic'`, reporting "Missing required field: deliverable".
   The triager then guesses an owning deliverable. Make the documented form valid: either the triage
   document sets an origin the validator accepts with `0`, or the validator accepts `0` for the
   fix-class origins a triage writes. One rule, stated in `triage.md`, `task-contract.md` and the
   validator's error text. Done when: `commit-add` of the exact task shape `triage.md` prescribes
   succeeds; `commit-add` with the `deliverable` field absent and a plain `plan` origin still refuses;
   `batch-add`, which carries a second copy of the same check, behaves identically.

2. **[PLAN-LB-06 D2]** **A fix task created after planning is schedulable and runs first.** `commit-add` writes no
   `envelope_id`, and the executor runs only tasks whose `envelope_id` equals the envelope it was
   dispatched with, so a fix task is reachable only through an undocumented `envelope_id: null`
   dispatch. `next` also returns tasks in number order, which puts a new fix task behind every
   remaining deliverable whose build it blocks. Define one mechanism and document it in
   `execution.md` and `phase-5-execute/SKILL.md`: a task created after envelope packing is assigned
   to an envelope at creation (or the null-envelope dispatch becomes a defined, named dispatch), and
   it is ordered ahead of the pending tasks whose verification it blocks. `manage-tasks get` returns
   `envelope_id` (today only `next` does). Done when: a test creates a task through `commit-add` on a
   plan whose tasks are already packed and reads a non-null `envelope_id` back from `get` (or, under
   the alternative, the documented null-envelope dispatch selects it); a test shows `next` returning
   the fix task before the remaining pending deliverable tasks.

3. **[PLAN-LB-06 D3]** **A failure a pending fix task already owns is not triaged again.** `execution.md` routes every
   `triage_required` return and every failed orchestrator-tier build into a fresh
   `verification-feedback` dispatch, with no check for a finding identical to one a pending fix task
   was created for. Add the short-circuit: before dispatching triage, the orchestrator compares the
   pending findings with the findings already resolved "will be addressed by TASK-N" whose task is
   still not done; when every pending finding matches one, it skips the dispatch and schedules the
   fix task. State in the same place which store a build's failures land in, so the orchestrator
   does not file a further copy by hand. Done when: a deterministic verb or documented query returns
   "all owned by TASK-N" for a repeated identical failure and "new findings" when one differs, with a
   test for each; `execution.md` names the store and the short-circuit before the dispatch block.

4. **[PLAN-LB-06 D4]** **The end-of-execute re-dispatch rules agree.** In `execution.md` the orchestrator-tier table says
   a green build means "Re-dispatch phase-5-execute … the freshness gate (Step 12a) now sees the
   stamp", while the pre-dispatch queue peek in the same file says the orchestrator "MUST NOT
   re-dispatch" when `loop-exit-guard` reports no pending and no in-progress task. At the end of
   execute both apply, and Step 12a was not re-entered. Make one rule win in words: name the
   post-build re-entry as an exception to the peek, or move the freshness check to where the peek
   leads. A leaf that returns because it owes the orchestrator a build says so in a defined return
   field that every termination branch honours, instead of free text beside `budget_yield`. Done
   when: the two passages no longer contradict (a doc test pins the exception or the relocation), and
   the return-field name appears in both `execution.md`'s termination table and
   `phase-5-execute/SKILL.md`'s return contract.

5. **[PLAN-LB-06 D5]** **A module-testing task is not `done` before its test ran.** `finalize-step` closes a task `done`
   as soon as its last step is terminal, with no branch for the task's profile, so a `module_testing`
   task whose only verification is an orchestrator-tier test run reads `done` before that run starts,
   and a failure has no task to reopen. Keep such a task open until its verification build reports,
   or give the failure a defined reopen path that the orchestrator-tier `error` row uses. Done when:
   a test closes the last step of a `module_testing` task that has an orchestrator-owed verification
   and reads a non-`done` status (or, under the alternative, a test shows the documented reopen verb
   returning the task to a runnable state and `next` selecting it).

6. **[PLAN-LB-05 D4]** **One rule for long builds, and it can be followed.** `await-long-running.md` and
   `build-server-client/SKILL.md` forbid backgrounding or sleeping a build wait; `execution.md`
   § "Orchestrator-tier phase-5 verification", `ref-workflow-architecture/standards/agents.md` and
   `phase-5-execute/standards/canonical_verify.md` say the await-long-running seam is the only
   component that backgrounds a build and tell the orchestrator to use `run_in_background: true`.
   Meanwhile the build wrapper's daemon route re-issues `wait` in an unbounded in-process loop, so a
   foreground wrapper call for a build longer than the per-call ceiling cannot return in time
   whichever document is obeyed. Pick one rule and make all five documents state it: the wrapper call
   for a daemon-routed build returns within a bound below the ceiling, either with a terminal result
   or with a live `running` status and the job id, and the orchestrator re-attaches with the
   documented bounded `wait`; backgrounding is named only for the non-daemon fallback, if it is kept
   at all. Done when: a test drives the routed path with a job that outlives the bound and receives
   the `running` hand-back instead of blocking; a doc test asserts none of the five documents
   prescribes `run_in_background` for a daemon-routed build while another forbids it.

7. **[PLAN-LB-08 D1]** **An unchanged re-emission keeps the recorded resolution.** In `add_qgate_finding`, a record matched
   on (title, content discriminator) whose resolution is any non-pending value — `fixed`, `suppressed`,
   `accepted`, `taken_into_account`, `rejected` — keeps `resolution`, `resolution_detail` and
   `resolution_timestamp` exactly as they are. The identity rule does not change: content is already
   part of the key, so a finding whose detail, file or rule changed fails the match and is filed as a
   new pending record, which is the correct handling of "the content changed". The call returns a
   distinct in-store status that names the kept resolution (for example `status: resolved_kept`,
   `resolution: accepted`), and that status joins `QGATE_PERSIST_OK`. The re-observation is recorded
   on the record without touching the resolution (a last-observed timestamp and an observation
   count). Done when: a test parametrized over every member of `VALID_RESOLUTIONS` except `pending`
   (derived from the constant, not listed by hand) resolves a finding, re-adds it with identical
   arguments, and reads back the same resolution, detail and timestamp with the pending count
   unchanged; the test fails at HEAD for all five values.

8. **[PLAN-LB-08 D2]** **Reopening is an explicit request, limited to `fixed`, and keeps the history.** The self-review
   loop depends on reopening: it marks a finding `fixed` because a landed change touched the file, and
   relies on the next round's re-detection to return it to `pending` if the defect survived. Keep that
   path as an opt-in on the add call (an API parameter and a `qgate add` flag) that reopens a matched
   record only when its resolution is `fixed` — `fixed` is the one resolution that claims the defect
   is gone, so an identical re-detection contradicts it; the other four record a decision to live
   with the finding and are never reopened by a re-emission. A reopen moves the previous resolution,
   detail and timestamp into a history field instead of setting them to null. The self-review
   re-surface call passes the opt-in; no other producer does. Done when: tests show (a) `fixed` plus
   the opt-in returns `reopened` and the prior resolution is readable from the record, (b) `fixed`
   without the opt-in is kept, (c) `accepted` with the opt-in is kept; and the existing
   self-correction test passes with the opt-in supplied.

9. **[PLAN-LB-08 D3]** **A checker says what it re-observed.** `qgate-mechanical-checks` counts a persist as emitted only
   when the status is `success`, so a run that reopened six findings reported zero. After deliverable
   1 it must not go silent in the other direction either: its result reports, alongside
   `findings_emitted`, how many findings it re-observed that already carry a resolution, and how many
   of those are recorded `fixed` — a finding recorded as fixed that the check still detects is worth
   a line in the output even though the store is left alone. Apply the same reporting to every
   caller that folds the persist status into a count. Done when: a test runs the mechanical checks,
   accepts one finding and resolves another `fixed`, re-runs the checks on the unchanged plan, and
   reads `findings_emitted: 0`, a re-observed count of 2 and a still-detected-but-fixed count of 1,
   with both resolutions intact in the store.

10. **[PLAN-LB-08 D4]** **The documents describe the behaviour the store has.** `manage-findings/SKILL.md` says `qgate
   add` "deduplicates by title" and that a resolved match is "reactivated to `pending`";
   `q-gate-validation.md` repeats the title-only rule; `jsonl-format.md` has the outcome table;
   `phase-lifecycle.md` lists `reopened` among resolution values; `pre-submission-self-review.md` and
   the `resolve_qgate_findings_by_evidence` docstring say a re-detection reopens. Bring each in line
   with deliverables 1 and 2: the key is (title, content discriminator), a resolved match is kept,
   reopening needs the opt-in and applies to `fixed` only. Done when: a doc test asserts that no
   document under `marketplace/bundles/plan-marshall/skills/` states that `qgate add` reopens a
   resolved finding without naming the opt-in, and that the status values listed in
   `manage-findings/SKILL.md` equal the members of `QGATE_PERSIST_OK`.

11. **[PLAN-LB-08 D5]** **The tests that pin reopen-by-default are rewritten.** The tests listed under Claim Labels assert
   `status == 'reopened'` after a plain re-add of a resolved finding. Each becomes either a
   kept-resolution assertion or an opt-in reopen assertion, according to what it was protecting, and
   the status-partition fixture gains the new value. Done when: the manage-findings, manage-tasks and
   phase-5-execute test directories pass, and no test asserts a reopen from a call that does not pass
   the opt-in.

## Claim Labels

Carried in source order: bullets 1 to 17 from PLAN-LB-06; bullets 18 to 21 from PLAN-LB-05; bullets 22 to 38 from PLAN-LB-08.

- OBSERVED: `triage.md` prescribes "title, deliverable: 0, domain matching the finding, profile: implementation" with no `origin` — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md:191`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: triage.md:191 FIX body reads 'title, deliverable: 0, domain matching the finding, profile: implementation, description quoting the finding, steps ...' and names no origin field
- OBSERVED: the validator defaults `origin` to `plan`, coerces an absent or blank `deliverable` to `0`, and raises "Missing required field: deliverable" when `deliverable == 0 and origin_raw != 'holistic'` — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py:837`, `:881-886`; the batch path carries its own copy at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py:436`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _tasks_core.py:837 defaults origin to 'plan'; :881-886 coerce None/blank deliverable to 0 and raise 'Missing required field: deliverable' unless origin is holistic; _tasks_crud.py:436 batch copy
- OBSERVED: the contract documents "`0` only valid when `origin == "holistic"`" and the origin set `plan, fix, sonar, pr, lint, security, documentation, holistic` — `marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md:502`, `:528`, `:531`; the mechanical checker already treats `deliverable=0` as the holistic sentinel at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:261`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: task-contract.md:502 '0 only for holistic origin', :528 '0 only valid when origin == "holistic"', :531 lists the eight origins; _cmd_qgate_mechanical.py:261-263 skips deliverable==0 as holistic sentinel
- OBSERVED: `commit-add` builds the task record without an `envelope_id` key — `cmd_commit_add` at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py:261-275`; an `update --envelope-id` path exists at `_tasks_crud.py:734-737`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _tasks_crud.py cmd_commit_add task dict at :261-275 has no envelope_id (nor cost_size/predicted_cost_tokens); cmd_update sets task['envelope_id'] from --envelope-id at :734-737
- OBSERVED: `get` (`cmd_read`) returns no `envelope_id`; `next` does — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py:117-136`, `:271`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _tasks_query.py cmd_read return dict :117-136 carries no envelope_id; cmd_next result has 'envelope_id': next_task.get('envelope_id') at :271
- OBSERVED: the executor "runs only tasks whose `envelope_id` equals `{E}`", and a `budget_yield` is handled by incrementing the envelope number — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:171`, `:178`, `:357`; no passage describes a task with a null envelope
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: execution.md:171 'runs only tasks whose envelope_id equals {E}', :178 packer text, :357 forwards envelope_id {E+1} on budget_yield; inventory search for null/absent/missing envelope does not hit execution.md
- OBSERVED: `next` returns the first in-progress task, else the first pending task in file order whose `depends_on` are done; nothing orders a later-numbered fix task first — `cmd_next` at `_tasks_query.py:159-203`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _tasks_query.py cmd_next :159-203 returns first in_progress task, else first pending task in get_all_tasks order whose depends_on are all done; no origin- or number-based reordering
- OBSERVED: `execution.md` § "Verification-feedback triage" dispatches `verification-feedback` on every `triage_required` return and § "Orchestrator-tier phase-5 verification" routes every build `error` into the same triage; neither has a known-failure check — `execution.md:287-330`, `:379`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: execution.md:287-332 dispatches verification-feedback on triage_required; :379 routes build status error into the same triage; neither section contains a known-failure check
- OBSERVED: the two re-dispatch rules — "Re-dispatch phase-5-execute … Step 12a" at `execution.md:378` and "MUST NOT re-dispatch the execution-context" on `pending_count: 0` and `in_progress_count: 0` at `execution.md:258`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: execution.md:378 success row 'Re-dispatch phase-5-execute ... Step 12a'; :258 'MUST NOT re-dispatch the execution-context' on pending_count 0 AND in_progress_count 0
- OBSERVED: `finalize-step` sets `task['status']` to `done` (or `failed`) when every step is terminal, with no profile branch; the file contains no reference to `module_testing` — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py:100-115`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_step.py cmd_finalize_step :100-115 sets task status to 'failed' if has_failed else 'done' when all steps terminal, no profile branch; whole file read, no module_testing reference
- OBSERVED: no file under `marketplace/bundles/plan-marshall/skills/` contains `orchestrator_build_owed`; the name comes from a run report and is not a defined field at HEAD
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: architecture search --content --literal orchestrator_build_owed over 3496 inventoried files returned count 0, unreadable 0, truncated false
- HYPOTHESIS: a daemon-routed failing build persists each failing test as a finding twice (once by the inner wrapper, once by the outer one re-storing the inner run's `routed_errors`), and the plan-scoped store appends without de-duplication — confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` § `cmd_run_common` (the `routed_errors` branch and the `_store_build_findings` call) and `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § `add_finding` (verify-at-outline)
- HYPOTHESIS: `verification-feedback.md` creates fix tasks only through `triage.md` § FIX and has no second task-creation recipe — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` (a search for `prepare-add`, `commit-add` and `deliverable` in that file returned nothing) (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: verification-feedback.md read in full: Steps 3-6 delegate FIX/SUPPRESS/ACCEPT to triage.md as single source of truth; no prepare-add, commit-add or deliverable text (content search confirms no hit)
- HYPOTHESIS: fix tasks created after packing also lack `cost_size` and `predicted_cost_tokens`, which the packer needs to place them — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py` and the fields `cmd_commit_add` writes (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _tasks_crud.py cmd_commit_add writes no cost_size/predicted_cost_tokens; _tasks_envelope.py _task_cost raises ValueError 'task is missing required field: predicted_cost_tokens'
- Verify-first clause: before scoping deliverable 2, decide between "assign an envelope at creation" and "define the null-envelope dispatch". The first needs a rule for which envelope (the current one, or a new trailing one with the manifest's `envelope_count` updated); the second needs the leaf's "is the next task in my envelope" equality check to treat null explicitly. Read `phase-5-execute/SKILL.md` § "Deterministic exit clause (envelope-group read)" and the manifest's `envelope_count` writer first; do not implement both.
- Verify-first clause: before scoping deliverable 3, establish how a triaged finding names its fix task. Today the link is free text in `resolution_detail` ("Will be addressed by TASK-{N}", `triage.md:203`). If the short-circuit would have to parse that text, add a structured task reference on the resolve call instead and match on it.
- Verify-first clause: for deliverable 5, list which task profiles can have an orchestrator-owed verification at close time before choosing between "stay open" and "reopen path"; a rule keyed on the literal profile name `module_testing` alone must be justified against that list.
- OBSERVED: the build-wait documents contradict each other — "The build consumer does NOT use this detach-and-notify seam" and "Do NOT `run_in_background` or `sleep` the daemon `wait`" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md:13`, `:28` and `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md:31`, against "background (`run_in_background: true`)" and "the orchestrator's `await-long-running` seam always does" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:370-373`, `:386`, `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md:170-172` and `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md:86`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: await-long-running.md:13,28 and build-server-client/SKILL.md:31 forbid backgrounding the build wait; execution.md:370-373,386, agents.md:170-172, canonical_verify.md:86 prescribe run_in_background via the seam
- OBSERVED: the wrapper's daemon route re-issues `wait` in `while True` until the job is no longer `running`, with no bound on the wrapper call itself — `_route_to_daemon` at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:788-796`; the client-side `wait` verb is bounded (`--bound`, default 300 s) per `build-server-client/SKILL.md:56-68`, `:189-193`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py _route_to_daemon :788-796 loops 'while True' re-issuing run_wait(bound=None) while job_status is running, no outer bound; build-server-client/SKILL.md:56-57,193 give --bound default 300s
- HYPOTHESIS: orchestrator-tier builds in this repository resolve to budgets above the 600 s per-call ceiling (745–3095 s reported), so the foreground wrapper call is backgrounded by the harness whatever the documents say — confirm/refute with `architecture resolve --command verify` and `module-tests` in the plan's worktree, reading `bash_timeout_seconds` (verify-at-outline)
- Verify-first clause: for deliverable 4, establish what a re-attached `wait` returns compared with the wrapper's own result (result TOON, findings persistence, the `kind=build` ledger stamp the freshness gate reads). If the hand-back cannot carry those, the plan narrows deliverable 4 to making the five documents agree on the rule that is actually runnable today and records the script change as owed.
- OBSERVED: the Q-Gate dedup key is the pair (title, `content_discriminator`), where the discriminator is a hash over `detail`, `file_path` and `rule`; the match is scoped to one phase's store file — `_content_discriminator` and `_find_by_title_and_discriminator` at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:150-164`, `:989-1004`, `:1061-1064`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _findings_core.py _content_discriminator :150-164 hashes detail/file_path/rule; _find_by_title_and_discriminator :989-1004 matches both; :1061-1064 scope the lookup to _store_qgate_path(store, phase)
- OBSERVED: on a match whose resolution is `pending` the call returns `deduplicated` and changes nothing; on a match with ANY other resolution it writes `resolution: 'pending'`, `resolution_detail: None`, `resolution_timestamp: None`, overwrites `iteration` when one is supplied, and returns `reopened` — `_findings_core.py:1065-1090`. The branch tests only `== 'pending'`, so all five other members of `VALID_RESOLUTIONS` (`fixed`, `suppressed`, `accepted`, `taken_into_account`, `rejected`, `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:145-159`) are reset alike, and nothing of the previous resolution is retained
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _findings_core.py:1065-1090 returns deduplicated on pending, else resets resolution/resolution_detail/resolution_timestamp, sets iteration if given, returns reopened; constants.py:145-159 lists the six resolutions
- OBSERVED: a re-emission whose detail, file or rule differs does not reach that branch; it is appended as a new pending record and the resolved one is untouched — `_findings_core.py:1064`, `:1092-1124`, and the test `test_qgate_same_class_different_subject_not_reopened` at `test/plan-marshall/manage-findings/test_manage_findings.py:224`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _findings_core.py:1064 match needs title AND discriminator, non-match falls to :1092-1124 fresh pending append; test_manage_findings.py:224 test_qgate_same_class_different_subject_not_reopened asserts it
- OBSERVED: the plan-scoped store has no such path — `add_finding` always appends a new pending record with a fresh `hash_id` and never reads existing records — `_findings_core.py:479-572`. A re-run of a plan-scoped producer therefore cannot reset a resolution; it can add a duplicate pending record beside the triaged one
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _findings_core.py add_finding :479-572 generates a fresh hash_id, builds a pending record and append_jsonl's it; no read of existing records and no dedup or reopen path
- OBSERVED: `qgate-mechanical-checks` returns `1 if status == 'success' else 0` per finding, so a `reopened` persist is counted as nothing emitted — `_emit_finding` at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:104-141`; it supplies no `rule` and `iteration=None`, so its identity is title, detail and file path
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_qgate_mechanical.py _emit_finding :104-141 ends 'return 1 if status == "success" else 0'; the add_qgate_finding call passes iteration=None and no rule argument
- OBSERVED: the reported incident — six `declared_scope_reconciliation` findings resolved `accepted` at the review gate in phase `4-plan` were reverted to `pending` by a verification re-run of `qgate-mechanical-checks`, and a later plan was instructed not to re-run the check after resolving — lessons `2026-09-02-19-001` and `2026-09-05-17-001`, read at `.plan/orchestrator/truthful-signals/lessons/` in the orchestrator ledger (both ids are absent from the global lessons store)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: Both lessons read under _orchestrator/.plan/archived-orchestrators/truthful-signals/lessons/ (epic now archived); content matches the claim; manage-lessons get returns not_found for both ids
- OBSERVED: the self-review loop relies on reopening a `fixed` record — "the re-surface below re-detects the defect and `add_qgate_finding` REOPENS the record to `pending`" at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:155`, the same statement in the docstring of `resolve_qgate_findings_by_evidence` at `_findings_core.py:1262-1266`, and the re-surface `qgate add` call at `pre-submission-self-review.md:608-613`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:155 'add_qgate_finding REOPENS the record to pending'; same statement in resolve_qgate_findings_by_evidence docstring _findings_core.py:1262-1266; qgate add call at :612-618
- OBSERVED: no script branches on the literal `reopened` or `deduplicated`; the only occurrences in `marketplace/bundles/**/*.py` are the two return sites and the `QGATE_PERSIST_OK` definition — `_findings_core.py:91`, `:1068`, `:1086`. Callers test set membership
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: Search for quoted 'reopened'/'deduplicated' over 456 script files hits only _findings_core.py (4 matches: QGATE_PERSIST_OK at :91, returns at :1068 and :1086); unquoted prose uses exist elsewhere
- OBSERVED: thirteen script files reference `add_qgate_finding`, `add_qgate_finding_checked` or `qgate add` — `manage-status/scripts/_cmd_classification_validate.py`, `plan-doctor/scripts/plan_doctor.py`, `workflow-integration-sonar/scripts/sonar.py`, `plan-marshall/scripts/_invariants.py`, `phase-5-execute/scripts/scope_creep_check.py`, `workflow-integration-gitlab/scripts/gitlab_pr.py`, `script-shared/scripts/build/_build_shared.py`, `manage-findings/scripts/_findings_store_state.py`, `_findings_core.py`, `manage-findings.py`, `manage-tasks/scripts/_cmd_qgate_mechanical.py`, `workflow-integration-github/scripts/github_pr.py`, `workflow-integration-git/scripts/_cmd_baseline_reconcile.py` (one file-name search at HEAD; some are mentions rather than calls)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: architecture search for add_qgate_finding|qgate add returns exactly the thirteen named script files under marketplace/bundles (source category), no more and no fewer
- OBSERVED: documents that state the old or a stale rule — "deduplicates by title … returns `status: reopened` (reactivated to `pending`)" at `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:223-226`; "Same title + resolved → `status: reopened`" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md:815-817`; the outcome table at `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md:262-270`; `reopened` listed as a resolution value at `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md:68`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-findings/SKILL.md:223-226 and q-gate-validation.md:815-817 state title-only dedup with reopened; jsonl-format.md:262-270 outcome table; phase-lifecycle.md:68 lists deduplicated, reopened as resolution values
- OBSERVED: tests that assert reopen from a plain re-add — `test/plan-marshall/manage-findings/test_findings_store_resolve.py:133-160` (resolved `fixed`), `:311-339` (evidence-resolved, the self-correction test); `test/plan-marshall/manage-findings/test_manage_findings_qgate.py:180-221`; `test/plan-marshall/manage-findings/test_findings_store_add.py:323`; the status-partition fixture at `test/plan-marshall/manage-findings/_findings_store_fixtures.py:80-95` with its consumer at `test_findings_store_resolve.py:438-460`; the `benign_status` parametrization at `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:315`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: test_findings_store_resolve.py:133-160, :311-339, :432-461; test_manage_findings_qgate.py:180-226; test_findings_store_add.py:323; _findings_store_fixtures.py:75-97; test_scope_creep_check.py:315 assert reopen as cited
- HYPOTHESIS: a non-zero pending Q-Gate count blocks phase boundaries, so a reopen re-arms a gate an operator had cleared — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `_capture_pending_findings_blocking_count` and the boundary table near line 1851 (verify-at-outline)
- HYPOTHESIS: the mechanical checks produce byte-identical title and detail for an unchanged plan, so a re-run matches the existing records instead of minting new ones — confirm/refute by running `qgate-mechanical-checks` twice on a fixture plan and comparing record counts; the incident (records reverted, not duplicated) points this way (verify-at-outline)
- HYPOTHESIS: some producers put volatile text into the title or detail (a line number, a count, a cohort size, a command string), so their re-emissions never match and each re-run adds a fresh pending record beside the resolved one — confirm/refute per producer in the thirteen files above; the self-review test title `defect at src/c.py:5` suggests at least one does (verify-at-outline)
- Verify-first clause: derive the caller population before changing the status set. For every call site of `add_qgate_finding` and `add_qgate_finding_checked`, and every workflow document that reads the `status` of `qgate add`, record whether it only tests in-store membership or also turns the status into a count or a branch. Deliverable 3 applies to the second group; a caller missed here will read the new status as "nothing happened".
- Verify-first clause: confirm that the self-review re-surface is the only consumer that needs a reopen. Search the workflow documents for instructions that depend on a resolved Q-Gate finding returning to `pending` on re-detection. If another consumer exists, it gets the opt-in explicitly; the default does not change back.
- Verify-first clause: decide with the operator whether `fixed` is kept by default (this spec's choice, matching the lessons' directive) or always reopened non-destructively. The case for keeping it: triage records `fixed` when it allocates the fix task, before the fix lands, so a check re-run in between would reopen the finding and a second triage would allocate a second task. The cost: outside self-review, a fix that did not work is reported by deliverable 3's count rather than by a pending finding.
- HYPOTHESIS: recurrence, folded in on 2026-10-08 from inbox message `lb-22-finalize-loop-control-005.md`: three separate triage runs in plan `lb-22-finalize-loop-control` hit "Missing required field: deliverable" on the `deliverable: 0` that `triage.md` prescribes, and each picked a real deliverable by its own rule (the one whose commit introduced the line; the one owning the file; the same as earlier fix tasks). Reported by that plan's retrospective, not reproduced here. It adds one consideration for PLAN-LB-06 D1: the deliverable number decides which per-deliverable commit and change-ledger entry a fix lands in, so the rule chosen there must be one every triage run reaches the same way — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` § the `deliverable` validation (verify-at-outline)
- HYPOTHESIS: second recurrence, folded in on 2026-10-09 from inbox message `lb-23-verify-builds-006.md`: four triage dispatches in plan `lb-23-verify-builds` hit the same "Missing required field: deliverable" and each chose a deliverable by its own judgement (seven fix tasks carry deliverables 1, 2, 5, 3, 4, 5, 5). The same dispatches show the PLAN-LB-06 D2 defect live: the fix tasks were created with `envelope_id: null`, and `manage-tasks next` handed out a queued plan task ahead of the fix task three times (TASK-7 before TASK-17, TASK-9 before TASK-18, TASK-11 before TASK-19); the leaves reordered by hand. Reported by that plan's retrospective, not reproduced here. It adds a done-condition to weigh for PLAN-LB-06 D1: a test that a fix task composed exactly as `triage.md` documents passes `commit-add` — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` § `cmd_next` (verify-at-outline)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — § FIX task shape (D1), structured task reference on resolve (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` — `deliverable: 0` rule (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` — batch copy of the rule (D1), `commit-add` envelope assignment (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — `get` returns `envelope_id`, `next` ordering (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py` — task auto-close (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md` — `deliverable` and `origin` rows (D1), `envelope_id` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — verb reference for `get`, `commit-add`, `finalize-step` (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — envelope dispatch, triage short-circuit, re-dispatch rules, termination table (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — envelope-group read and return contract (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` — triage return fields the short-circuit reads (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py` — only if deliverable 2 assigns envelopes through the packer (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — only if deliverable 3 adds a structured task reference to the resolve call (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_add.py` — `deliverable: 0` and envelope-at-creation tests (D1, D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_get.py` — `envelope_id` on `get` (D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_next.py` — fix-task ordering (D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_finalize_step.py` — auto-close rule (D5)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_batch_add_batch.py` — batch copy of the rule (D1)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py` — envelope and re-dispatch wording (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` — build-consumer rule (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — § "Orchestrator-tier phase-5 verification" (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` — § "Leaf cannot reap a backgrounded build" (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — `execution_tier=orchestrator` bullet (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` — wait rule and re-attach contract (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `_route_to_daemon` bounded hand-back, only if the verify-first clause on deliverable 4 allows the script change (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/script-shared/test_build_execute_factory.py` — routed hand-back test, same condition as the factory entry (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — `add_qgate_finding` match branch, `QGATE_PERSIST_OK`, `add_qgate_finding_checked`, the `resolve_qgate_findings_by_evidence` docstring (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — `qgate add` opt-in flag and result fields (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py` — re-observed counts in the result (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — deduplication paragraph and `qgate add` reference (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — outcome table and record fields (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — Step 6 note (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md` — resolution-value line (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — the evidence-resolution paragraph and the re-surface `qgate add` call only (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — `qgate-mechanical-checks` result fields (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — only if the caller census puts it in the counting group (D3) (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_resolve.py` — reopen, self-correction and partition tests (D1, D2, D5)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_qgate.py` — CLI reopen test (D2, D5)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_add.py` — checked-add reopen test (D5)
- OBSERVED: `test/plan-marshall/manage-findings/_findings_store_fixtures.py` — status-partition fixture (D5)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_qgate_mechanical.py` — re-run regression (D3)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_scope_creep_check.py` — `benign_status` parametrization (D5)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_qgate_resolution_survives_reemission.py` — new parametrized test for D1 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Suggested order inside the plan: the PLAN-LB-06 deliverables and PLAN-LB-05 D4 together, because both rewrite `execution.md` § "Orchestrator-tier phase-5 verification" (one how the build is waited for, the other what happens after it reports); then the PLAN-LB-08 deliverables.
- The document assertion for PLAN-LB-05 D4 goes into a test module of this plan's own, not into `test_no_standalone_sleep_in_wait_docs.py`, which belongs to PLAN-LB-25.
- Overlaps with: PLAN-LB-22 and PLAN-LB-27 on `plan-marshall/workflow/execution.md`; PLAN-LB-27 on `phase-5-execute/SKILL.md` and on `test/plan-marshall/phase-5-execute/test_scope_creep_check.py`; PLAN-LB-24 on `plan-marshall/workflow/triage.md`; PLAN-LB-22 on `manage-findings/scripts/_findings_core.py`; PLAN-LB-22 and PLAN-LB-28 on `phase-6-finalize/workflow/pre-submission-self-review.md` (this plan edits the evidence-resolution paragraph and one call); PLAN-LB-23 on `manage-tasks/SKILL.md`. Sequence against those five.
- May run together with: PLAN-LB-25, and with PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-06:

- Depends on: none.
- Overlaps with: PLAN-LB-05 (`execution.md` § "Orchestrator-tier phase-5 verification" — that plan rewrites how the build is waited for, this plan rewrites what happens after it reports; sequence, and whichever lands second re-reads the section), PLAN-LB-07 (`phase-5-execute/SKILL.md`, a different step), PLAN-LB-01 (the freshness gate Step 12a reaches; this plan only keeps it reachable and changes nothing in `_freshness_crosscheck.py`), PLAN-LB-08 (`_findings_core.py`, only if deliverable 3 adds a field to the resolve call).
- Adjacent to: PLAN-LB-08. Deliverable 3 stops a repeated failure from being triaged again; PLAN-LB-08 stops a re-emitted finding from losing its resolution. They meet at the findings store but change different functions.
- Left out on purpose: the envelope packer placing a task behind a `depends_on` edge into a later envelope, and its blindness to orchestrator-tier build yields when counting dispatches; the `phase-6-finalize/SKILL.md` item 7b wording that re-loads `phase-5-execute` inline while that skill describes itself as dispatched; removing the double persistence of build findings at its source (deliverable 3 only states which store holds them). Each is a real defect from the same runs and none blocks the triage loop once deliverables 1–3 land.

From PLAN-LB-05:

- Overlaps with: PLAN-LB-09 (`branch-cleanup.md`, pre-merge check), PLAN-LB-10 (`ci_verify.py`), PLAN-LB-06 (`execution.md`), PLAN-LB-12 (`script-shared/scripts/build/*`), PLAN-LB-19 (`github_pr.py`), PLAN-LB-02 and PLAN-LB-11 (`phase-6-finalize/SKILL.md`). Each touches a different section; sequence rather than pair.
- Left out on purpose: reaping the build when a daemon wait times out, per-test time budgets, and the adaptive build budget (truthful-signals PLAN-TRUTH-169 D1–D4; the build half is PLAN-LB-12's subject); the argparse-hint and documented-invocation deliverables of PLAN-TRUTH-162 (D0–D2, D4).

From PLAN-LB-08:

- Depends on: none.
- Overlaps with: PLAN-LB-02 (`pre-submission-self-review.md` — that plan reworks the round loop; this one edits the evidence-resolution paragraph and one call. Sequence the two, and whichever lands second re-reads the reopen wording), PLAN-LB-07 (`scope_creep_check.py` and its test — the guard re-emits an unchanged finding on every task, so after this plan an accepted scope-creep finding stays accepted; PLAN-LB-07 rewrites the same test file, so do not run them together), PLAN-LB-06 (`_findings_core.py`, only if that plan adds a task reference to the resolve call), PLAN-LB-09 (reads the pending count this plan stops re-arming; no shared file expected).
- Adjacent to: the self-review step marking a finding `fixed` because a change from the base branch touched its file. That is the evidence rule in `resolve_qgate_findings_by_evidence`, which this plan leaves as it is apart from its docstring.
- Left out on purpose: de-duplication in the plan-scoped store (`add_finding` appends a new pending record on every re-emission, so a build re-run duplicates a triaged failure) — a different function with a different remedy, partly addressed from the workflow side by PLAN-LB-06 deliverable 3; and re-keying producers whose titles or details are volatile — the third hypothesis above measures the problem, and a fix belongs to each producer.

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
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-26-execute-loop-triage.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
