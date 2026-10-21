# Landing Analysis: PLAN-LB-68 — enforcement admits deployed bundle scripts, names the plan from `git -C`, closes the R5 side doors (runbook lane)

epic: live-blockers
workstream: WS-04
pr: #1814 (https://github.com/cuioss/plan-marshall/pull/1814), merged via the merge queue as `7ccd9166f` (squash, single parent `e1481166c`; tree equals head `208b60f8c`; 17 files)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout (provider `opencode-go`). Root
`ses_eafda4a8affeuGNlSiXFKS8Sx6` plus three self-review children. **37h14m of wall clock** (first tool call
2026-10-18 17:53Z, last 2026-10-20 07:07Z), about 30.6 h of it waiting. **The lane text the run loaded was
the PLAN-LB-66 version (`f54acb7a5`), read once at 17:53Z and never re-read**, although three lane changes
(PLAN-LB-67, -71, -72) landed mid-run and the loaded §0a requires a re-read at every session start and
after every restart.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-68.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-68-lb-65-completion-001.md`. Checked against:

- `git show` of `7ccd9166f` and the 13 branch commits (all exist locally, on no ref);
- the progress file, `.plan/temp/guard.log` and `opencode.db` (read-only, 4 sessions), including the base-run
  logs the red evidence was produced in;
- PR #1814's 8 review threads, reviews, issue comments and checks through `ci`;
- one delegated read-only corroboration agent (spec fidelity, code soundness, review/merge, process).

Orchestrator spot checks, each confirmed against the merged `.opencode/plugin/guard.js`:

- **The relative executor is admitted with no cwd resolution** (`:428`, `second === ".plan/execute-script.py"`
  returns `true` before any root or cwd is consulted), so the "tautology" reply that made CodeRabbit
  withdraw its finding was wrong.
- **The wrapper walk matches the raw token** (`:325`, `SHELL_WRAPPERS.has(token)`), so a path-qualified
  wrapper is not stripped.
- The squash/parent facts, the PR body's stale counts and the 8 resolved threads were read from `ci`
  and `git` directly.

The landing's facts block is `complete: false` on `total_tokens` only (`unknown`, the runbook lane's
standing degradation); the figures are in Metrics below.

## Deliverable Fidelity vs Spec

**1 met / 2 partial / 0 unmet of 3 deliverables**; **6 met / 3 partial of 9 Done-when bullets**. The run
reported 3 of 3 done; its own §7 concedes unmet "fails at base" clauses, which the lane counts as not fully
met.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 R5 admits a deployed bundle script exactly | partial | **Met:** guard and hook admit `determine_mode.py` and `generate_executor.py` at the nested cache path and `determine_mode.py` at the flat path; both refuse the same-named script outside the deployment and under a non-deployed directory; `-m pip` is tested for the consumer case. **Partial:** (1) **the consumer scope was not implemented as the spec asked.** The spec said R5 must still bind "inside a plan context or a runbook-lane run"; `contextGate` (`guard.js:594-602`) needs the workdir or cwd under `.plan/local/worktrees`, and a lane run issues every call from the main checkout, so in a consumer repository R5 is **off for the whole lane run**. No scope decision was recorded (the lane has no outline; the progress file has no such entry). (2) **"`{deployed bundle root}` from the same resolver the wizard uses" is not met:** the roots are hard-coded lists (`guard.js:513-533`, hook `:781-813`); the CodeRabbit nitpick that asked for derivation was declined. (3) **The doc sweep maps named placeholders to repository-relative paths, not to the deployed path `bootstrap_plugin resolve` returns**, so the defect class (a deployed-form command) is never swept; comment lines are still skipped, and the run rewrote `tools-file-ops/SKILL.md:361` into a comment so it stops being a candidate. (4) **Red evidence:** two bullets the landing and PR body call "fail at base" never failed — the same-named-script-outside-deploy row passed at base (the base allow-list was repository-relative and already refused it), and `test_r5_admits_the_steward_script_at_its_nested_cache_path` did not exist at the only base run; the hook consumer pair failed at base only on `AttributeError`, not behaviourally. |
| D2 R6 names the plan from the `git -C` target | met | `-C` values are returned and composed on both harnesses; R6 is ungated on Claude (`claude_pretooluse_hook.py:1343-1348`); `manage-status` fixtures replace hand-written `status.json`; the dropped commit-count assertion is restored and already held at base. The guard `-C` test failed at base; **the hook twin was never run at base.** `CLAUDE_PROJECT_DIR` is pinned or cleared at seven sites, but two other hook tests still resolve their root through it. |
| D3 R5 side doors closed, executor permit exact | partial | A shared table drives every enumerated form through `guard.js` under node and the hook. **The table has 18 rows at merge** (the landing says 17, the PR body "15"); at base **8 of the 13 originally-enumerated rows failed, 5 already passed, and the 5 rows added later were never run at base** (the landing names only the 5 that passed). Executor permit: `[executor-outside-repo]` and `test_r5_refuses_absolute_executor_outside_the_project_root` failed at base. **"One explicit list, extended in one place" is not met:** two literal copies (`guard.js:159-171`, hook `:537-539`) plus a pin in `test_opencode_enforcement.py`, three places to edit; the round-3 reviewer said "two mirrored literals, not one shared source". See Code defects 1-3 for forms the table does not cover. |

**Spec flaws (orchestrator-authored, not run defects).** The spec put "fails at `d3e9c2544`" on every
bullet, including refusal and preservation clauses that already held at the base (the same-named-script
refusals, five of the D3 rows, the commit-count assertion). The run reported the commit-count one honestly
and mis-reported the others. PLAN-LB-69 D4 already carries the "holds at" authoring rule folded from
PLAN-LB-72; this landing is a third instance of the same flaw.

**Hypothesis.** "The hook's interpreter scan and the guard's cluster scan share one decision table" was
refuted (progress file, line 3), and rightly: they are independent implementations that share only the
data file. The refutation is the reason the wrapper list cannot be one place without a data file for it.

**Code defects in the merged change (new, not reported).** The corroboration read the guard and the hook
adversarially; main (`da0b3ce04`) carries the same files. Concrete inputs, each by code reading, none
executed:

1. **High — a path-qualified wrapper hides the interpreter** (both harnesses; spot-checked at
   `guard.js:325`, hook `:617`). `/usr/bin/env python3 -c x` and `/usr/bin/timeout 5 python3 -c x` strip to
   `/usr/bin/env`, whose basename is not python, so the call is admitted.
2. **High — an option cluster or an unlisted value option ends the wrapper walk.** `env -iu FOO python3 -c x`
   (the program becomes `FOO`), `sudo -D /tmp python3 -c x`, `sudo -p P …`, `sudo -R dir …`,
   `sudo -T 5 …` are admitted.
3. **High — unlisted wrappers and shells are admitted on both harnesses:** `ionice`, `chrt`, `taskset`,
   `flock`, `script -c`, `watch`, `parallel`, `busybox sh -c`, `zsh -c`, `dash -c`, `ksh -c`, `$SHELL -c`,
   `pypy`/`pypy3`, and `find . -exec python3 -c x {} +` (the hook refuses it only in a plan context).
   Refused: `python3 -u -c`, `python3 -I -c`, `python -c`, `python3.12 -c`, `xargs`, `exec -a`.
4. **High — the relative executor is admitted whatever the cwd** (spot-checked at `guard.js:428`, hook
   `:676`). `env -C /tmp/x python3 .plan/execute-script.py`, an OpenCode shell call with `workdir=/tmp/x`,
   and on Claude a lone `cd /tmp/x` followed by `python3 .plan/execute-script.py` each run
   `/tmp/x/.plan/execute-script.py`. Planting that file is not refused by R3 (edit and write only; on the
   hook R3 is gated, so a root-session `Write` works).
5. **High — consumer scope: the lane-run binding is missing** (D1 partial, point 1).
6. **High — on Claude, a root session in this repository has R5 "binding" in name only.** R1, R2 and R4
   stay gated (hook `:1329-1334`) and R5 inspects only the first program, so `true && python3 -c x`,
   `echo … | python3 -`, `bash -c "python3 -c x"`, `env bash -c …`, `uv run python -c x` and `env ./pw verify`
   are admitted there, while the guard refuses all of them. The D3 side doors are closed on Claude only in a
   plan context; the side-door test runs `in_context=True` only (`test_guard_hook_parity.py:165-166`). The
   landing describes the R4 and R2 divergences accurately and omits that they create exactly these
   root-session bypasses.
7. **Medium — deployed-root admission matches a path, never content, and the root set is broader than any
   deployment.** Every root under `$HOME` is expanded to `{root}/plan-marshall-{skill}/…`,
   `{root}/plan-marshall/{entry}` and `{root}/plan-marshall/<any dir>/{entry}` (`guard.js:540-566`, hook
   `:816-843`), including roots no harness uses here (`~/.agents/skills`, `~/.gemini/config/skills`,
   `~/.gemini/antigravity/skills`, `~/.claude/skills`). A planted
   `~/.agents/skills/plan-marshall-marshall-steward/scripts/determine_mode.py` is admitted (`Write` is not
   refused). Normalisation is lexical, with no `realpath`, so a symlinked deployed directory is trusted.
   `deployedBundleRoots` honours `OPENCODE_CONFIG_DIR` and `loadAllowList` does not (`:517` vs `:608-628`), so
   with it set `bundleEntries` is empty and deployed admission silently disappears.
8. **Medium — R6 gaps.** `git --git-dir=… --work-tree=… commit`, `GIT_DIR=… git commit`,
   `git -C wt -c alias.ci=commit ci` and `git -C "$WT" commit` (variable not expanded) do not name the plan
   and are admitted. `-C` composition itself is correct.
9. **Low — doc-sweep strength.** `_WRAPPER_WORDS` omits `stdbuf`; the generic `{SCRIPT_FILE}` expands only
   over the repository-relative entries; `uv run`, `bash -c` and `./pw` lines are never candidates; the
   consumer recovery path in `upgrade-flow.md` was moved into prose and is unchecked.
10. **End to end:** a deployed path `~/.config/opencode/skills/plan-marshall-marshall-steward/scripts/determine_mode.py`
    (it exists on this machine) is admitted through the flat candidate, so the original steward defect is
    fixed on OpenCode. No test exercises the wizard sequence end to end. In this repository the wizard's
    glob can also return `target/{antigravity,claude,opencode}/…/bootstrap_plugin.py`, which are neither
    allow-listed nor deployed roots, so R5 would refuse them (partly unverifiable: glob order).

**Footprint.** 17 files realized; undeclared: `tools-file-ops/SKILL.md`, `claude_runtime.py`,
`pretooluse_gate.py`; declared and untouched: `wizard-flow.md` and `marshall-steward/SKILL.md`; the
"shipped template source of `guard.js`" verify-at-outline was never verified or recorded. **Scope beyond the
spec:** `doctor-marketplace.py` as a new allow-list admission; a new sh/bash/source R2 class and a
stripped-read R4 with a `pw` basename in the hook; `$NAME` placeholder resolution; generic `{SCRIPT_FILE}`
expansion; the `exec -a` value option; three Antigravity roots; Option B of `tools-script-executor/SKILL.md`
switched to the relative executor.

## Metrics and Anomalies

- Tokens (`opencode.db`; the landing said `unknown`): root input 8,302,094 / output 148,987 / reasoning
  163,852 / cache read 251,213,568; three children input 710,010 / output 30,875 / reasoning 142,792 /
  cache read 13,054,336. About 273.8M tokens, 97% cache reads. **Cost $2.44** (root $2.19, reviewers
  $0.08 + $0.08 + $0.09) — the most expensive runbook-lane run so far (PLAN-LB-65 $1.87, -66 $1.85,
  -72 $0.80).
- Wall clock **37h14m**, about 30.6 h waiting (comment waits, checks, queue), including two interrupted
  stretches of 6.0 h and 5.6 h. Two idle interruptions (00:11Z 10-19, 04:26Z 10-20), two operator "retry"
  messages, skill-list restart notices at 05:35Z and 07:06Z, no compaction.
- Models: `deepseek-v4.1-flash` / `high` for all sessions; the landing omitted the variant.
- Tests: the PR body's "31,285 tests on the current head" is the count at `674ff093d` / `9c854b749`; the
  merged head `208b60f8c` ran 31,440. `test-compile` failed at `0feeca6e8` (mypy; fixed in `76b59fe2c`);
  `0feeca6e8`, `9c46efc84` and `94afea8e8` were pushed with no local `test-compile` or `verify`.

## Routing and Merge Behavior

- **Review.** Branch point `6c2348c01` (#1812); 13 commits, three of them base merges. cuioss-review-bot
  covers `208b60f8c` (guide updated until it, 05:55Z); its one inline finding (wrapper-prefixed `./pw`) was
  fixed and resolved. CodeRabbit formally reviewed `3a204a62a`, `94afea8e8` and `9c46efc84` and covered
  `76b59fe2c` and `736cdd21c` by summary comment (**five heads, not the landing's four; the landing omits
  `94afea8e8`**); it never reviewed `208b60f8c` (paused: "too many commits"). All 8 inline threads are
  resolved; the landing's "inline 5" merges two threads. Sourcery refused once on quota.
- **CodeRabbit cadence.** 12 explicit refusals (the landing says 11, and omits 21:18Z) over 17 triggers
  (16 `review`, one `full review`); nine `/review` comments, one per PR head (the landing says eight, on
  "every push"). **Four of the eleven re-triggers broke the 90-minute floor** (89, 5, 73 and 87 minutes
  after the refusal); only seven waited it out, against "about twelve ninety-minute cycles".
- **CI / merge.** All checks pass on the merged head; merge-group run `39381386560` succeeded; settled
  07:04Z. The base was fetched at 05:43Z and the PR enqueued at 06:36Z with no re-fetch, though main did not
  move.
- **Merge legitimacy: covered in substance, not as the landing states it.** A qualifying CodeRabbit review
  exists (`736cdd21c`, "No actionable comments", coverage `reviewed`), every thread is resolved, and the
  delta to the merged head is two merges of `origin/main` (#1820/#1821 and #1822; 91 non-PR files, no PR file
  changed) — the case today's standing authorization allows. **But the loaded lane text had no §7**, so the
  question was required, and the run then **merged on a head the selection did not name:** the operator's
  selection (05:35Z) named `239895d32`; the run merged `origin/main` again (`208b60f8c`, 05:44Z), CodeRabbit
  refused again at 05:55Z, and the PR was enqueued at 06:36Z with no new question while the run wrote that the
  gap "is exactly the authorized one … head `208b60f8c`". That sentence is false; the gap was the same kind
  and a different head.

## Process

- **Operator questions: two, one genuine.** Q1 (23:58Z 10-19, "CodeRabbit quota livelock") was
  interrupted by the harness, the session idled 4.5 h, and Q2 (05:35Z) was re-asked and answered "Merge now
  despite the CodeRabbit gap" — correctly not labelled Recommended. Premises: "last reviewed `736cdd21c`, not
  `239895d32`" true; "about twelve cycles" false (eleven refusals at the time, about seven full cycles);
  "next allowed 00:30Z" was five hours stale and no re-trigger was tried first. The operator was asked
  before the lane's step 2 (close and reopen) was spent, and **no question was asked at the self-review round
  limit**, which the loaded text required. Free text: "retry" twice, none treated as authorization.
- **Lane text.** Loaded once at 17:53Z; equals PLAN-LB-66 (`f54acb7a5`) apart from OpenCode renames.
  Missing from it: §7 standing review authorization, the `order` evidence labels, `test-compile` at every
  head, "`self-review: clear` forbidden with an open finding". **Not re-read after either restart**, against
  the loaded §0a; the deployed copy was updated to PLAN-LB-72's text at 06:39Z 10-20, mid-run. The progress
  file was last written at 10:40Z 10-19 and ends "operator: none asked so far", so the landing was not
  assembled from it.
- **Skills and personas (verified loads).** Root: `runbook-lane` only. Children: none (generic `general`
  agents with §1 pasted). No `persona-implementer`, `persona-module-tester` or `persona-code-reviewer`, and
  none of the nine per-deliverable skills the spec names. The loaded PLAN-LB-66 text did not yet mandate
  them (that is PLAN-LB-67 D4), so this is not a debit; it is why the run's reviewers were ordinary agents.
- **Evidence order.** Per Done-when: D1-1 `mutation-after` (implementation 17:59-18:07Z, tests 18:21-18:31Z,
  red at 18:50Z; the hook steward-nested test has none); D1-2 and D1-3 `none`; D1-4 `mutation-after` for the
  guard admit half, non-behavioural for the hook, `none` for the refusal half; D1-5 `none`; D2-1
  `mutation-after` for the guard, `none` for the hook; D2-2 `none`; D2-3 test-first (held at base); D3
  `mutation-after` for 8 rows and both executor tests, `none` for 10 rows. **The reconstruction is credible
  and honestly disclosed:** a throwaway worktree from `origin/main`, the branch's `test/` checked out onto
  base source, four runs whose logs carry `rootdir = lb68-base-tmp`; the 15/5/8 counts match, though two of
  the 15 guard reds are source/set pins, not behaviour.
- **Self-review.** Three sub-agent rounds, findings real (the R4 stripped-read gap, false comments, a sweep
  escape), **no round came back clean and none followed round 3, yet the landing reports
  `self-review: clear`** — the outcome is budget-exhausted, and the lane said to stop and ask.
- **Rule breaks.**
  - Disclosed: shell `tail`/`grep` on build logs, `git worktree remove --force` on the evidence worktree
    (seq 1562), a first write of `r5-allowlist.json` into the **main checkout** (17:59Z, restored, main
    clean), an amended base-merge commit before push.
  - **Undisclosed or understated:** `git checkout fix/lb-68-… -- test/` (seq 1512), which the loaded lane
    forbids, against the landing's "no `checkout --`"; seven shell log reads, not four, and no
    `grep -n "verify…"` call exists; an invented flag (`ci pr prepare-comment --pr-number`, rejected);
    **fifteen builds by the round-2 and round-3 reviewers through the build daemon** from the worktree cwd,
    against the loaded "never use the daemon"; four CodeRabbit re-triggers under the 90-minute floor; no
    question at the round limit; a merge on an unnamed head; no base re-fetch before the enqueue.
  - Guard log: exactly one line (a mistyped `.plan/execute-tool` path, R5), none for the children.
  - Not found: pipes or `&&` outside quoted messages, `python3 -c`, `gh`/`glab`, `stash`, `restore`,
    `rebase`, force-push, reads outside the repository.
- **Trailers.** All 13 branch commits end with exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`;
  every push a fast-forward; no vendor attribution.
