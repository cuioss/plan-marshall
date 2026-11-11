# Landing Analysis: PLAN-LB-141 — tempdir teardown in the guard-node harness and the executor-mapping tests

epic: live-blockers
workstream: WS-04
pr: #1951 (merge commit `e7033b83a2ccacbe1e45163dc15163799cbf7f90`, one parent `549e35374`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent, ten files, +828/-31, every path under `test/`; no file under `marketplace/bundles/` changed, as the spec's standing constraint requires. The facts block (`pr=#1951`, `merge_state=merged`, `deliverables 3/3`, `review_body_findings 0/0`) agrees with git and with `runbook_lane review-gate --pr-number 1951` (0 threads, 0 findings, `merge_allowed: true`). The message was amended once (revision 2) before it was drained. `total_tokens=unknown` is an unobserved fact, not a defect.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — harness teardown, relocation unchanged | shipped-as-specified | `_outside_any_worktree` (`_guard_node_harness.py:258-261`): the predicate `'/.plan/local/worktrees/' in normalized` and the `else: return scratch` arm are untouched; only the creator changed, to `_system_temp.create(prefix='guard-node-')`. Re-read. None of the ten `build_harness` caller files is in the diff. The registry is drained by `pytest_unconfigure` in `test/conftest.py:1604`, with a per-root `atexit` backstop (`_system_temp.py:49-52`). Re-read. |
| D2 — no module-level stub directory | shipped-as-specified | Lazy `_mapping_stub_directory()` called by `load_executor_module`, a session autouse fixture releases it, one parametrized criterion per notation asserts the resolved path and `is_file()` (leaf, `test_execute_script.py` 61-212, not re-read). |
| D3 — leak regression guard | shipped-as-specified | `test_tempdir_teardown.py`: recursive scan of `test/`, population assertion, six positive controls and a negative control (leaf, 310-448, partly re-read). Six extra sites fixed across four files, versus the narrative's "four extra sites". |
| Run-private TMPDIR measurement | claimed, not re-run | The lane reports six runs in one private root with zero `guard-node-*` and zero `executor-mappings-*`. Run evidence; not shown by reading. |

Files outside the spec's Expected Surface, each disclosed by the lane: `test/_shared/_system_temp.py` (the shared registry), `test/README.md`, the unused `create_temp_dir` helper removed from `test/conftest.py`, and the four extra converted sites. The leaf's repository-wide diff search found `create_temp_dir` in no tracked file at the tip. Untracked and git-ignored trees were not covered.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the two sibling landings drained in the same scan.
- **Verdict:** layer 1 findings (2, minor); layer 2 clean (surface expansion disclosed, nothing unexplained); layer 3 findings (8, minor) plus three points not shown by reading. No blocker or major.

Re-read at `_system_temp.py` 1-78, `conftest.py` 1590-1619, `test_tempdir_teardown.py` 36-185 and `_guard_node_harness.py` 246-262. **Not re-read** (unverified leads): `README.md:95`, the `test_tempdir_teardown.py` controls at 310-448 and 511-582, `test_execute_script.py`, `test_maven_pom_parse.py`, the `create_temp_dir` search, the ten caller files, and the pytest-version claim behind L3-1.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D3 as written covers only `tempfile.mkdtemp`, while the standing constraint forbids any import-time temp-directory creation. A guard built to D3's letter cannot see a module-level `_system_temp.create`, an aliased `mkdtemp` or another directory primitive, so D3 does not enforce its own constraint. | checked (spec re-read; sweep recogniser re-read) | refutes | spec D3; `test_tempdir_teardown.py:57-64` |
| L1-2 | The spec requires that a second run in the same private root "shows no accumulation"; the lane's table shows 6 to 10 entries over the runs (one `tmp*.md` file per run from the `mkstemp` helper). No directory accumulates, but the wording is not met literally. | checked (lane's table) | refutes | lane report § 1 |
| — | The spec premise "ten caller files of `build_harness`" holds; the count of 68 itself was not counted. | checked (leaf) | confirms | `_guard_node_harness.py:290` |

