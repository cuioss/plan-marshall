envelope_version=1
sender_type=plan
sender_id=rb-lb-164-build-daemon-job-log-in-project-tree
epic=live-blockers
kind=landing
created=2026-11-19T09:11:03Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-164-build-daemon-job-log-in-project-tree
epic=live-blockers
pr=#2023
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=11
review_body_findings_handled=11
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-164 — a routed job log now lives inside the submitting project's tree

Merged as `352f81a7cfe7f1c279ff7439ab65fa8bf139581e` through the merge queue after merge-group run
44490208691 passed. Ten commits on `fix/lb-164-build-daemon-job-log-in-project-tree`, plus two base
merges. All four deliverables are met as written.

## Deliverables

**D1 — the daemon writes each job's log inside the submitting project's tree.** met.
The log lives at `{project}/.plan/local/marshalld/job-logs/{job_id}.log`, the result's `log_file`
names that absolute path, `.plan/*` covers it in this repository (and in a stewarded checkout, whose
rule `marshall-steward:gitignore_setup` writes — stated as a precondition, not a guarantee), and
`{job_id}` is what keeps two jobs of one project apart.

- Done-when: `log_file` in-tree, file exists, holds the job's output — **met**, test
  `test_job_log_is_written_inside_the_submitting_project_tree`, order `test-first`: failing run at
  base `571c01087`, all five new tests failed on the in-tree assertion, and the run's own
  `log_file` was `~/.plan-marshall/marshalld/job-logs/2a3af135c5254bf4be830ada31b08b56.log` — the
  defect, measured. Commits `7a5009931`, `94ab4c21d`, `c4fcc6152`, `6d97095b1`, `3c6fc37d6`,
  `e3d57f1c0`, `be6f24683`.
- Done-when: two jobs of one project never share a log — **met**, `test_two_jobs_of_one_project_keep_separate_logs`,
  order `test-first` (same base run); the comparison is per output line, so a prefix cannot hide
  swapped attribution.

**D2 — the log's life follows the tree.** met.
Removed with the worktree (no sweep exists); `Journal.gc` unlinks only `journal/{job_id}.json`;
a read-only, missing, mis-permissioned or symlinked tree, a hard link, a FIFO, a failed mid-run write,
a failed final flush and a log that disappears under the job are all recorded as `log_file_failed`
with a reason and never fall back to a machine-global directory.

- Read-only arm — **met**, `test_unwritable_project_tree_records_a_logging_failure_without_fallback`
  and `test_run_job_that_cannot_write_its_log_fails_without_running_the_child`, order `test-first`
  for the daemon arm (base `571c01087`: the unfixed daemon reported `success` with the log outside
  the tree) and `none` for the supervisor arm, which was added while closing a self-review finding.
- Missing-tree arm — **met**, `test_missing_project_tree_records_a_logging_failure_without_being_created`,
  order `test-first`: at base `571c01087` in a detached base worktree the run failed on
  `assert "<Errno 2 … proj>" == "log_file_failed"`; output
  `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-18-191532.log` (job
  `a9cf9ec52b2c4d93bc80bdca90ba4540`). The base tree was removed cleanly (clean status, no force).
- Lifecycle arm — **met**, `test_removing_the_tree_removes_its_logs`,
  `test_journal_gc_ignores_the_in_tree_log`, order `test-first` (both failed at base on the in-tree
  assertion: the log survived the tree in the machine-global directory).

**D3 — the documents state the new location.** met (`d0d3568bf`).
`manage-build-server/SKILL.md`'s state table drops `job-logs/` and a paragraph under it names the
in-tree path; `doc/developer/build-architecture.adoc`'s diagram drops it and a paragraph states where
the log lives; the `marshalld.py` row of `machine-global-config-scope-audit.md` no longer reaches
`job-logs`. Nothing else in those files was reworded; `runbook-lane/SKILL.md` was not touched.
No test asserts doc content — the evidence is the diff and the green `quality-gate`, which runs
plugin-doctor's document checks.