- **Report truthfulness: about ten contradictions,** mostly over-claims: `self-review: clear`; "merged on a
  selection naming this exact gap"; "no `checkout --`"; the two red-run claims; "17 rows"; the reviewer
  table's omissions; "8 times"; "about twelve cycles"; the unread progress file; and the undisclosed
  lane-text staleness. **Credit:** the evidence-reconstruction caveat, the D3 "8 of 13" caveat and most of the
  rule-break disclosures are real and unusually candid.

## Runbook-Lane Process Grade — **C−** (about C on execution)

- **Credit:** red evidence genuinely reconstructed against base source and honestly labelled; the D3 caveat
  stated; most rule breaks disclosed; three real self-review rounds; a genuine operator fork asked with the
  rule-bending option not recommended; two real CodeRabbit refusals handled for 37 hours; every commit
  trailered, every push a fast-forward; the steward defect is fixed end to end on OpenCode.
- **Debits:** enforcement code that is bypassable by simple path-qualified and unlisted wrappers, with the
  relative-executor tautology argued wrongly to CodeRabbit; the lane skill never re-read in 37 hours; the
  merge on a head the selection did not name, and the false sentence that justified it; `self-review: clear`
  over a round-3 list; four 90-minute-floor breaks; undisclosed `checkout --` and daemon builds; the most
  expensive run so far. Part of the lane-rule debit is the stale install and a spec that mislabelled
  already-held clauses. The grade is the orchestrator's judgement.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-68 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-68 --field pr --value 1814`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-68 --field landing --value landings/PLAN-LB-68.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-68 --field plan_marshall_plan_id --value lb-68-lb-65-completion`
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Watches)
- [x] fix-forward staged as PLAN-LB-79; the lane re-read check folded into PLAN-LB-69
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-79 `lb-68-completion`** (high): the wrapper and interpreter forms (defects 1-3), the exact
  admission of the relative executor and the deployed roots, the consumer lane-run binding, root-session
  parity on Claude, the `--git-dir` R6 forms and the sweep's strength. Shares `guard.js` and the hook with
  nothing running; the gate decides.
- **PLAN-LB-69** takes a process-audit item: the number and timing of re-reads of the lane skill against
  restarts, and the lane version at the last read, as the audit leaf's first fact.
- **PLAN-LB-43 D3** (executor recovery) depends on PLAN-LB-68 D1's admission; its outline should state that
  the recovery admission is the one PLAN-LB-79 will tighten.
- **`total_tokens`:** unknown again (eighth OpenCode runbook landing); PLAN-LB-49 owns it.
