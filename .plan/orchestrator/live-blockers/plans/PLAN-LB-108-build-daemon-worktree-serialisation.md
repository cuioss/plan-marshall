# PLAN-LB-108: The build server runs one build per directory at a time, and a second build for a busy directory waits and says so

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-108-build-daemon-worktree-serialisation.md` and is queued as one row file, `queue/PLAN-LB-108.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's instruction of 2026-11-02 ("stage the corresponding plans, aggregate where sensible") from inbox
> finding `lessons-routing-069`, graded high by operator ruling in the 2026-11-02 cross-repo sweep. Its source is API-Sheriff
> lesson `2026-10-04-09-002`, seen twice: PLAN-V02-10 (PR 382) and PLAN-V02-14 (PR 387). Since PLAN-LB-104 the build server is
> the default route for every runbook-lane build, so every caller is exposed.

## Objective

The build daemon admits a job on the machine-wide slot cap alone. It never checks whether a job for the SAME directory is already
running, so two builds of one worktree run at once and write the same `target/`. Observed cases are two Maven jobs submitted
4 s apart, and module tests running beside integration tests. The result is false failures: ClassNotFoundException,
NoClassDefFoundError and "Failed to start quarkus". Serial re-runs are green.

The in-process path has the same gap. Its limiter is keyed on the plan id, and a lane build passes `--project-dir`, so it has
no plan id and skips the limiter entirely.

This plan serialises builds per project directory on both paths. A second build for a busy directory waits in a queue, and the
submit, the wait and the result say what it is waiting on. Slots are spent only across different directories.

## Deliverables

1. **The daemon admits at most one job per project directory.**
   - `Scheduler.admit_next` skips a queued job whose directory already has a running job, and admits the next eligible job
     instead. The directory key is the canonicalised `spec.project_path`: it is resolved, so two spellings of one worktree are one
     key.
     - FIFO order within one directory is kept.
     - Round-robin fairness across registered projects is kept.
     - A job blocked on its directory never holds up a job for another directory queued behind it, so there is no head-of-line
       blocking.
   - The key is the job's own directory, not the registry `canonical_root` the fairness queue uses today. The main checkout and
     each of its worktrees are separate keys.
   - Admission also skips a directory with a live in-process holder (D3), so the daemon never spends a slot on a child that would
     then wait on its directory. When that holder releases, admission runs again (see the HYPOTHESIS on the re-admission trigger).
   - Idempotent attach is unchanged: an identical submit still attaches to the job already in flight.

   *Done when:* all of the following hold.
   - A pure scheduler test with `max_slots=2` submits A (directory W1, `module-tests`), B (W1, `integration-tests`) and C (W2).
     It asserts that `admit_next` yields A and then C, never B; that B is admitted only after `complete(A)`; and that FIFO holds
     for a third W1 job. It is red at HEAD, where B is admitted second.
   - A daemon-level test through `Daemon.handle_request`, with a stub `run_job`, shows B's journal status staying `queued` while A
     runs.
   - A test with a live D3 holder on W1 shows a W1 job is not admitted until the holder releases.
   - The existing idempotent-submit and round-robin tests stay green unchanged.

2. **The wait is visible in the submit, the wait and the routed result.**
   - The submit response carries `queued_behind`: the id of the job running in the same directory, empty when there is none. It
     sits beside the existing `status`, `job_id` and `attached`.
   - While a job is not yet admitted, `wait` returns `job_status: queued` with `waiting_on` (a job id, or the identity of the
     in-process holder) and `queued_seconds`. Today it returns `running` with `elapsed` 0 for a job that has not started. Once
     the job is admitted, `wait` returns `running` as now.
   - The routed client (`_route_to_daemon`) treats `queued` as non-terminal and keeps waiting within its bound. The running
     hand-back and the terminal result carry `queued_seconds`. The result formatter's field whitelist carries the new fields on
     both the TOON and the JSON path.
   - Fields consumers read stay unchanged, each with its own check:
     - `job_status` values `running` and the four terminal ones keep their meaning;
     - `elapsed`, `last_progress` and `eta` on a running job are unchanged;
     - `job_id` on the hand-back is unchanged;
     - `attached` on submit is unchanged.
   - Edges, each with its own check:
     - no other job: `queued_behind` is empty and `queued_seconds` is 0;
     - one job ahead;
     - two jobs ahead, in FIFO order;
     - a holder that finishes within the wait bound;
     - a job still `queued` when the bound expires, which returns a hand-back, not `indeterminate`.

   *Done when:* tests show each field and each edge above. A client test feeds in a `queued` wait payload and asserts that the
   loop keeps waiting and never reaches the `indeterminate` leg for "terminal job_status this client does not recognise". That test
   is red at HEAD, or shown to be unnecessary there if HEAD never emits `queued`. The build-server-client SKILL text names `queued`
   as non-terminal.