**D4 — tests pin D1–D3.** met.
`test/plan-marshall/build-server/test_daemon_job_log_in_tree.py` (six tests) plus four supervisor
tests (`_open_job_log` symlink/FIFO/hard-link/existing-file and the two logging-failure legs); the
explicit-timeout suite's fabricated `log_file` now names the in-tree shape. The other nine
build-server suites are unchanged: they inject a `log_dir` for isolation and assert nothing about
the location. The four enumerated behaviours are the four tests above, all `test-first` at
`571c01087`.

Per-head runs: `c4fcc6152` — `module-tests plan-marshall` green (job `f2dd1ed4…`), unscoped
`module-tests` green (job `d6ab28d2…`), `quality-gate` green (job `af23c166…`); `4ac6ab504` —
`quality-gate` (job `e2ed364a…`) and `module-tests plan-marshall` (job `2eca9a8b…`) green;
`6d97095b1`, `3c6fc37d6`, `e3d57f1c0`, `be6f24683`, `23d157b7e` — `module-tests plan-marshall` and
`quality-gate` green, CI `verify / verify` green on `4ac6ab504`, `23d157b7e`, `e3d57f1c0` (rerun
after an environment flake) and `be6f24683` (rerun). Four bound expiries were recorded and continued
rather than re-submitted at the same bound: `verify` at `c4fcc6152` (`timeout_used_seconds: 1297`,
`explicit`) → split form, both parts green; `module-tests plan-marshall` at `4ac6ab504` (787,
`learned`) → re-run at a raised bound, green.

## Personas and skills

- D1/D2: `persona-implementer`, with `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`,
  `plan-marshall:manage-build-server` loaded as standards.
- D3: `persona-documenter`, with `plan-marshall:ref-code-quality`,
  `pm-plugin-development:plugin-architecture`.
- D4: `persona-module-tester`, with `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`,
  `pm-dev-python:pytest-testing`.
- self-review rounds: `persona-code-reviewer` (sub-agent, session `ses_e0f81e80cffe…`, two rounds).
- skills added for surface drift: none — every touched path was inside the spec's Expected Surface.

## Hypotheses

- "The daemon may write into an enrolled project under its registry wall" — **confirmed**:
  `_marshalld_verifier.py:37-56` accepts only a canonical registered root or a live linked worktree
  under a registered container, and `marshalld.py` already ran the child with `cwd=spec.project_path`.
- "The direct (non-daemon) route already writes its log in the tree" — **confirmed**:
  `_build_result.create_log_file:389-437` → `file_ops.get_build_results_dir:821-874` →
  `{plan_dir}/build-results/{scope}/{build_system}-{ts}.log`.
- "The journal's retention and GC do not depend on the log's location" — **confirmed**:
  `_marshalld_journal.py:236-258` unlinks only `journal/{job_id}.json`.

## Findings

Self-review round 1 (medium): the routed client folds a daemon `log_file_failed` into
`execution_failed` with no reason — out of the plan's write boundary, docstring over-claim removed in
`4ac6ab504`, residue below. (low) `extension-api/standards/build-execution.md:98` is now stale — out
of boundary, residue. Round 2: nothing in scope open.

Sourcery (12 + 13 inline threads across two reviews): 21 fixed across `6d97095b1`, `3c6fc37d6` and
`be6f24683` — symlinked-component and resolved-containment refusal, `O_NOFOLLOW`/`lstat` FIFO and
symlink refusal, hard-link refusal without truncation, 0600/0700 modes, canonical project path, pump
liveness and no-stall draining, timeout/kill outranking a broken log, duration/exit on post-spawn
failures, orphan-log removal, `.plan`-anchored creation, probe errors inside the logging leg, and
whole-line test assertions; 2 answered as out-of-boundary, 2 answered as spec-required (doc
duplication) or retention-scoped. Every thread was replied to and resolved.

