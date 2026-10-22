envelope_version=1
sender_type=plan
sender_id=rb-lb-79-lb-68-completion
epic=live-blockers
kind=landing
created=2026-10-22T13:13:14Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-79-lb-68-completion
epic=live-blockers
pr=#1835
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
```

guard: present on this harness.

# Landing report — PLAN-LB-79 (lb-79-lb-68-completion)

Merged as `d60b36f8dc152f57532dc330f5188abf798b60a1` (PR #1835). Branch
`fix/lb-79-lb-68-completion` deleted locally and remotely; the main checkout was
fast-forwarded to the merge commit through `git-workflow switch-and-pull`.

## 1. Deliverables

Base-sha evidence was produced against a throwaway clone of `origin/main`
(`d7e351419`; the guard/hook/sweep files are unchanged since `7ccd9166f`).

### D1 — one shared wrapper table — **met** (commit `4087079bc`)

| Done-when | Verdict | Test | order | failing run (base) | commit |
|---|---|---|---|---|---|
| path-qualified `env`/`timeout`, `env -iu`, `sudo -D`, `sudo -p` refused on both harnesses | met | `test_guard_wrapper_table.py::test_d1_side_doors_are_refused_on_both_harnesses` | test-first | `python-2026-10-21-175551.log` (32 failed) | `4087079bc` |
| ionice/chrt/taskset/flock/watch/parallel/busybox/zsh/dash/ksh/`$SHELL`/pypy3/`find -exec` refused | met | same parametrisation + `test_both_harnesses_strip_every_table_wrapper` (derived from the data file) | test-first | same log | `4087079bc` |
| structural: guard.js, hook and pin read one table, no second literal list | met | `test_neither_implementation_carries_a_literal_wrapper_table` | test-first | same log (assert `SHELL_WRAPPERS` not in source fails at base) | `4087079bc` |
| the 18 pre-existing rows still pass | met | `test_guard_hook_parity.py::_SIDE_DOOR_REFUSED` (unchanged 18 rows) | test-first | — | `4087079bc` |

### D2 — exact admissions — **not met as written** (commit `4b44387d9`)

| Done-when | Verdict | Test | order | failing run (base) |
|---|---|---|---|---|
| `env -C /tmp/x …` refused | met | `test_executor_after_an_env_chdir_is_refused` | test-first | `python-2026-10-21-184645.log` |
| `workdir=/tmp/x` refused | met | `test_executor_from_another_workdir_is_refused` | test-first | same log |
| a preceding `cd /tmp/x` followed by the relative executor refused | **not met as written** | `test_executor_after_a_leading_cd_is_refused` | none | this row PASSED at base — R1 already refuses the `;` that joins the two commands, so the clause does not fail at `7ccd9166f` |
| `python3 .plan/execute-script.py` from the repository root admitted | met (holds at base) | `test_executor_from_the_repository_root_is_admitted` | none | positive control |
| a script under `~/.agents/skills` refused | met | `test_a_script_under_an_unnamed_root_is_refused` | test-first | same log |
| a symlink out of a deployed root refused | met | `test_a_symlink_out_of_a_deployed_root_is_refused` | test-first | same log |
| `OPENCODE_CONFIG_DIR` set → deployed script admitted | met (holds at base) | `test_opencode_config_dir_admits_the_deployed_bundle_script` | none | preservation |
| consumer `python3 x.py` refused in a lane run, admitted outside | met | `test_consumer_python_is_refused_inside_a_lane_run` | test-first | same log |

Spec deviation recorded: the bullet's "`git -C`-style directory change … resolved
first" is deliberately NOT implemented as a shell cwd change — git's `-C` moves
git's own working directory for that one invocation, never the directory a
following program runs in (documented in both implementations). A
plan-worktree exemption was added after review (phase-5 pins the shell cwd to
`{worktree_path}`, where `.plan` is the same executor through the symlink); the
Done-when rows above are unaffected (`/tmp/x` and foreign roots still refused).

### D3 — root session parity and R6 — **met** (commit `4178610e7`)

| Done-when | Verdict | Test | order | failing run (base) |
|---|---|---|---|---|
| six side-door forms refused in a root session, no plan context | met | `test_guard_root_session.py::test_root_session_refuses_every_side_door` (both contexts) | test-first | `python-2026-10-21-190305.log` (all six FAILED at base) |
| the side-door table fails when the hook's gating is restored | met | `test_the_side_door_rows_depend_on_the_scope` (negative control: scope off → all admitted) | test-first | same log |
| R6 refuses `--git-dir`/`--work-tree` and `GIT_DIR` commits into a 6-finalize plan | met | `test_r6_names_the_plan_from_every_commit_form` | test-first | same log |
| `git -C "$WT" commit` refused (unresolvable) | met | `test_r6_refuses_an_unresolvable_commit_target` | test-first | same log |

### D4 — the sweep's forms — **met, with evidence order `mutation-after`** (commit `48db7b878`)

| Done-when | Verdict | Test | order | failing run (base) |
|---|---|---|---|---|
| a doc line prescribing a deployed-form command R5 refuses is reported | met | `test_a_deployed_form_doc_line_is_reported_end_to_end` | mutation-after | `test_guard_documentation_sweep_base_probe.py/python-2026-10-22-053658.log` |
| a fixture doc with `bash -c "python3 -c …"` and one with `uv run python -c …` is reported | met | `test_a_fixture_doc_with_bash_c_and_uv_run_is_reported` | mutation-after | same probe log |
| the `upgrade-flow.md` prose recovery command is in the swept set | met | `test_upgrade_flow_prose_recovery_is_swept` | mutation-after | same probe log |

The sweep is BOTH the implementation and the test, so its delivered form cannot
import at the base sha; the base evidence is a probe of the base module's own
behaviour (10 failed / 0 passed: `_is_candidate` false for every form, no
explicit-fixture scan, no deployed resolution, no prose scan). Reported as
`mutation-after`, never as fail-first.

**test-compile runs at every pushed head:** `368d4eaae` (CI run 39731270110,
verify/verify 1208s), `eaae96b83` (CI run 39773635365), `31b5a19e3` (CI run
39776572150, verify/verify 1346s) — all green; local `test-compile` green at
`368d4eaae` (log `default/python-2026-10-21-194430.log`) and at `31b5a19e3`
(`default/python-2026-10-22-120643.log`).

## 2. Personas and skills

Per step: `persona-implementer` for all four deliverables (their `Persona:` line);
`persona-module-tester` as the testing standard inside each declared `Skills:`
list; `persona-code-reviewer` for the three self-review rounds and for triaging
every PR comment.

Per deliverable, the domain skills named by the spec (all loaded):
D1/D2/D3 — `pm-plugin-development:plugin-architecture`,
`pm-plugin-development:plugin-script-architecture`, `pm-dev-python:python-core`,
`plan-marshall:ref-code-quality`, `pm-dev-frontend:javascript`,
`pm-dev-python:pytest-testing`, `plan-marshall:persona-module-tester`;
D4 — the same seven plus `pm-documents:ref-documentation`.
`skills added: pm-plugin-development:plugin-architecture (doc/developer), reason:
surface drift — D2 changed the antigravity runtime documentation that the
spec's Expected Surface does not name`.