3. **Every in-process build holds a per-directory lock, plan-less builds included.**
   - The in-process leg of `cmd_run` takes a per-directory lock (k=1) for the whole build, keyed exactly as in D1. The daemon child
     takes the same leg, so it holds the lock too. An in-process build and a routed build of one directory therefore block each
     other.
   - The lock is separate from the slot. Plan-less builds (`NO_PLAN`, which includes every `--project-dir` lane build) still take
     no slot, as now, but they DO take the lock: the hazard is the shared `target/`, not the slot budget.
   - Waiting is a queue (FIFO per directory, re-polled), never a refusal. If the wait bound runs out, the build does not run and
     the result is a named `directory_busy` error. That error names the holder: plan id or `NO_PLAN`, command, pid and seconds
     held. The build never runs concurrently and never passes silently.
   - The lock of a holder that died (its pid is gone) is reclaimed, so a crashed build cannot block a directory forever.

   *Done when:* all of the following hold.
   - A test runs two in-process builds of one tmp directory concurrently (stub tool, real lock). It asserts they do not overlap
     and that the second reports its wait. Both builds are `NO_PLAN`, so this test is red at HEAD.
   - A test with a dead-pid holder shows the lock reclaimed.
   - A test with an exhausted bound shows `directory_busy` naming the holder, and the build not spawned.
   - A cross-order test shows no deadlock under the lock order in Standing Constraints. In it, a directory holder waits on a slot
     while a slot holder wants that directory.

4. **A build-queue slot is held per build invocation, not per plan.**
   - Today `build_queue acquire` hands a second concurrent build of the same plan the EXISTING active id. Both builds then run on
     one entry, and the first release frees the slot while the second is still running. After this deliverable, the acquire
     carries a per-invocation token. A re-poll with its own token keeps its FIFO place, as now, and a second invocation of the
     same plan is a second entry.
   - Result fields stay unchanged, each with its own check: `id`, `admission`, `active_count`, `waiting_count`, `warnings` (always
     present), `max_slots` and `max_slots_source`, and the `cap_*` verdict fields.
   - Edges, each with its own check: the same plan twice at cap 1; a re-poll after promotion; release of an absent id (a no-op, as
     now); a queue entry written before the token existed.

   *Done when:* a test at cap 1 acquires twice for one plan with two tokens. It asserts that the second acquire is `blocked`, that
   re-polling with its own token keeps its position, and that releasing the first promotes the second. It is red at HEAD. The
   existing admission, FIFO, reap and cap-disagreement test files stay green.

5. **The docs describe the mechanism instead of asking agents to avoid the race.**
   - `runbook-lane/SKILL.md` § 4 "One daemon-routed build at a time per worktree, sub-agents included" is rewritten to describe
     the mechanism. A second build for a busy worktree waits, and the wait shows as `queued`, `queued_seconds` or
     `directory_busy`. Running builds in parallel in one worktree gains nothing.
   - The mechanism supersedes the prose rule. The hazard that rule names ("a result can carry its sibling job's counts") cannot
     happen once one directory runs one build at a time.
   - `manage-build-server/SKILL.md`, `manage-locks/SKILL.md` and `doc/user/parallelism-and-locking.adoc` describe the
     per-directory lock, the split between slot and lock, and the lock order.
   - Code comments saying "the daemon child holds the single machine-global slot" are corrected to state when that holds.

   *Done when:* the guard test in `test_runbook_lane.py` that pins the old sentence is updated to pin the new statement, and no doc
   or comment describes the per-plan or slot-only model as current.

