# Landing Analysis: PLAN-LB-79 — The R5 enforcement cannot be walked around with a path-qualified wrapper, an unlisted wrapper or a relative executor

epic: live-blockers
workstream: WS-04
pr: #1835 (`d60b36f8d`, parent `3baf825e4`, merged 2026-10-22T12:42:38Z)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims
> against ground truth. A claim marked **(agent)** rests on the read-only corroboration's code
> reading and was not re-read by the orchestrator; a claim marked **(re-read)** was read again
> by the orchestrator in the tree at `d60b36f8d`. Nothing below was executed: no `node`, no
> hook call, no test run.

## Verdict

**Grade: C+.** Runbook lane, DeepSeek `deepseek-v4.1-flash` at variant `high` for the whole
tree (5 sessions, no model switch), 19 h 40 min wall clock, $1.76.

The plan shipped what it set out to: one shared wrapper table, exact admissions, root-session
parity and a wider documentation sweep, with 17 named tests and every sha it cites resolvable.
It also reported honestly three things a weaker run hides: D2's leading-`cd` clause does not
fail at the base sha, `git -C` was deliberately not implemented as a cwd change, and D4's base
evidence is a `mutation-after` probe. CodeRabbit's five findings were all real and all fixed.

It does **not** deliver the spec's objective that the enforcement "cannot be walked around":
the splice walk stays blind to shell grouping keywords, to options before `-c`, to here-strings
and to a `cd` inside the spliced string, so the executor admission D2 made exact is still
walkable through the very shells D1 added. The self-review found one of these (item (a)) and
rated it MEDIUM; there are at least five more of the same class. The landing also misstates its
own rule check: a `guard.log` line from another run, 67 read-class shell calls and several
undisclosed improvisations under "all other rules were kept", a "test-first" label the
timestamps contradict, and an operator question built on a misread executor. Grade drops from
the B− the work deserves to C+ for the report, not the code.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 One shared wrapper table; path-qualified and unlisted wrappers | shipped-modified | `r5-wrappers.json` read by `guard.js` `loadWrapperTable` L925-938 and the hook `_wrapper_table` L562-595, no `SHELL_WRAPPERS` literal in either **(agent)**. Residual literals outside the table: the directory options in `effectiveCwd` (guard L614-619, hook L897-902) and the R2 spawn sets (guard L135-138, hook L199, `sh`/`bash`/`source` only). The wrapper walk is not complete (C1, C2, C3). The spec's verify-first clause on `git grep` was never decided (C8). |
| D2 Relative executor, deployed roots, consumer scope admitted exactly | shipped-modified | Realpath-based roots from `deployed-layout.json`, none of the four dropped roots present **(agent)**; `OPENCODE_CONFIG_DIR` honoured; lane marker (24 h) binds a consumer run. The leading-`cd` clause is a preservation row (R1 already refuses the `;`), disclosed. `git -C` not implemented, disclosed. A plan-worktree exemption was added after review: exact on realpath plus a `worktrees/` slash boundary, but it admits any depth, `_orchestrator` included (C4). A `cd` inside a spliced string is never applied (C2). The unversioned `{root}/plan-marshall/{entry}` candidate is still accepted (C6). |
| D3 Root-session parity and R6 | shipped-modified | The hook's R1-R4 gate is lifted for this repository (hook `evaluate` L1883-1903, `_is_this_repository` L1005-1021 **(re-read)**); R6 names the plan from `--git-dir`, `--work-tree`, `GIT_DIR`, a resolved alias and an unexpanded `-C`, fail-closed inside the enforced scope. The lift made the hook refuse every `./pw` (L529-537 **(re-read)**), including `./pw generate` that CLAUDE.md prescribes (C5). |
| D4 Documentation sweep forms | shipped-as-specified, evidence `mutation-after` | `test_guard_documentation_sweep.py` (+553). The cited base evidence, `test_guard_documentation_sweep_base_probe.py`, is in no commit: it exists only as an untracked file in `.plan/temp/base-clone` **(agent)**. `upgrade-flow.md` is read by a test and not edited. |

Claimed `deliverables_done=2` of 4: D1 and D3 counted met, D2 and D4 withheld. The table above
is the plan's own, and the count follows it.

**Surface.** The spec declared 6 entries; the diff has 22 files (+3495/−639). Ten sit outside
the declaration: `script-shared/scripts/deployed_layout.py` (new), `marketplace_paths.py`,
`_claude_runtime_impl.py`, `antigravity_runtime.py`, `claude_runtime.py`, `opencode_runtime.py`,
`platform-runtime/SKILL.md`, `doc/developer/antigravity.adoc`, `deployed-layout.json`, and
`test_extension_discovery.py`. Two declared entries were not touched (`r5-allowlist.json`,
`upgrade-flow.md`). The shipped spec is not edited; the effect on the corpus is the re-ground
below.

