# Landing Analysis: PLAN-LB-108 — one build per project directory

epic: live-blockers
workstream: WS-04
pr: #1922

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-108.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `9bd6a39d2f07a657c9200e50cb148bd4277b5ac1`, a squash commit with ONE parent, `a8840acf1c4161856fc34e693180cc662128152f` (the ledger land of PR 1924, read with git and named in the leaf prompt). Landing message `rb-lb-108-build-daemon-worktree-serialisation-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 33 files, +2759/−179 (`git show --stat 9bd6a39d2`). The lane reports 3 of 5 deliverables done, `self-review: budget-exhausted` after three rounds (the operator chose to proceed to the PR), a spec read from the ledger copy.

Surface against the spec's Expected Surface: the diff touches about fifteen files the spec did not declare, not the two the lane names — four docs under `doc/concepts/` and `doc/developer/`, `build_server.py`, `_build_result.py`, `_build_shared.py`, `_build_directory_state.py` (new), `pyproject.toml` (a marker registration), `test/conftest.py`, three `build-pyproject` tests, `test_fallback_escalation.py`, `test_build_execute_factory.py`. Two files the spec expected were not touched (`_locks_core.py`, `_build_queue_fixtures.py`). Only `build_queue.py` gains parser arguments (`--token`, `directory status|clear`), so an executor regeneration IS owed after the merge, together with the harness sync and the daemon reconcile (the lane lists the last two).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the daemon admits at most one job per directory | shipped; one Done-when clause not met (edited round-robin test) | `_marshalld_scheduler.py` `admit_next` takes the first free-directory candidate and keeps the rotation; `marshalld.py:672-673` skips a directory with a live in-process holder (leaf). The round-robin test and three cap tests were edited (job trees only, no assertion weakened, leaf); "unchanged" is not met as written, as the lane says. The "red at HEAD" is red by construction (a new keyword argument), not by B being admitted. |
| D2 — the wait is visible | shipped | `queued_behind` on submit, `queued` with `waiting_on` and `queued_seconds` on wait, `LIVE_STATUSES` in the routed client, the `_PASSTHROUGH_STATUS_FIELDS` extension (leaf, all cited lines). The "fields consumers read unchanged, each with its own check" clause rests on the existing suites. |
| D3 — a per-directory lock on every in-process build | shipped-modified; two Done-when clauses not met as written, as the lane says | The two-build test drives two threads of one process through `directory_lock`, never `cmd_run`, and never asserts the key `cmd_run` passes. The cross-order test builds one half of the shape. The lock lives as top-level keys of `build-queue.json`, written through `rmw_json`; `_next_state` carries them (leaf). |
| D4 — a slot per build invocation | shipped | `_entry_identity` and `run_acquire` in `build_queue.py` (leaf); the tokenless and pre-token edges are tested; the "release of an absent id" edge has no new test. |
| D5 — docs describe the mechanism | **not met as written** (the lane says met) | See L1-11: the Done-when is "no doc or comment describes the per-plan or slot-only model as current". |
| executor regeneration | owed | Parser arguments added in `build_queue.py`. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit. It reported tool deviations (a skill load, a denied Grep, a failed `git` call re-run quoted) and no write. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — the read crosses 33 files, with 14 narrative claims passed one by one. It ran beside the leaves for PLAN-LB-119 and 120.
- **Verdict:** layer 1 findings (minor); layer 2 findings (minor); layer 3 findings (minor and info only). No blocker and no major.
- **Orchestrator re-read:** L1-11 (all three stale texts), L3-1 (the wait loop). Every other row is a lead the leaf checked and I did not re-read.
- **Prompt check.** The 14 claims went into the prompt as separate items.
- **Not read by the leaf:** the PLAN-LB-115 and 116 specs (the collision note below is the orchestrator's reading), the PR body, the full `test/conftest.py`, `runbook_lane.py` and other consumers of the hand-back `job_status`, a repo-wide sweep for leftover `unserialized` or per-plan wording.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at 9bd6a39d2) |
|---------|-------|---------|-----------------------------------|
| L1-11 (minor, re-read) | D5 Done-when: no doc or comment describes the per-plan or slot-only model as current | **not met.** The `build_queue.py` module docstring still describes `acquire` as plan-id idempotent ("if the plan already holds an `active` slot OR already has a `waiting` entry — REUSE that existing id"), which is the behaviour D4 removed for a token acquire. `doc/concepts/parallelism-and-locking.adoc:25` keeps "A build takes exactly one limiter path — daemon or in-process, never both, never stacked", and the same document's own `:23` says the daemon child takes the in-process leg too. `_build_result.py:166` still says the hand-back `job_status` is "always 'running' on this shape", while the hand-back now carries `queued`. The lane graded D5 met. | `build_queue.py:46-62`; `doc/concepts/parallelism-and-locking.adoc:23,25`; `_build_result.py:166` |
| L1-7 (minor, leaf) | D3: two in-process builds of one tmp directory concurrently | not met as written (the lane says so): two threads, one pid, `directory_lock` only | `test_build_queue_slot.py` `test_two_plan_less_builds_…` |
| L1-9 (minor, leaf) | D3 cross-order test | met with deviation (one half) | `test_a_directory_holder_waiting_on_a_slot_does_not_deadlock` |
| L1-4 (minor, leaf) | D1 existing tests unchanged | not met as written (the lane says so) | `test_marshalld_scheduler.py` hunks at 45, 81, 154, 211 |
| L1-12 (minor, leaf) | Constraint: no I/O inside `_mutate` | violated literally: `os.kill` and a `/proc/{pid}/stat` read run inside `_mutate`; the existing `holder_is_dead` reaper has the same precedent | `build_queue.py:1354,1356,1557` |
| L1-6 (minor, leaf) | D2 fields consumers read, each with its own check | met with deviation: no new dedicated check for `elapsed`, `eta`, `last_progress`, `attached` | acceptance diff |
| L1-14 (info, leaf) | Expected Surface | about fifteen files outside it | see above |

**Layer 1 verdict:** findings — all minor; one Done-when clause (D5) not met that the lane graded met.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1 (first free-directory candidate, rotation kept), C2 (re-admission on wait entry and every poll, `marshalld.py:526,529`; re-read), C3, C4, C6, C11 (only `build_queue.py` gains parser arguments), C12 (`js_coverage.py` parses a report and spawns nothing, so it does not bypass the lock), C13, C14 (`deliverables_done=3` is D2, D4, D5 as the lane graded them; with L1-11 the honest count is 2).
- **C5 corroborated, and the docs overstate it:** the in-process holder never waits on a daemon slot, so there is no cycle at all; the cost is a daemon slot spent for up to the child's wait bound (L2-5, info).
- **C7 partly contradicted:** the rename, the re-pin and the `directory-only` label hold; the three stale texts do not (L1-11).
- **C8 deviations real.** The round-robin edit does not weaken D1; the D3 two-build test does weaken D3. The suite-wide no-op of the directory lock (`conftest.py` `_neutralize_directory_lock`, opt-out marker `real_directory_lock`) means no `cmd_run` test runs the real lock. A key mismatch would be hidden; the leaf read the code and found none today. It also hides L3-4.
- **C9 mostly confirmed:** holder pids in the status report are only control-character stripped, not coerced to integer-or-empty (`build_queue.py:1496` against `:1507`; `marshalld.py:594`). TOON-safe; minor.
- **C10 contradicted:** the surface is wider than the lane says.
- **Both keys agree (leaf):** `Path.resolve()` on the same absolute tree in the daemon (`marshalld.py:493`), the lock (`_build_queue_slot.py` `directory_lock`) and the factory (`_build_execute_factory.py:1246,1268`). The routed parent takes no lock, so it cannot deadlock with its own child.

**Layer 2 verdict:** findings — one claim partly contradicted (C7), one contradicted (C10), two minor; the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `marshalld.py:526-529,672` | An in-process holder releases while free daemon slots exist and no client is waiting (for example after a 300 s hand-back) | Re-admission runs only on submit, on complete and inside `wait`; the daemon has no timer. The queued job stays `queued` until an unrelated event, then runs late, possibly against a worktree that has moved on. | minor |
| L3-2 (leaf) | `_build_server_protocol.py` (`LIVE_STATUSES` only) | A client from before the merge (an older worktree's own scripts) waits on a reconciled daemon | It meets `queued`, treats it as an unknown terminal status and reports `indeterminate`. `PROTOCOL_VERSION` is unchanged, so the handshake cannot detect the skew. | minor |
| L3-3 (leaf) | `_build_execute_factory.py` about `:1046-1058`; `_build_shared.py` about `:887`; `_build_result.py:166` | A consumer keyed on `job_status == running` for a hand-back | The hand-back can now carry `queued`, against the TypedDict comment. Other consumers of the field (`runbook_lane.py`) were not read. | minor |
| L3-4 (leaf) | `_build_queue_slot.py` `directory_lock`; `_build_execute_factory.py:1812-1815` | A plan-less in-process build with an unwritable `~/.plan-marshall/build-queue.json` or a guard timeout | Every in-process build now needs that file. An acquire failure raises a bare `RuntimeError` the caller does not catch: a crash, not a structured error. The suite-wide no-op lock hides it from every `cmd_run` test. | minor |
| L3-5 (leaf) | `_build_queue_slot.py` `_DIRECTORY_WAIT_SECONDS = 1800` | A queued in-process build under an agent shell with a 600 s ceiling | The harness ends the call long before the 1800 s bound, so the named `directory_busy` error never surfaces. | minor |
| L3-6 (leaf) | `build_queue.py:1552-1565`, `_waiter_is_live` | A waiter whose pid reads alive (suspended, or a reused pid) | It blocks the directory's FIFO for up to 7200 s; `directory clear` touches holders only. | minor |
| L3-7 (leaf) | `_build_directory_state.held_directories`; `marshalld.py:673` | A holder pid reused after a crash | The holder reads live, so daemon jobs for that directory are never admitted (the daemon queue has no timeout) and every in-process waiter fails at 1800 s. Only `directory clear --force` recovers it. | minor |
| L3-8 (leaf) | `marshalld.py:673` | An in-process waiter is queued for a directory | The daemon admits into it anyway and the child waits behind the waiter holding a daemon slot: the bounded window is wider than "a moment". | info |
| L3-9 (leaf) | `marshalld.py:576-595`; `build_queue.py` `_holder_view` | A job queued only on the slot cap; an earlier waiter | `waiting_on` is empty; `directory_busy` can name an earlier waiter as the holder. | info |
| L3-10 (leaf) | `Path.resolve()` | A case-insensitive file system; a root build beside a `--project-dir` sub-module build | The case is not folded; the two keys are separate and can overlap in the sub-module's `target/`. | info |
| L3-11 (leaf) | `marshalld.py:610-617` | The daemon reads the queue file unguarded | It fails open to "nothing held"; safe, because the child takes the lock anyway. | info |
| L3-12 (leaf) | `_build_execute_factory.py:1791` | Any in-process build of Maven, Gradle, npm or pyproject | All now touch the machine-global file and serialise per directory; the log token changed from `unserialized` to `directory-only`, which breaks any grep on the old token. | info |

**Layer 3 verdict:** findings — no major; minor L3-1 to L3-7, the rest info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `af324fae9` and `bbe8e9162` (seven findings across two reviews, all fixed in `5a98b4537` and `d6749fe02`, threads resolved), a rate-limited third round on the merged head `25e2a2098`, the standing authorization applied, and Sourcery (optional) refusing on size. Three self-review rounds (the operator chose "proceed to the PR now" over a fourth). I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `9bd6a39d2` and its subject.

## Residue and Watches

- No major layer-3 finding, so no fix plan is owed on the focus rule. The minor set (L1-11 docs, L3-1 wake-up, L3-2 skew, L3-4 structured error, L3-5 bound against the shell ceiling, L3-6 and L3-7 recovery) is one coherent follow-up on the same files (`build_queue.py`, `marshalld.py`, `_build_queue_slot.py`, three docs). It is NOT staged; it is offered to the operator as an optional small plan.
- **Collision watch (the orchestrator's reading; the leaf did not read the specs):** PLAN-LB-115 (held behind this plan) and PLAN-LB-116 cite line numbers in `_build_execute_factory.py` and the runbook-lane files this merge moved (the routing comment, `_record_resolution`, `_daemon_result_to_direct`/`_map_daemon_result`, `_running_hand_back`, the `_route_to_daemon` wait loop, the in-process leg of `cmd_run`; `runbook-lane/SKILL.md` § 4). Both specs must be re-grounded against HEAD before they are emitted; the cleanup pass re-reads them.
- Owed outside this plan, operator-run: the daemon reconcile (`manage-build-server install/upgrade`), the harness sync, the executor regeneration (parser arguments added), and the post-merge live check of two builds for one worktree with the second reporting `queued`.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (shell file operations, reads outside the repository for build logs, two guard refusals) is its own account and is not re-read.