Split guard: five deliverables, one invariant (one build per directory at a time). D1 and D3 enforce it at its two points, D2 and
D4 make it observable and correct at the slot layer, and D5 makes the docs true. None of them closes the defect alone.

## Standing Constraints

- **Queue, never reject.** A build for a busy directory waits and says that it waits. An error is allowed only when a wait bound
  runs out, and it names the holder.
- **Lock order everywhere: directory lock first, then slot.** No build waits for a directory while it holds a slot, and the daemon
  never spends a slot on a job whose directory is held (D1). This rules out a deadlock between the daemon's slots and the
  in-process lock.
- **The slot cap is unchanged.** The machine-global cap (`_machine_config.resolve_max_slots`, set to 2 on the operator's machine)
  and how it is resolved stay as they are. Slots are spent only across distinct directories as a consequence of D1 and D3, not
  through a new cap.
- **Leave routing alone.** Do not change the semantics of `--execution-mode`, `build-routing`, or the `--project-dir`
  absolutisation from PLAN-LB-104.
- **Shared state is written only through `_locks_core.rmw_json`.** No mutation happens outside a critical section, and no I/O
  happens inside `_mutate`.
- **Tests stay isolated and real.** Tests never read the real `~/.plan-marshall` or this repository's live `.plan/marshal.json`;
  they use the `PLAN_MARSHALL_HOME` fixture. The operator has ruled that a test reading live config is always a bug. Every new or
  changed test states what it protects. A scheduler or lock test uses the real `Scheduler` and the real lock, not a stub that
  would pass at HEAD.
- **The daemon side takes effect only after a reconcile.** D1 and D2 need the daemon reconciled to the new code, an operator step
  in `manage-build-server` after the merge and the harness sync. The PR's evidence is therefore the test suite.
  - A live record from a worktree before the merge is NOT a Done-when; PLAN-LB-104's D1 live clause failed for exactly this
    reason.
  - The landing lists the post-merge live check as owed: two builds submitted for one worktree, with the second reporting
    `queued`.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: the scheduler admits on free slots alone and pops FIFO from a project queue, with no check of what is running —
  `_marshalld_scheduler.py` L128-130 (`available_slots`) and L202-223 (`admit_next`).
- OBSERVED: the scheduler's fairness key is the registry's `canonical_root` (the main checkout), so every worktree of one
  repository shares one FIFO queue — `marshalld.py` L492 (`self._scheduler.submit(spec, outcome.record.get('canonical_root', ''))`)
  and `_marshalld_scheduler.py` L194-197.
- OBSERVED: each job carries its absolute directory and the daemon runs it there — `_build_server_protocol.py` L22-23 (JobSpec
  `project_path`), `_build_execute_factory.py` L1026 and L1051-1058 (`exec_path=exec_root, project_path=exec_root`), and
  `marshalld.py` L638-645 (`run_job(spec.command, spec.project_path, ...)`).
- OBSERVED: a submit attaches only when its fingerprint (plan id + command + tree) is identical, and a lane build is submitted as
  `NO_PLAN`. So `module-tests` and `integration-tests` from one worktree are two jobs, and both run — `_build_server_protocol.py`
  L22-25, `_marshalld_scheduler.py` L181-183, `_build_execute_factory.py` L1050.
- OBSERVED: admission runs only on a submit and on a job's completion — `marshalld.py` L495-496 (`_apply_current_cap`,
  `_admit_ready` in `_submit`) and L654 (`_admit_ready` at the end of `_execute`).
- OBSERVED: a job that is queued and not yet admitted is reported as `running` — `marshalld.py` L518-532 (`_running_status` always
  emits `STATUS_RUNNING`, with `elapsed` 0 when there is no progress), while the journal holds `queued` until admission
  (`_marshalld_journal.py` L119, `marshalld.py` L598). The submit response is only `{status: queued, job_id, attached}`
  (`marshalld.py` L497).