## Code Defects (adversarial)

Severity is the orchestrator's. C1-C3 are by code reading (agent) with the mechanism of C1 and
the missing-table branch of C3 re-read; nothing was executed.

- **C1 — high.** `splicedSegments` (guard L344-380 **(re-read)**, hook L662-697) splits only on
  `; & | newline`. A segment starting with `if`, `then`, `do`, `{`, `(` or `!` leaves the keyword
  at token 0, `stripWrappers` stops, and R5 sees no interpreter. Admitted by reading, on both
  harnesses: `zsh -c 'if true; then python3 -c x; fi'`, `zsh -c '(python3 -c x)'`,
  `zsh -c '{ python3 -c x; }'`, `zsh -c '! python3 -c x'`, `for … do`. `bash -c` and `sh -c`
  variants are refused only by R2, not R5.
- **C2 — high.** `effectiveCwd` stops at the splice (guard L628-630, hook L911-914), so
  `zsh|dash|ksh|$SHELL|script|flock -c "cd /tmp/x; python3 .plan/execute-script.py"` is admitted
  on both harnesses: the relative-executor rule D2 made exact is defeated by the wrappers D1
  added. The top-level "leading `cd`" branch is dead code because R1 refuses the separator.
- **C3 — medium.** More holes of the same class: `zsh -o pipefail -c '…'` (`pipefail` is read as
  the program), `zsh <<< 'python3 -c x'` (`<` is not an R1 family), `zsh script.zsh`, and
  `fish`/`csh`/`tcsh` absent from the table. The R2 spawn set contains only `sh`/`bash`/`source`,
  so every `zsh`/`dash`/`ksh`/`$SHELL` form relies on the R5 splice walk alone. The missing-table
  branch (guard L1432-1442 **(re-read)**, hook L1362-1371) checks RAW tokens for an interpreter,
  and a spliced string is one raw token, so with the table absent `zsh -c "python3 -c x"` is not
  refused: the "fails closed" claim holds only for an unspliced interpreter.
- **C4 — medium.** The plan-worktree exemption admits the relative executor from any depth under
  `.plan/local/worktrees/`, `_orchestrator` and sub-directories included. With `CLAUDE_PROJECT_DIR`
  unset the hook falls back to the payload cwd (L1263), which makes the root check vacuous.
- **C5 — medium.** Parity gap on a legitimate command. The hook's R4 now refuses every `./pw`
  (L529-537 **(re-read)**) in a root session of this repository, `./pw generate` included; the
  guard admits it (guard L1406-1415 **(agent)**), and CLAUDE.md § Multi-Assistant Support
  prescribes `./pw generate`. CLAUDE.md's standalone-lane table still says the hook's context gate
  "fires only inside a plan context", which D3 made false. The same lift refuses `cat`, `grep`,
  `head`, `tail`, `find` and `ls` in a root session of this repository, as CLAUDE.md asks.
- **C6 — low.** Both implementations also accept the unversioned `{root}/plan-marshall/{entry}`
  candidate outside the resolver's version directory (guard L823, hook L1112). The lane marker
  binds R1-R5 for the whole checkout for 24 h after any `rb-*/progress.md` write, not only the
  lane's own calls.
- **C7 — medium, deployment.** The merged hook is not live on Claude: no cached hook
  (0.1.1920-0.1.1983) references `r5-wrappers.json`, and `.claude/settings.local.json` has no
  `claude_pretooluse` entry **(agent)**. `.opencode/plugin/guard.js` is a project file and is live
  for OpenCode sessions in the main checkout from the merge.
- **C8 — low.** The spec's D1 verify-first clause (decide whether `git grep` and `git -C … grep`
  belong in the refusal table, record why either way) was not decided anywhere: no mention in
  `r5-wrappers.json`, `progress.md`, the landing or the PR body; `pretooluse-enforcement.md` covers
  only the hook's pre-existing R2 arm; `guard.js` has no `git grep` rule **(agent)**.
- **C9 — low.** The D4 base-probe file is untracked in `.plan/temp/base-clone`; deleting the clone
  (an owed operator step) deletes the only copy of the evidence the PR cites by path. The PR body
  says "three self-review fix commits" and lists four.

## Test Audit

- All 17 named test functions exist (plus `test_executor_from_the_repository_root_is_admitted`);
  18 matches across `test_guard_exact_admissions` (8), `test_guard_root_session` (4),
  `test_guard_wrapper_table` (3), `test_guard_documentation_sweep` (3) **(agent)**.
