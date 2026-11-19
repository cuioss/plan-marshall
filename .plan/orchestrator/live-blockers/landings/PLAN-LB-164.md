# Landing Analysis: PLAN-LB-164 — A daemon-routed build writes its job log inside the submitting project's tree

epic: live-blockers
workstream: WS-02
pr: #2023 (https://github.com/cuioss/plan-marshall/pull/2023)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-164-build-daemon-job-log-in-project-tree-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

PR #2023 `merged` through the CI abstraction; merge commit `352f81a7cfe7f1c279ff7439ab65fa8bf139581e` (squash, parent `46d3308ea`), on `origin/main`, read with git. The diff is eight files, 792 insertions and 46 deletions: `doc/developer/build-architecture.adoc`, `manage-build-server/SKILL.md`, `_marshalld_supervisor.py`, `marshalld.py`, `manage-locks/standards/machine-global-config-scope-audit.md`, the new `test_daemon_job_log_in_tree.py`, `test_explicit_timeout_routing.py` and `test_marshalld_supervisor.py` (diff stat, re-read).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the daemon writes each job's log inside the submitting project's tree; `log_file` names it; two jobs never share a log; gitignore-covered | shipped-as-specified | re-read: `marshalld.py:767-769` derives `{root}/.plan/local/marshalld/job-logs/{job_id}.log` from `canonicalize_root(spec.project_path)`; `.gitignore:45` is `.plan/*`, which covers it. The sink is opened before the child is spawned (`_marshalld_supervisor.py:599-611`, re-read). Job-id uniqueness (uuid ids, one job per directory) is the leaf's reading. |
| D2 — the log's life follows the tree; a log that cannot be written is a recorded failure, never a fall-back | shipped-as-specified | re-read: every failure leg of `_prepare_job_log` (`marshalld.py:773-828`) raises `JobLogUnavailable` and none names another directory; the supervisor's open failure returns `log_file_failure_payload` (`:599-606`). `Journal.gc` untouched and location-independent (leaf reading of `_marshalld_journal.py:236-258`, not re-read). |
| D3 — the three documents state the new location; `runbook-lane/SKILL.md` untouched | shipped-as-specified | the diff stat lists the three documents and not `runbook-lane/SKILL.md` (re-read); the wording is the leaf's reading. No test asserts document content. |
| D4 — tests pin D1 to D3, written against the unfixed tree first | shipped-modified | the new module holds SEVEN test functions (`test_daemon_job_log_in_tree.py:124,149,178,196,215,238,263`, re-read); the landing says "six tests" and its PR table says "5 new tests failed", so the counts disagree with each other and with the file. Which tests fail at base `571c01087` is the lane's claim: the squash keeps no intermediate commit, so a reading cannot settle it. |