- OBSERVED: the routed client treats only `running` as non-terminal, and turns an unrecognised `job_status` into `indeterminate` —
  `_build_execute_factory.py` L1080-1084 and L784-793. A new `queued` wait status that bypassed the loop would land there (D2).
- OBSERVED: the in-process limiter does nothing for a routed build or for a build without a real plan id — `_build_queue_slot.py`
  L419-421. A build given only `--project-dir` resolves to `NO_PLAN` (`_build_cli.py` L60-66), so every lane build runs in-process
  with no slot and no lock. This matches the epic's recorded rule that in-process builds bypass the slot cap.
- OBSERVED: the daemon child runs the in-process leg — `_build_execute_factory.py` L1018-1019 (`in_daemon_job`), L1499-1500 and
  L1516-1517 (`with build_queue_slot(plan_id)`). The child therefore takes a slot only when it has a real `--plan-id`. The comments
  saying the daemon child "holds the single machine-global slot" (`_build_execute_factory.py` L1415-1416, `_build_queue_slot.py`
  L33-37) are true only in that case.
- OBSERVED: `build_queue acquire` is idempotent per plan. A plan that already holds an active slot gets that same id back —
  `build_queue.py` L907-914, and the waiting re-poll at L920-934. Release removes by id (L1085-1093), so two concurrent builds of
  one plan share one entry and the first release frees it.
- OBSERVED: no script keys any build exclusion on a directory. A content search for per-project or per-worktree lock, serial,
  mutex or exclusion, and for `project_path` near running, in-flight or busy, returned 0 of 502 source files with clean coverage.
  This agrees with the reads above.