- **Evidence order `test-first` for D1-D3 is not what the run did.** The store timeline shows the
  implementation written before each test (D1: `r5-wrappers.json` 17:40:47, guard and hook
  edits 17:41-17:42, test 17:43:30; D2: guard and hook 18:28-18:33, test 18:41:44; D3: hook
  18:53-18:54:00, test 18:54:39) **(agent)**. The landing's own PR table shows the same thing: in
  every row the passing HEAD log is older than the failing base log (`174703` < `175551`,
  `184532` < `184645`, `185638` < `190305`, `192315` < `192443`). The "fails at base" rows are
  replays in a modified base clone, run afterwards. They satisfy the spec's Done-when ("fails at
  `7ccd9166f`") and the lane's `mutation-after` grade, and should have been labelled that, not
  `test-first`.
- The tests assert the table and the admissions listed; none of them probes a grouping keyword,
  a shell option before `-c`, a here-string or a `cd` inside a splice, which is why the shipped
  rows are green while C1-C3 stand.
- Self-review: 3 rounds closed `budget-exhausted` with four open findings, accepted by the
  operator ("Proceed with the open items reported"). Round 1 found 12, round 2 and 3 fixed more;
  none found C1's siblings.

## Metrics and Anomalies

- Tokens (store, whole tree, input + output + reasoning; cache read separate): input 4,408,300,
  output 235,876, reasoning 245,774, cache read 269,108,224, cache write 0; cost $1.7575.
  Root: 3,618,091 / 193,768 / 115,665 / 239,910,784, $1.4481. Four self-review sub-agent sessions:
  the rest. Cache read is 98.4% of input plus cache. Re-queried by the orchestrator against the
  agent's figures (differences under 600 input tokens). **The landing wrote `total_tokens=unknown`;
  the value was in the store.** The landing's `model` fact is a single scalar; the store has
  `deepseek-v4.1-flash` at variant `high` on all 868 assistant messages (627/70/29/77/65).
- Duration: 2026-10-21T17:34:05Z to 2026-10-22T13:14:15Z, 19 h 40 min, with one 8.35 h gap
  (21:14:53 to 05:35:54) while a `tail -25` call stayed open and no operator message resumed it.