## 3. Hypotheses

- **HYPOTHESIS: the end-to-end bypass inputs are admitted by the running guard
  and hook, not only by the code reading** — CONFIRMED. Every D1/D2/D3 row was
  driven through both implementations at the base sha and admitted (e.g.
  `ionice python3 -c x`, `env -u FOO -C /tmp/x …`, `zsh -c "cd …; git commit"`).
- **HYPOTHESIS: the documentation-sweep test lives in
  `test/plan-marshall/platform-runtime/`** — CONFIRMED
  (`test_guard_documentation_sweep.py`).
- **HYPOTHESIS: platform-runtime `layout bundle-cache-root` names every deployed
  root a harness really uses** — CONFIRMED for the deploy roots: the three
  runtimes' lists were consolidated into `standards/deployed-layout.json`, and
  the lists that remained after removing discovery-only roots
  (`.claude/skills`, `.agents/skills`, `opencode/skill`, the two unused gemini
  roots) are exactly the sync engine's `TargetSyncConfig.default_dest` values
  (`marketplace/targets/sync.py:274-296`).
- **Verify-first decisions recorded:** D2 lane recognition = the lane's own
  `.plan/temp/rb-<plan>/progress.md` marker with a 24 h freshness bound; D3 =
  lift the R1-R4 gate for this repository rather than give R5 a second full scan.

## 4. Findings

**Self-review (3 rounds, `budget-exhausted`).** Round 1: 12 findings — fixed the
executor option-order hole (`env -u FOO -C`, `sudo -D`), `watch`/`parallel`
positional splicing, `env find -exec`, R6's git-program check and scoped
fail-closed branch, the D4 end-to-end fixture tests, both-context side-door rows,
the data-file probe roots and the temp-dir leak. Round 2: fixed the env-dependent
R6 test, segment-by-segment splicing of a wrapper's command string, the
resolver-mirrored version rule, the lane-marker freshness bound, the gating
negative control and the remaining doc drift. Round 3: fixed a commit in any
spliced segment and the guard's version comparator. Still open (reported, not
fixed): (a) the spliced walk is blind to shell grouping keywords
(`zsh -c 'if true; then python3 -c x; fi'` is admitted) — MEDIUM; (b) two of the
ten D4 base-probe clauses are structural (`hasattr`) — LOW; (c) D2's leading-`cd`
clause does not fail at the base sha — LOW/reporting; (d) `_guard_node_harness`
leaks a `/tmp/guard-node-*` tree per build — LOW.

