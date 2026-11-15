envelope_version=1
sender_type=plan
sender_id=rb-lb-141-tempdir-teardown-in-test-harnesses
epic=live-blockers
kind=landing
created=2026-11-10T05:01:26Z
revision=2
amended=2026-11-10T05:02:37Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-141-tempdir-teardown-in-test-harnesses
epic=live-blockers
pr=#1951
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

Plan-marshall LB-141 landed as PR #1951, merge commit `e7033b83a2ccacbe1e45163dc15163799cbf7f90`.
guard: present on this harness (the run's sessions wrote no line to `.plan/temp/guard.log`).

Two footnotes on the facts fence, so neither gap reads as a silent one:

- **`total_tokens` is `unknown`, and `inbox landing-check` reports `complete: false` with
  `missing_keys: [total_tokens]`.** The runbook lane carries no metrics recorder, so no phase total exists
  to sum, and this checker rejects `unknown` at `total_tokens` as a failed read. The lane text this run read
  prescribes `total_tokens=unknown` for exactly this state, so the mismatch is between the lane template and
  the checker's measured-subset contract. It is reported here rather than papered over with a fabricated `0`.
- **`surface_delta` is `unmeasured` with `could_not_look: declared_not_supplied_and_realized_not_supplied`.**
  The landing-check call takes no declared/realized footprint arguments, so it compared nothing and said so.
  The realized footprint of this landing is the merged diff of PR #1951, whose files are the ten the PR
  lists; of those, only `test/_shared/_system_temp.py` and `test/README.md` sit outside the spec's Expected
  Surface.

## 1. Deliverables

All three deliverables are fully met. Evidence `order` = how the failing output was obtained.

| Deliverable / criterion | verdict | test | order | failing run | commit |
|---|---|---|---|---|---|
| D1 — relocated harness root removed deterministically, relocation unchanged | met | `test_a_worktree_shaped_scratch_root_is_relocated_and_torn_down` (+ `test_a_plain_scratch_root_is_used_as_is`) | mutation-after | `1cc30ac8627d4d2d8f0e47536b6c117f.log`: reverted `_outside_any_worktree` to a bare `mkdtemp`, `assert system_temp.release(...) is True` → `assert False is True` | 5b3bd8506 |
| D2 — no module-level stub directory; three notations each resolve to an existing file | met | `test_each_mapped_notation_resolves_to_its_existing_stub` ×3 (+ the sweep's module-level arm) | mutation-after | `24e24a6f3e2e41348c1160f5539b95d3.log`: re-added a module-level `mkdtemp`, sweep names `test_execute_script.py:53: module-level mkdtemp runs at import` | 7b6bf95b4 |
| D3 — the sweep fails on an unremoved system temp directory, naming every site | met | `test_no_test_support_module_leaks_a_system_temp_directory` (+ 5 positive controls, 1 matched negative control, the drain control and the unconfigure-wiring control) | mutation-after | `df4c336486c6473b98042187f270cfde.log`: reverted `_write_pom` to a bare `mkdtemp`, sweep names `test_maven_pom_parse.py:35 … in _write_pom` | ad2e19f57 |
| D3 — every flagged site beyond D1/D2 fixed, not debt | met | the sweep's clean verdict over the whole `test/` tree | none | — | ad2e19f57 |
| D3 — relocation unit proof | met | `test_a_worktree_shaped_scratch_root_is_relocated_and_torn_down` | mutation-after | as D1 above | ad2e19f57 |

Per-pushed-head test runs (no head was merged untested):

| head | run | result |
|---|---|---|
| ad2e19f57 | module-tests plan-marshall, 28 139 tests | green (`…/python-2026-11-09-222618.log`) |
| 3085bb47c | module-tests plan-marshall, 28 142 tests | green (`…/python-2026-11-09-233059.log`) |
| bb3b6191d | module-tests plan-marshall, 28 145 tests | green (`…/python-2026-11-09-235616.log`) |
| 9a7b36ea4 | module-tests plan-marshall, 28 145 tests | green (`…/python-2026-11-10-002559.log`) |
| 62a1fe75a | verify (quality-gate + test-compile + module-tests), 33 130 tests | green (`/home/oliver/.plan-marshall/marshalld/job-logs/34bdc93c45b74a23b9c6ed18c86f77b4.log`) |
| bc46cf190 (merge head) | verify, 33 209 tests | green (`/home/oliver/.plan-marshall/marshalld/job-logs/e4a520c2cd2f4114b69f3be2b2a27746.log`) |

Run-private measurement (Standing Constraint 5): `TMPDIR=/tmp/opencode/lb141-measure-1`, run from inside the
plan worktree with `-n auto`, six runs in the SAME root — 6, 7, 8, 9, 10, 10 entries; **zero**
`guard-node-*` and **zero** `executor-mappings-*` after every run, and no directory accumulation across runs.

## 2. Personas and skills

- D1 (test-support production code) — `persona-implementer`. D2 — `persona-implementer`. D3 (the guard is a
  unit test) — `persona-module-tester` + `persona-implementer`.
- Every self-review round and the PR-comment triage — `persona-code-reviewer`.
- The spec's `Skills:`/`Persona:` lines: `skills: none named` (`resolve` reports `skills_note: none named`).
  No surface drift occurred: no module outside the spec's Expected Surface was touched, and the two additional
  files (`test/_shared/_system_temp.py`, `test/README.md`) are the shared-helper home and its contract page.

## 3. Hypotheses

- **OBSERVED (harness relocation, no teardown)** — confirmed pre-change at `_guard_node_harness.py:251`; the
  module now returns through `_system_temp.create`, and the predicate (`'/.plan/local/worktrees/' in
  normalized`) is byte-identical.
- **OBSERVED (68 `build_harness(` call sites, ten files)** — confirmed; zero call-site edits.
- **OBSERVED (module-level `_MAPPED_DIR`, stub loop, three `_MAP_*` readers)** — confirmed at old
  `test_execute_script.py:41-46`/`83-85`/`107`.
- **OBSERVED (pytest-xdist declared; 10 workers on the host)** — confirmed.
- **OBSERVED (three secondary `mkdtemp` sites already clean)** — confirmed; `test_executor_recovery.py`'s
  `finally` (unread by the spec author) does carry `shutil.rmtree`.
- **HYPOTHESIS (bare `mkdtemp` sites may or may not leak)** — resolved site by site: 4 fixed
  (discover_modules ×3, maven_pom_parse, extension_implementations, build-map-seed fixture), the rest
  confirmed already-safe by a `finally` or a class lifecycle method. None left as debt.
- **HYPOTHESIS ("atexit does not reliably run in an xdist worker, a hook does")** — **refuted in its atexit
  half**: a `-n 2` probe registered one atexit-owned and one hook-owned directory per process and BOTH were
  gone after the run (6 workers). The hook half was confirmed. The lane adopted the hook anyway, because
  `pytest_unconfigure` runs at the end of the session and does not depend on interpreter-shutdown semantics;
  the per-root `atexit` remains as a backstop for non-pytest exits. Probe artifact:
  `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-09-215254.log` (6 leftover
  `executor-mappings-*`, the leak observed live).
- **HYPOTHESIS (harness registry + one conftest hook, no call-site changes)** — confirmed in substance, with
  one variation: the registry lives in the shared `test/_shared/_system_temp.py` rather than in the harness
  module, so every test-support site uses one drain.

## 4. Findings

Self-review round 1 (8 open of 13): vacuous sweep → population assertion; fixture-only stub directory → lazy
creation (a cross-module `load_executor_module` would have rendered `None`); token-only removal matching →
bound-name matching; delegation branch masked a second leak → deleted; removal not `finally`-scoped →
scoped; `_system_temp` naming; tuple sort; `release_all` control; `SyntaxError` → named offender. Declined
with reason: reusing `_test_shape_scan.py` (coupling to another instrument) and the stale per-root atexit
handler (no-op on a missing path).

Self-review round 2 (11 open): teardown wiring untested → the new control drives the real
`conftest.pytest_unconfigure`; `atexit` receiver now checked; class-lifecycle negative control;
`AnnAssign`/walrus; `yield from`; `try/except*/finally`; README documents `_system_temp`; prefix on the
extension helper; evidence carried here. Declined with reason: the per-root atexit cost, and moving the guard
to a root-level file (the spec proposes this path).

Self-review round 3: **open: 0** — no blocking finding, no regression from round 2. Its three nits were then
closed in 9a7b36ea4 (a registered teardown must name a removal callable; the unreachable `weakref` arm
dropped; walrus and `yield from` controls added).

CI found what the local quality gate does not run: `test-compile` (mypy over `test/`) reported four
`arg-type`/`attr-defined` errors in the sweep, because the custom predicates do not narrow for mypy. Fixed in
62a1fe75a by narrowing on `isinstance(node, ast.Call)` before reading `node.args`; `verify` and CI then went
green.

No PR-comment finding arrived: CodeRabbit's review produced "No actionable comments were generated";
Sourcery never reviewed.

## 5. Reviewers

| reviewer | required | outcome | head reviewed | history |
|---|---|---|---|---|
| coderabbit | yes (`quota_limited`) | reviewed (0 findings, "Merge Risk: Minimal") | 62a1fe75a (`final_review_risk_coverage.kind=reviewed`, `coveredCommitId=62a1fe75a`) | triggered 00:38:15Z → quota refusal ("next included review in 38 min"); re-triggered 02:10:12Z after the 90-minute policy wait → quota refusal (no ETA); escalated `@coderabbitai full review` at 03:42:20Z → full review finished 03:50:41Z with zero findings; re-triggered once after the merge push at 04:06:12Z → quota refusal recorded |
| sourcery | no (`optional`, `quota_limited`) | refused (hard quota, 2 days) | — | triggered 00:38:27Z |

**Standing review authorization used for the merge head `bc46cf190`**: CodeRabbit is `quota_limited`; a
qualifying review exists on 62a1fe75a (a head of this PR) with zero findings; every finding handled (none
exist); it was re-triggered once after the merge push and refused (recorded); every other gate condition
holds on the merge head (CI green, `verify` green, `review-gate` `all_handled`, `sonar-gate`
`not_configured`).

## 6. Operator questions

none asked. No free-text operator messages were sent.

## 7. Rule check

`guard: present`; the guard's audit log `.plan/temp/guard.log` has **no line for this run's sessions** — its
last entry is `2026-11-09T20:08:57Z`, before this run's 21:49Z start. So no guard refusal occurred.
Deviations the run itself must report:

- **Read/list outside the repository (rule: stay inside the repository).** The plan's own Standing Constraint
  5 requires a RUN-PRIVATE `TMPDIR` and an assertion over its contents after pytest exits, and a `TMPDIR`
  inside the repository makes ~85 repo-relative tests fail (measured). The root used is
  `/tmp/opencode/lb141-measure-1`, created by this run; only its own entries were listed (never file
  contents, never any other path). This is the one deliberate bend, forced by the spec.
- **One shell file-read command**: `wc -l .plan/temp/guard.log` (a line count of the guard log), instead of a
  file tool.
- **One leftover directory from a mutation run**: `guard-node-_8ylsp_7` in `/tmp`, created by the D1 mutation
  that deliberately reintroduced the leak. Removing it is a shell file operation the lane forbids, so it is
  reported instead.
- **`git mv` and `git commit --amend`** were used; the amend touched an unpushed commit only (to fold in the
  gate's own auto-formatting).
- No build was backgrounded, no `sleep`, no CI CLI, no direct `pytest`/`ruff`/`mypy`/`pw` invocation, and
  every script call used the executor notation.

Spec-read record: `resolve` read the **ledger worktree** copy (`spec_source: ledger_worktree`) and carried
**no `spec_differ` marker**, so the main checkout's copy did not disagree.

`executor-skew`: **not_applicable** (source checkout; the executor maps this checkout's own scripts) —
answered, recorded, never asked about.

## 8. Build server

- Setup preflight on the worktree: **ready** (registered).
- Mechanisms: **daemon_longpoll** for the gate builds and the verification runs (≈24 builds),
  **in_process_fallback** for 8 builds — every one of them a run that carried `--env TMPDIR=…` for the
  run-private measurement, where the routing client answers `degraded` with `reason:
  env_or_working_dir_set`. No launch-fault retry; no `killed` job; one live job (`8dc67945…`) re-attached
  through `build_server wait` and completed successfully.
- `runtime_stamp_reason`: absent — the resolve stamp resolved every field.

## 9. Residue

- **Owed, out of scope and operator-run** (as the spec requires): a `systemd-tmpfiles` rule or janitor reaping
  stale `guard-node-*` / `executor-mappings-*` directories (the only cover for killed runs) and any raise of
  the tmpfs `nr_inodes` limit. Both live outside the repository.
- `create_temp_file` (a `mkstemp` FILE helper) drops one `tmp*.md` file into TMPDIR per suite run. It is a
  file, not a directory, so it is outside this plan's sweep; recorded here rather than fixed.
- Sourcery never reviewed this PR (hard quota until roughly 2026-11-12); it is optional, so the merge gate was
  satisfied without it.
- `test/_shared/_system_temp.py` registers one `atexit` handler per created root; after `release_all` those
  handlers are no-ops. Accepted as a nit (one no-op `rmtree(ignore_errors=True)` per root at exit) rather than
  switching to a single shared drain, which would require the sweep to credit a registration that does not
  name its directory.
- The guard file sits at `test/plan-marshall/platform-runtime/test_tempdir_teardown.py` rather than at the
  root as a tree-subject meta-test; the spec proposes this path (Expected Surface, HYPOTHESIS), so the
  placement is recorded as a deviation from `test/README.md`'s convention rather than changed.
- `test/conftest.py` loses the unused `create_temp_dir` helper (its contract was "caller must delete with
  shutil.rmtree") and `test/README.md` loses its row — a surface change the spec does not name, made because
  Deliverable 3 flags the helper's bare `mkdtemp` and it has no caller anywhere in the tree.