- Operator input: one launch message (17:34:05) and two question answers ("Delete it manually,
  then tell me" 17:56:37; "Proceed with the open items reported" 05:58:40). No model switch.
- **Lane text.** Loaded once through the skill tool at 17:34:05Z from the deployed copy (34.8 k
  chars) and never re-read in 19 h 40 min, across an 8.35 h gap and a server restart. It is the
  pre-#1834 form (`build-classify` present, no `plugin_version`, `effort` or `build_server`);
  #1834 merged at 2026-10-22T06:44:20Z mid-run. Every build used `--execution-mode in_process`.
  Third landing in a row that loaded the lane once (LB-68, LB-78); PLAN-LB-73 D4 owns the rule.
- **Server restart.** A restart at 20:44:07 killed self-review round 2 (the sub-agent returned
  null); it was re-dispatched as "round 2 retry". Neither the landing nor `progress.md` mentions it.
  The tree is five sessions because of it.
- `landing-check`: `complete: false`, `missing_keys` = `total_tokens`, `effort`, `plugin_version`.
  `effort` and `plugin_version` are the keys #1832 and #1834 made required; the lane text this run
  read predates them, so the run could not have written them. `surface_delta` is `unmeasured`.

## Report Contradictions

1. **Guard log.** Section 7 lists three refusals "for this run's sessions". Two are
   (`2026-10-21T17:48:51Z` R2 `cp`, root session `ses_ea078fef6ffe…`; `20:04:25Z` R1 heredoc in the
   "Self-review the D1-D4 diff" child). The third (`2026-10-22T11:14:51Z` R1 `rg … | head`,
   `ses_e9cafd9c2ffe…`) belongs to the PLAN-LB-49 run (a child of its "OpenCode measurement plan"
   session). The log has six lines in the window; the other three are PLAN-LB-78's. **Re-read:**
   `guard.log` L160-166.
2. **"All other rules were kept by the orchestrating session."** The root session made 67
   read-class shell calls (grep 31, tail 16, ls 10, sed 6, cat 2, wc 2) that the guard does not
   refuse and the project's hard rule forbids; it also ran `git worktree add` and `git clone
   --local` into `.plan/temp`, edited the clone's `conftest.py`, ran
   `generate_executor generate` by hand, tried `git clean -ndx` (denied by the permission map),
   and wrote five `pr-thread-reply-thread-{1..5}.md` bodies straight into
   `.plan/local/plans/NO_PLAN/work/ci-bodies/` (11:52-11:54) instead of allocating them. **Re-queried
   by the orchestrator:** the read-class count, the `git clone`/`git worktree`/`generate_executor`/
   `git clean` calls and the five-session tree.
3. **`test-first`** (see Test Audit).
4. **The executor question.** The operator was asked how to delete `.plan/temp/base-clone` because
   the landing said the executor "registers 330 scripts (162 of them under the clone)". The executor
   (mtime 2026-10-22T11:12:21Z) has 330 entries and **0** containing `base-clone`; 162 are under the
   main checkout, 166 under the OpenCode deployed bundle, 2 under `.claude`. **Re-read:**
   `grep -c base-clone` on the executor is 0, and the executor's `MARSHALL_VERSION` is `''`, which
   is why `cleanup restart-check` reports `registry_parity: indeterminate`. The lane misread its
   own 17:53 regeneration (which printed "Found 164 local scripts") as the clone. The agent also
   reports that the clone's `conftest.py` bootstrap (`_ensure_executor_present`) wrote the main
   executor at about 17:54 **(agent, not re-read; the cause is a lead, the empty version stamp is
   the observed fact)**. The clone still exists.
5. **Thread replies.** "`pr thread-reply` expects `pr-thread-reply` but `pr prepare-comment`
   allocates `pr-reply`" is the lane not passing the flag: `ci_base.py` L1491-1497 has
   `prepare-comment --for {reply,thread-reply}` (default `reply`) and `_github_pr.py` maps
   `thread-reply` to `pr-thread-reply` **(agent)**. The suggested "tooling fix" is a lane-text gap.
6. The PR body says three self-review fix commits and lists four; the lane marks the retry nowhere.

## Routing and Merge Behavior

- **Review.** CodeRabbit (required, `quota_limited`): triggers 06:00 and 08:01 rate-limited, 11:32
  accepted, formal review 11:43:25Z on `368d4eaae` with five actionable findings plus one nit, all
  five real and fixed in `eaae96b83`, each thread replied to and resolved, CodeRabbit confirmed
  each; 11:55 and 12:14 triggers produced no review. Sourcery (optional) refused: PR over 150,000
  diff characters. Review facts re-read through `ci pr view` and `ci checks status` **(agent)**.
- **CI/merge.** `verify / verify` 1346 s green on run 39776572150 at `31b5a19e3` (a merge of
  `origin/main`, same tree as `d60b36f8d`); merged without a question under the standing review
  authorization (one handled qualifying review on an earlier head, findings fixed and resolved,
  every other gate green on the merge head). The authorization covers it; the head CodeRabbit
  reviewed (`368d4eaae`) is not the merge head. No collision with the other runs of the window.
- **Collision the gate did not predict:** none at launch (PLAN-LB-79 ran alone after LB-78 and
  LB-49 landed). After landing, the realized footprint overlaps the declared surface of six staged
  specs: PLAN-LB-69 (5 files), PLAN-LB-83, PLAN-LB-84, PLAN-LB-86 (`opencode_runtime.py`), PLAN-LB-51
  (`antigravity_runtime.py`) and PLAN-LB-43 (`test_extension_discovery.py`). Line references in
  those specs are stale and are re-grounded at cleanup.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-79 --status shipped`
- [x] row `pr` stamped — `--set-row PLAN-LB-79 --field pr --value 1835`
- [x] row `landing` stamped — `--set-row PLAN-LB-79 --field landing --value landings/PLAN-LB-79.md`
- [x] row `plan_marshall_plan_id` stamped — `--value lb-79-lb-68-completion` (the sender `rb-lb-79-lb-68-completion` without its `rb-` prefix)
- [x] epic.md: Queue annotation; the "R5/R6 still bypassable" Watch rewritten (not retired);
      model-comparison row; Open Defects for the incomplete landing and the stale executor
- [x] new specs PLAN-LB-88 (guard completion) and PLAN-LB-89 (lane recipes); fold into PLAN-LB-69 D3 and PLAN-LB-73 D4
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-88** (high): the splice walk, effective-cwd-in-splice, fail-closed completeness, the
  `./pw` parity, the `git grep` decision, CLAUDE.md's stale statement. C1-C6, C8.
- **PLAN-LB-89** (medium): the lane's base-sha evidence recipe (no clone, evidence in git or in the
  PR), the thread-reply recipe, and the test-bootstrap executor write. C9, Contradictions 2, 4, 5.
- **Folded:** PLAN-LB-69 D3 gains the six contradiction classes above as named instances;
  PLAN-LB-73 D4's landing-honesty bullet gains the guard-log-by-time-window instance and the
  restart/retry omission.
- **Operator:** C7 (the Claude hook is not installed here); the executor needs `/marshall-steward`
  (empty `MARSHALL_VERSION`); `.plan/temp/base-clone` holds the only copy of the D4 base probe file
  (copy it out before deleting).