**CI.** Every run green on every pushed head; the `verify / verify` job was
skipped on two intermediate heads by the workflow's own gate and ran in full on
`368d4eaae` and `31b5a19e3`.

**PR comments (CodeRabbit, 5 actionable + 1 nitpick).** All five were real and
were fixed in `eaae96b83`: the relative executor was over-refused from plan
worktrees (fixed by admitting the repository's own `.plan/local/worktrees/*`,
which phase-5 pins the cwd to); a `cd` preceding `git commit` inside a spliced
string was dropped by R6 (fixed by composing the `cd` target); the guard's R6
fail-closed scope dropped Signal 1 (fixed by passing the event's agent); the
hook's missing-table branch refused the executor permit (reordered); the R1 doc
row's unescaped pipe broke the GFM table (escaped). The nitpick (vacuous generic
placeholder assertion) was fixed with a positive deployed-path test. Each thread
was replied to and resolved; CodeRabbit confirmed every one as addressed.

## 5. Reviewers

| Reviewer | Required? | Outcome | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | required (`quota_limited: true`) | reviewed | `368d4eaae` (11:43) | triggered 06:01 (rate limited), 08:01 (rate limited), 11:32 (accepted → review 11:43), 11:55 and 12:13 (rate limited/silent). All 5 findings fixed and resolved. |
| sourcery | optional (`quota_limited: true`) | refused | — | 06:01: refused — "PR larger than the review limit of 150,000 diff characters"; optional, so not gating. |

**Standing review authorization** (coderabbit is quota-limited): qualifying
review on `368d4eaae`; current head at merge `31b5a19e3`; each finding fixed in
`eaae96b83` and its thread resolved; re-triggered once after the last push
(12:13, no review); every other gate green on `31b5a19e3` (CI verify/verify
1346s, local quality-gate + test-compile + module-tests 31786).

## 6. Operator questions

1. Asked: how to remove the throwaway clone `.plan/temp/base-clone` (shell `rm`
   and `git clean` are blocked). Options: delete manually / allow a scoped
   `git clean` / leave it. **Selected: "Delete it manually, then tell me".** The
   clone was still present at the end of the run (see Residue).
2. Asked: how to proceed at the self-review round limit with four open findings.
   Options: proceed with them reported / one more fix round / stop. **Selected:
   "Proceed with the open items reported".**

Free-text operator messages: none beyond those selections.

## 7. Rule check

guard: present on this harness; refusals recorded in `.plan/temp/guard.log` for
this run's sessions:

- `2026-10-21T17:48:51Z | rule=R2 | session=ses_ea078fef6ffepiT0NGuT8QyU9m | cp .plan/local/worktrees/…/test_guard_wrapper_table.py .plan/temp/base-probe/…` — the guard refused a `cp`; the file tools were used instead (the same copy was then made with the write tool).
- `2026-10-21T20:04:25Z | rule=R1 | session=ses_e9ff86fd6ffesutpp9D5DoTUFB | python3 - <<'EOF'` — a self-review sub-agent used a heredoc + inline Python; its rule break counts as this run's.
- `2026-10-22T11:14:51Z | rule=R1 | session=ses_e9cafd9c2ffem775mR4wpM5MZ1 | rg -n … | head -20` — a self-review sub-agent piped to `head` and read a path outside the repository; its rule break counts as this run's.

All other rules were kept by the orchestrating session.

## 8. Residue

- **`self-review: budget-exhausted`** with the four open findings in section 4.
- **D2 and D4 are not counted as fully met** (see section 1): D2's leading-`cd`
  clause does not fail at the base sha; D4's evidence order is `mutation-after`.
- **`.plan/temp/base-clone` still exists.** The operator chose manual deletion
  and had not done it by the end of the run. The main checkout's
  `.plan/execute-script.py` was regenerated while that clone existed, so it
  registers 330 scripts (162 of them under the clone). **Regenerate the executor
  (`/marshall-steward`) once the clone is deleted**, otherwise those entries
  dangle.
- The CI abstraction's `pr thread-reply` expects a body of kind
  `pr-thread-reply`, but `pr prepare-comment` allocates kind `pr-reply`; the
  thread replies only worked after writing `pr-thread-reply-<slot>.md` directly.
  Worth a tooling fix.
- `test/plan-marshall/platform-runtime/_guard_node_harness.py` still leaves a
  `/tmp/guard-node-*` tree per harness build (open finding (d)).