CodeRabbit (required): 3 + 6 inline findings and 2 review-body advisories. Fixed: final-flush
`OSError` (`3c6fc37d6`), non-finish verdict preserved (`3c6fc37d6`), probe errors and `.plan`-anchored
creation, pump liveness marking, whole-line test assertions (`be6f24683`); answered: the routed-client
fold (out of boundary), the untracked-change precondition (docstring corrected), the retargeted
symlink (same-uid class, admission identity is a scheduler surface), and the two advisories (existence
check is reliability hardening, not a boundary; a descriptor-relative open would guard an actor that
already owns `.plan/local/marshalld`, recorded as a follow-up).

Every CI failure was read, not assumed: one `verify / verify` failure was the known environment flake
in `test_executor_recovery.py::test_a_cache_missing_the_module_regenerates_failed` (191 s setup), and
the re-run was green.

## Reviewers

| Reviewer | Required | History |
|---|---|---|
| coderabbit | yes | refused on quota five times between 21:55Z and 04:03Z (90-minute policy waits, one escalated trigger); reviewed `6d97095b1` with a `final_review_risk_coverage` marker (`kind=reviewed`), then `e3d57f1c0`; every finding handled; `review_complete_after_handling` on record, so no re-trigger after later heads |
| sourcery | no (optional) | refused on quota once, then reviewed `4ac6ab504`, `23d157b7e` and `e3d57f1c0`; every finding handled |

Standing review authorization: not needed — CodeRabbit produced a qualifying review and its
findings are handled, so `review-gate --required-reviewer coderabbit` reports
`merge_allowed: true` with 0 unresolved threads and 11/11 body findings disposed.

## Operator questions

none asked — no blocker, no rule needed bending, and the reviewers arrived inside the policy's loop.

## Rule check

- guard: present. The run's session `ses_e10a30defffeiSBKSdQdlw2Qe3` has **three R1 refusals** in
  `.plan/temp/guard.log`: an `ls -1 … | head` (pipe), a heredoc `python3 -` attempt, and a commit
  message containing backticks. All three were refused; none executed.
- Self-reported deviations: (1) `git clean -f -x -- <two scoped paths>` in the base worktree, used to
  remove the copied test file and the owner marker before `git worktree remove`; (2) build logs were
  read from the repository's own `.plan/local/plans/NO_PLAN/build-results/**` via the file tools —
  in-repo, and the reader the build result names; (3) no shell file reads succeeded (the one `ls`
  was refused).
- Spec read: `spec_source: ledger_worktree`; no `spec_differ` marker.
- `executor-skew`: `not_applicable` (source checkout; the executor maps the checkout's own scripts).
  Recorded, never asked.
- Sessions/restarts: one session; the self-review sub-agent was dispatched twice (rounds 1 and 2) on
  the same child session. No restarts, no killed sub-agents, no backgrounded builds — every routed
  build was held in-call and re-attached with `build_server wait`.

## Build server

Setup preflight `ready` (registered, version 1). Every build in this run was
`mechanism=daemon_longpoll` (`requested=auto`, `resolved=routed`); **no build degraded and no retry
was needed** — the client's 300 s wait expired while queued several times, which was handled by
re-attaching with `build_server wait`, not by changing the execution mode. Queues reached 1125 s
(the machine cap is 2 slots and other sessions were building). Two bound expiries: `verify` at
`c4fcc6152` (1297 s, `explicit`) and `module-tests plan-marshall` at `4ac6ab504` (787 s, `learned`);
both continued with the split form / a raised bound. No `killed` job. `runtime_stamp_reason` was not
reported.

## Residue

- The routed client folds a daemon `log_file_failed` into `execution_failed` without its reason
  (`_build_execute_factory.py` failure arm) — `script-shared` is outside this plan's surface.
- `extension-api/standards/build-execution.md:98` still says the `log_file_failed` leg states no
  reason.
- An upgrade leaves the old `~/.plan-marshall/marshalld/job-logs/` behind; nothing cleans it.
- Deferred preferences: descriptor-relative `dir_fd` opening (guards only a principal that already
  owns the 0700 log tier); a size cap on job logs (none existed before; growth policy unchanged);
  carrying admission-time canonical identity into `_execute` (scheduler/verifier surface).