- OBSERVED: the prose rule is at `runbook-lane/SKILL.md` L540-544 ("One daemon-routed build at a time per worktree, sub-agents
  included ... two routed builds from one worktree can interleave, and a result can carry its sibling job's counts"). It covers
  every build in the lane, not only self-review. No `phase-6-finalize` file carries a counterpart: searches for
  `build at a time|...|interleave` and `daemon-routed build|One daemon|sibling job` matched no file there.
- OBSERVED: PLAN-LB-104 is in HEAD — `_build_execute_factory.py` L926-982 (`_absolutise_project_dir`) and L1039-1044.
- OBSERVED: `_next_state` carries every unrecognised top-level field of `build-queue.json` forward, so a new top-level key for the
  directory lock survives other mutators — `build_queue.py` L358-381.
- HYPOTHESIS: the rule at L540-544 is the one PLAN-LB-78 D2 added. Confirm in the ledger's `landings/PLAN-LB-78.md` or with
  `git log -S "One daemon-routed build at a time"` on `runbook-lane/SKILL.md` (verify-at-outline). D5 does not depend on the
  attribution.
- HYPOTHESIS: `test_runbook_lane.py` pins the L540 wording (one content hit for the pattern). Confirm the test name before D5
  (verify-at-outline, `test/plan-marshall/runbook-lane/test_runbook_lane.py`).
- HYPOTHESIS: the reported Maven and Quarkus failures are this admission gap, with two builds writing one `target/`. This was not
  reproduced here because no Maven project was built. D1's test, red at HEAD, reproduces the admission itself (verify-at-outline;
  the build failures stay the lesson's evidence).
- HYPOTHESIS: the daemon has no timer, so the release of an in-process holder triggers no re-admission. D1 then needs a periodic
  re-admit, or a re-admit on each `wait`. Confirm at the `_admit_ready` callers in `marshalld.py` (verify-at-outline).
- HYPOTHESIS: `_locks_core.holder_is_dead` judges liveness by the plan directory, which a `NO_PLAN` holder does not have, so D3
  needs liveness by pid. Confirm at `_locks_core.py` § `holder_is_dead` (verify-at-outline).
- HYPOTHESIS: the field whitelist of the result formatter, which must carry `queued_seconds` and the fields of `directory_busy`, is
  `_build_format.EXTRA_FIELDS` (cited at `_build_execute_factory.py` L906-907). PLAN-LB-104's landing found its whitelist there and
  not in `_build_result.py` (verify-at-outline, `_build_format.py`).
- HYPOTHESIS: `run_submit` and `run_wait` in `build_server.py` pass the daemon payload through unchanged, so the new fields need no
  change to the client verbs. Confirm at `build-server-client/scripts/build_server.py` (verify-at-outline).
- HYPOTHESIS: a build-class script that does not go through `create_execute_handlers` would bypass D3.
  `build-npm/scripts/js_coverage.py` declares its own parser (`_build_cli.py` L41-46). Confirm whether it spawns a build tool
  outside `cmd_run`, and list it in the PR as covered or out of scope (verify-at-outline).
- Verify-first clause (D1): before editing, write D1's scheduler test and run it at HEAD. It must be red (B admitted beside A). If
  HEAD already serialises, the spec is wrong at its centre: loop back and re-scope.
- Verify-first clause (D3): before choosing the storage, settle whether the directory lock lives as a top-level key in
  `build-queue.json` or in a sibling file under the same home root. Either way it goes through `rmw_json`. Record the choice and
  its reason in the PR.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` — per-directory admission (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — `_submit`, `_admit_ready`, `_running_status`, re-admission trigger (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py` — `queued` wait payload fields (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `queued` as non-terminal in `_route_to_daemon`, the lock around the in-process leg, comment fixes (D2, D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_queue_slot.py` — the per-directory lock beside the slot, lock order (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_format.py` — field whitelist for `queued_seconds` / `directory_busy` (D2, D3; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/build_queue.py` — per-invocation token (D4), directory-lock state (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` — pid liveness for a plan-less holder (D3; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` — `queued` is non-terminal (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 4 L540-544 rewritten (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md` — per-directory admission (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — lock versus slot, lock order (D5)
- OBSERVED: `doc/user/parallelism-and-locking.adoc` — user-facing locking description (D5)
- OBSERVED: `test/plan-marshall/build-server/test_marshalld_scheduler.py` — D1 admission tests
- OBSERVED: `test/plan-marshall/build-server/test_build_execute_routing.py` — D2 client `queued` handling
- OBSERVED: `test/plan-marshall/build-server/test_acceptance_status_toon.py` — D2 wait payload fields
- OBSERVED: `test/plan-marshall/script-shared/test_build_queue_slot.py` — D3 lock tests
- OBSERVED: `test/plan-marshall/manage-locks/test_build_queue_admission_and_release.py` — D4 per-invocation tests
- OBSERVED: `test/plan-marshall/manage-locks/_build_queue_fixtures.py` — fixture support for D3 and D4
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — D5 guard update

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-104 (PR 1893, merge 42b421ff2) is shipped and present in HEAD.
- **Overlaps with:**
  - PLAN-LB-87 (parked) declares `_build_execute_factory.py` and the `test/plan-marshall/script-shared/` directory, which holds
    `test_build_queue_slot.py`. If PLAN-LB-87 is un-parked, run it in sequence with this plan, never concurrently.
  - PLAN-LB-23 (shipped) declared `marshalld.py` and is no longer live.
  - Within the 2026-11-02 staging: `runbook-lane/SKILL.md` and `test_runbook_lane.py` are shared with PLAN-LB-106 (a different
    section, § 7), and the gate decides the pairing.
- **Adjacent to** (left untouched):
  - `_marshalld_supervisor.py` and `_marshalld_verifier.py`: the child runs and is verified as now.
  - `_machine_config.py`: the cap and how it is resolved.
  - `runbook_lane.py`: no verb changes; the lane only reads the new result fields.
  - `extension-api/standards/build-execution.md` and `phase-5-execute/standards/canonical_verify.md`: they describe routed builds
    but state no concurrency rule. Leave them unless the outline finds a sentence that D5 makes false.
  - The post-merge daemon reconcile, an operator step in `manage-build-server`.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-108-build-daemon-worktree-serialisation.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