**Layer 1 verdict:** findings — 2 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_guard_node_harness.py:258-261`, `_system_temp.py:39-78`, `conftest.py:1604` | relocation unit proof and plain-path control (leaf, `test_tempdir_teardown.py` 548/573); wiring control (511) | none | checked |
| D2 | `test_execute_script.py:61` (leaf) | one criterion per notation (leaf, 188-212) | none | checked |
| D3 | `test_tempdir_teardown.py:57-185` | the sweep plus controls (leaf, 310-448) | none | checked |

Nothing the diff touched is unexplained; the narrative's "four extra sites" is six sites in four files (a wording slip, not an overclaim of work). The claim that `pytest_unconfigure` runs in every xdist worker rests on the lane's own `-n 2` probe; no committed test runs under xdist, so it is not shown by reading.

**Layer 2 verdict:** clean (no finding); not shown by reading — 2 (the xdist worker claim, the unread remaining `mkdtemp` sites)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `test_tempdir_teardown.py:43` | a class method named `teardown`, `cleanup`, `close` or `__exit__` that removes a directory a `setup_method` created | `_LIFECYCLE_METHODS` credits the name without proving pytest invokes it; the leaf says a plain `teardown` method is not called under the pinned pytest, so the sweep passes and the directory leaks (unverified: the version claim was not re-read) | minor |
| L3-2 | `test_tempdir_teardown.py:163-173` | `root = mkdtemp(); prepare(root)` (raises) followed later by `try: ... finally: rmtree(root)` | any `try`/`finally` in the function that removes the same name credits the site, regardless of position, so an exception before the `try` leaks and the sweep passes | minor |
| L3-3 | `test_tempdir_teardown.py:176-185` | a generator fixture whose setup raises between `mkdtemp` and the `yield` | a removal after the last `yield` is credited, but pytest never runs post-yield code after a setup error, so the directory leaks | minor |
| L3-4 | `test_tempdir_teardown.py:47, 57-64` | `from tempfile import mkdtemp as mk`; a module-level `_system_temp.create(...)`; `os.rmdir`/`os.unlink` as the "removal" | the aliased call is invisible, the import-time `create` is never examined, and `rmdir`/`unlink` are credited though they fail on a non-empty directory or on any directory | minor |
| L3-5 | `_system_temp.py:51, 68, 72-78` | `release()` followed by process exit; a root whose removal fails | `release()` drops the registry entry but leaves the `atexit` handler, which `rmtree`s the path a second time (a foreign directory of the same random name would be deleted, probability negligible); every removal uses `ignore_errors=True`, so a root that cannot be removed (a read-only subtree) is popped and left behind with no signal | minor |
| L3-6 | `_system_temp.py:24-25`, `test/README.md:95` (not re-read) | — | both say a bare `mkdtemp` in a test module "fails the suite"; function-level `mkdtemp` with a `finally` passes by design, and the shapes in L3-4 are not examined. The docs overstate the guard | minor |
| L3-7 | `_guard_node_harness.py:253-256` | — | the docstring carries transitional history ("Before that ... over five days ... about 41,000 directories") against the current-state documentation rule; the "(68 call sites)" figure is already stale (the new test adds `build_harness` calls); `test_execute_script.py` 45-48 and `test_tempdir_teardown.py` 553-554 carry the same kind of history (leaf, not re-read) | minor |
| L3-8 | `_system_temp.py:36-52` | — | no list locking; fine because tests do not create roots from threads (leaf: `info`) | info |

**Layer 3 not shown by reading:**

- Whether `pytest_unconfigure` and the `atexit` handler run in EVERY xdist worker under `-n auto`: the hook's own docstring (`conftest.py:1607-1611`) cites the lane's `-n 2` probe, and the lane's report says the `atexit` half of its hypothesis was refuted by that probe (both directories were gone). A killed worker skips both and stays out of scope by design.
- The run-private TMPDIR measurement (six runs, zero leaked directories) and the green gates are run evidence.
- Whether the remaining bare `mkdtemp` sites the leaf did not read are safe (`_manage_files_open_in_ide_fixtures.py`, `test_manage_files_open_in_ide_static_guards.py`, `test_guard_exact_admissions.py`, `test_runbook_lane.py`, `test_executor_integration.py`, `test_doctor_marketplace.py` and the other `conftest.py` sites). The sweep, if it passes on the real tree, is the authority.

Settled in the fix's favour (checked): `pytest_unconfigure` cannot raise or mask a result (`release_all` pops and calls `rmtree(ignore_errors=True)`; in the xdist controller the registry is empty). Re-read at `_system_temp.py:72-78` and `conftest.py:1604`. The relocation semantics are unchanged.

**Layer 3 verdict:** findings — 7 (minor) plus 1 info; not shown by reading — 3

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec standing constraint | test-support only; no file under `marketplace/bundles/` changes | conforms | `git diff --stat 549e35374 e7033b83a`: ten paths, all under `test/` |
| spec standing constraint | relocation semantics unchanged | conforms | `_guard_node_harness.py:258-261` |
| spec standing constraint | teardown holds under `pytest -n auto` | not_shown_by_reading | `conftest.py:1604`; proof is the lane's probe |
| spec standing constraint | no import-time temp-directory creation in a touched module | conforms | leaf: lazy creation, `test_maven_pom_parse.py` read in full |
| spec D1 | the 68 call sites need no edit | conforms | none of the ten caller files is in the diff |
| spec D3 | the guard names every site; no flagged site accepted as debt | conforms | leaf: rows `label:line:reason`, zero offenders asserted, six extra sites converted |
| spec verification | no accumulation on re-run | not_shown_by_reading | one `tmp*.md` per run (L1-2) |
| CLAUDE.md § Documentation Standards | current state only | deviates | L3-7 |
| CLAUDE.md § Commit Trailer | trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, no PR footer | conforms | leaf: the squash body ends with the trailer |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` `missing_keys: [total_tokens]` is no defect.
- Anomalies: eight builds ran in-process because the routing client degrades on `--env TMPDIR=...` (`env_or_working_dir_set`), which is expected and not a launch fault. CI found four `mypy` errors in the new sweep that the local quality gate does not run (`test-compile`), fixed at `62a1fe75a`. One `guard-node-*` directory was left in `/tmp` by the lane's own mutation run; the lane reported it instead of removing it.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) produced "No actionable comments"; the run used the standing review authorization for the merge head after the 90-minute quota wait and an escalation to `@coderabbitai full review`. Sourcery (optional) never reviewed. The three review numbers re-read with `runbook_lane review-gate --pr-number 1951`: `unresolved_review_threads` 0, `review_body_findings_total` 0 and `merge_allowed: true` agree with the landing; `handled` 0 of 0 trivially holds.
- CI/merge: `verify` and CI green at the merge head; merge-queue squash with one parent.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-141 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-141 --field pr --value 1951`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-141 --field landing --value landings/PLAN-LB-141.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-141 --field plan_marshall_plan_id --value rb-lb-141-tempdir-teardown-in-test-harnesses`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- **Operator-owed, unchanged by this landing:** the `systemd-tmpfiles` janitor for killed runs and the optional `nr_inodes` raise. Both live outside the repository.
- **Not a defect, recorded:** `create_temp_file` (a `mkstemp` file helper) drops one `tmp*.md` file into the temp directory per suite run; outside this plan's directory sweep.
- **Watch:** the sweep's blind spots (L3-1 to L3-4) and the overstated guard docs (L3-6). All are minors of a guard whose job is regression detection on the two named sites; none is staged.
- The inode-exhaustion Open Defect for the test harnesses is retired by this landing for the two named sites; a live count of `guard-node-*` in the system temp directory after the next suite run from a plan worktree is the cheap confirmation, and is run evidence rather than a reading.