**Surface delta** (declared 6 entries, realized 8 files): every realized file is inside a declared entry (the directory entry `test/plan-marshall/build-server/` covers the three test files). Declared and untouched: none. Realized and undeclared: none. The spec is shipped, so no correction is owed to it; no staged spec (PLAN-LB-165, 167, 168, 169) declares any of these paths.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`). The orchestrator re-read the points marked "re-read" at their lines; every other point is the leaf's reading and is an unverified lead. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with another's. The leaf reported four rule slips of its own, all read-class: one `git grep`, two argparse rejections on invented flags of `architecture search`, and read-only executor calls that may append the executor's own script log. My brief also overstated one claim (it said the mid-run, flush and vanished-log legs exit `-1`; the code passes the child's own exit code there, and the landing never claimed `-1` for them), which the leaf corrected.
- **Verdict:** layer 1 confirms; layer 2 findings (two minor); layer 3 findings (six minor, no blocker or major); not shown by reading on layers 1 and 2.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The base premise holds: the removed lines were `job_log_dir()` returning `daemon_dir()/'job-logs'` and `ensure_daemon_dir()` creating it | checked (leaf reading of the diff, not re-read) | confirms | `marshalld.py:137` |
| L1-2 | The Done-when "gitignore-covered" holds with no plan change | checked (re-read) | confirms | `.gitignore:45` (`.plan/*`) |
| L1-3 | The hypothesis "journal retention and GC do not depend on the log's location" holds | checked (leaf reading) | confirms | `_marshalld_journal.py:256` |
| L1-4 | The runbook-lane premise text and the hypothesis "the direct route already writes its log in the tree" | not_shown_by_reading | none | the leaf did not read `runbook-lane/SKILL.md` or `tools-file-ops` `get_build_results_dir`; the landing's own evidence names a main-checkout path for a run from a detached worktree, so "in the tree" may mean the main tree |

**Layer 1 verdict:** sound; not shown by reading — 1 (L1-4)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `marshalld.py:767-769`; `_marshalld_supervisor.py:599-611` (re-read) | `test_job_log_is_written_inside_the_submitting_project_tree` (in-tree, existing, own output, 0600) and the whole-line separate-logs test can fail (leaf reading) | none | checked |
| D2 | `_prepare_job_log` `marshalld.py:773-828` (re-read) | the read-only and missing-tree tests assert `log_file_failed` and no machine-global write (leaf reading) | the injected-`log_dir` exemption is unreachable in production: `build_daemon` passes none and the run parser has only `--foreground` (leaf reading) | checked |
| D3 | the three documents | no test asserts their text | `SKILL.md:102` "All daemon state lives under the machine-global home root" now precedes its exception (leaf reading, landing self-acknowledged) | checked (minor) |
| D4 | the new module and the supervisor tests | the test-first order and every green run | the landing's test counts disagree with the file (seven, re-read); about six added guard branches have no test that reaches them: the mid-run pump failure, the final-flush failure `:643-647`, the exit-0 vanished log `:672-681`, the orphan-log unlink `:619-625`, the "holds no `.plan`" refusal `marshalld.py:787-790` and the post-create resolve check `:822-828` (the branches are re-read; that no test reaches them is the leaf's reading) | checked (minor); the order is not_shown_by_reading |
| the lane's narrative | "Four bound expiries were recorded" (D4 section) against "Two bound expiries" (Build server section) | — | the message contradicts itself; only two are listed | not borne out |

**Layer 2 verdict:** findings — 2 (minor); not shown by reading — 1 (the test-first order and the green runs)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `marshalld.py:811-813`; `_marshalld_supervisor.py:403` (re-read) | a later change to `_JOB_LOG_SUBDIR` | the per-component `mkdir` loop hard-codes `('local','marshalld','job-logs')` while the target directory comes from the constant, so the loop creates the old path, `directory.stat()` at `:818` raises, and every routed job fails as `log_file_failed` | minor |
| L3-2 | `marshalld.py:795-805`, `:819`, `:822-828`; `_marshalld_supervisor.py:520-523` (re-read, the open at `:520` leaf reading) | a concurrent writer of the tree swaps a component for a symlink after the probe | the probe, the symlink-following `os.chmod` and the resolve check are separate steps and only the last component is opened `O_NOFOLLOW`, so the log can land outside the tree, or an outside directory can be chmod'ed; reachable only by a same-user writer, and the landing names the descriptor-relative open as its deferred preference | minor |
| L3-3 | `marshalld.py:814-815` (re-read) | another process creates a component between `exists()` and `mkdir()` | `FileExistsError` becomes `JobLogUnavailable` and the job fails as `log_file_failed`; narrow window | minor |
| L3-4 | `marshalld.py:815`, `:818-819` (re-read); the umask at `:251` (leaf reading) | `run --foreground`, which inherits the umask | `anchor.mkdir()` takes the default mode and only the leaf `job-logs` is tightened to 0700, so the parents can be 0755 while the docstring says the directories are 0700; the file (0600) and the leaf still protect content | minor |
| L3-5 | `_marshalld_supervisor.py:610-625` (re-read) | a cancellation of the job task, or a non-`OSError` from the spawn | the sink is released only on `OSError`, so the descriptor leaks and an empty log stays behind; the landing records this as a preference it did not take | minor |
| L3-6 | `_marshalld_supervisor.py:672` (re-read) | a non-zero-exit job whose log vanished | the check covers `status == 'success'` only, so a failed job whose log vanished is reported `build_failed` with a `log_file` that no longer exists | minor |
| L3-7 | `manage-build-server/SKILL.md:121` (leaf reading) | jobs routed for the main checkout | the log is removed "with the worktree" only; a main-checkout project keeps one `{uuid}.log` per job with no sweep and no size cap; the spec accepts it and the landing lists the cap as deferred | minor |
| L3-8 | `_marshalld_supervisor.py:643-647` (leaf reading) | an `OSError` from `proc.wait()` | the `except OSError` meant for the close-time flush wraps the wait block, so it is relabelled a logging flush failure; the timeout outcome is still reported as `timeout` | info |

**Layer 3 not shown by reading:** the end-to-end behaviour of a routed build under load (queue, pump, kill), the routed client's folding of `log_file_failed` into `execution_failed` without its reason (`script-shared/.../_build_execute_factory.py` was not read; the landing's own residue), and whether any reader outside the inventory (`.claude/**`, `.github/**` lie outside the content sweep) still reads the removed machine-global directory.

**Layer 3 verdict:** findings — 8 (7 minor, 1 info), no blocker and no major; not shown by reading — 3

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| ref-code-quality | nesting depth at most 3, complexity under 15, one responsibility per method | deviates | `_prepare_job_log` (`marshalld.py:734-829`) mixes four concerns with about 16 decision points and a four-level nest at `:770-799` (leaf reading; the span re-read in part) |
| ref-code-quality | method length hard limit 100 lines | deviates | `run_job` spans about 180 lines and grew by about 65 in this diff (leaf reading) |
| ref-code-quality | one constant, one place | deviates | L3-1 |
| ref-code-quality / python-core | release resources on every exit path; context managers | deviates | L3-5 |
| ref-code-quality | fail-closed error handling, no silent fall-back | conforms | no branch of `_prepare_job_log` names an alternate directory (re-read) |
| ref-code-quality | every added guard branch reached by a test | deviates | Layer 2, D4 |
| python-core | specific exceptions, chained with `from` | conforms | `raise ... from exc` at `marshalld.py:779,805,821` (re-read) |
| CLAUDE.md § Documentation Standards | no version history, no timestamps, current state only | conforms | the three document edits state the current location (leaf reading); the `SKILL.md:102` precedence gap is a minor |
| spec Standing Constraints | stay-inside rule and `runbook-lane/SKILL.md` unchanged; registry wall; machine-global state kept; nothing outside the surface | conforms | the diff stat (re-read); `project_path` has passed `verify_submit` before `_prepare_job_log` (leaf reading) |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope under the ruling of 2026-10-23, so no defect and no recurrence note.
- Duration: not stated.
- Anomalies: three R1 refusals in `.plan/temp/guard.log` (a pipe, a heredoc, backticks in a commit message), all refused and none executed, per the landing; the log was not re-read here. Self-reported deviations: a scoped `git clean -f -x` of two paths in a detached base worktree, and build logs read from the repository's own `build-results` tree. One `verify / verify` failure was the known executor-recovery environment flake and its re-run was green, per the landing. Two bound expiries on routed builds, both continued as documented.
- Model: `deepseek-v4.1-flash/high`, harness `opencode`, one model throughout.

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 11 body findings, 11 handled. `runbook_lane review-gate --pr-number 2023` returns `unresolved_review_threads: 0` and `review_body_findings_total: 11`, both agreeing; `handled` reads 0 from the provider by design (the disposition lives in the run's ledger). `review_body_findings_handled: 11` is **not re-verified**: the progress file carries one prose review line ("11/11 body findings disposed") and no `finding:` lines.
- CI/merge: merged (`352f81a7c`) through the merge queue. CodeRabbit was refused on quota five times and then reviewed two heads, and Sourcery reviewed three heads, both per the landing (not checked here).
- Sonar: `sonar_open_new_issues: n/a`; Sonar is not enabled for this project.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-164 --status shipped`
- [x] row `pr` stamped — `2023`
- [x] row `landing` stamped — `landings/PLAN-LB-164.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-164-build-daemon-job-log-in-project-tree` (from the sender)
- [x] epic.md narrative reconciled: the job-log decision of 2026-11-18 marked shipped; the minors recorded in the BACKLOG Watch
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **No major, nothing reported as a defect to the operator.** The minors L3-1 to L3-8 are one BACKLOG Watch under the focus rule; a plan would be one change in `manage-build-server`, which the operator can ask for.
- **Residue the landing lists:** the routed client folding `log_file_failed` into `execution_failed` without its reason (`script-shared`, outside this plan's surface), the stale `extension-api/standards/build-execution.md:98`, the old `~/.plan-marshall/marshalld/job-logs/` left behind by an upgrade, and three deferred preferences (descriptor-relative opening, a size cap, admission-time identity into `_execute`). Recorded, not staged.
