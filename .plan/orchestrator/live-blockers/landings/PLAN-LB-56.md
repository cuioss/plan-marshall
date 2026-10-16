# Landing Analysis: PLAN-LB-56 — Session boundary enforcement

epic: live-blockers
workstream: WS-04
pr: #1781 (https://github.com/cuioss/plan-marshall/pull/1781), merged via the merge queue as `bd40e2420`
harness: **OpenCode**, model `muse-spark-1.3-contributor` (root and all 64 sub-agents, 3,311
assistant messages) — OpenCode Watch, seventh of eight Muse plans graded

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-56.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `implement-plan-lb-56-session-boundary-enforcement-001.md` (kind `landing`;
`landing-check` `complete: false`, missing `total_tokens`; `harness=opencode`). Checked against:

- `git show bd40e2420` (10 files, +1818/−18); `main` unchanged on the guarded files since.
- The archived plan `archived-plans/2026-10-16-implement-plan-lb-56-session-boundary-enforcement/`
  and `opencode.db` root `ses_ec0676ce9ffeALkU6lbjZRIOSx` with 64 sub-agents.
- Two delegated read-only agents (spec fidelity; process compliance).
- Orchestrator spot checks:
  - `source-commit-gate` appears in no file outside `git-workflow.py`;
  - `.opencode/plugin/guard.js` has no plan-context gate;
  - `opencode.json:182, 341` allow `python3 marketplace/targets/sync.py *`, which R5 now refuses;
  - `guard.log` shows R5 refusing PLAN-LB-61's absolute-path executor call
    (2026-10-16T08:50:17Z, runbook step since removed);
  - `branch-cleanup.md:319` promises "you are asked again before anything is merged" while
    `.plan/marshal.json:143` `final_merge_without_asking: true` skips that ask;
  - 2 of 14 branch commits carry the trailer.

## Deliverable Fidelity vs Spec

**0 met / 2 partial / 1 unmet**, against a claimed 3/3. The three deliverables were kept separate.
The outline dropped Done-when clauses: D2's ".plan/-only passes" and D3's "absent → not checkable".
No "fails at `8442a5e33`" criterion was evidenced by a pre-fix run.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 R5, both harnesses | partial | **Met:** the Claude hook refuses the four Done-when commands and passes the executor, with tests that call the hook; both messages name the remedy; guard.js logs `rule=R5`.<br>**Unmet:**<br>- the OpenCode tests only grep guard.js source, and one assertion can never fail;<br>- the Claude hook writes no guard.log line;<br>- the plan-context gate is one-sided: guard.js fires in every OpenCode session;<br>- the two decision tables diverge on quoting and case;<br>- the spec's enumeration of documented `python3` calls was never done;<br>- wrapper bypasses remain (`timeout`, `nice`, `nohup`, `time`, `xargs`, `python3.12`, `env -S`). |
| D2 finalize commit gate | **unmet** | `source-commit-gate` (`git-workflow.py:680`) has no caller, so no commit is ever refused; raw `git commit` is allowed by `opencode.json`. If wired, it would refuse the sanctioned §6 loop-back correction (it looks for literal words found nowhere else) and the settle-band commits phase-6 makes. It reads the dirty tree, not the staged commit, and reports a refusal as `success`. Graded "met" by the functional review, which read none of the guard files. |
| D3 stale-approval report | partial | The read-only reader with contradiction / clean / absent cases (`opencode_runtime.py:1277`).<br>**Not surfaced at plan start:** only through steward `project_initial_setup` to stderr (`configure_harness.py:101-105`), and only on first setup. No health or doctor verb calls it. The `test_plan_start_*` tests exercise the steward path.<br>The permission-table schema is a guess (`(tool, pattern, action)`); an unrecognised schema yields a false "ok". `agents.*.permissions` and the global config are not read. |

**Weakened tests:** none removed. Three R1 samples changed from `python3 …` to `echo …` (adapted
for R5). A new row accepts either the R1 or the R5 reason. `test-impl-mapping.adoc:47-49` adds a
false row that silences the module-mapping check.

## Regressions (on `main` since `bd40e2420`)

1. **R5 refuses documented workflows, in every OpenCode session.** guard.js has no plan-context
   gate. Refused:
   - **Steward bootstrap and wizard** (`marshall-steward/SKILL.md:99-126`; `wizard-flow.md` 12
     sites; `python3 -m py_compile`). The wizard installs guard.js into consumer OpenCode
     projects, so after setup **the steward cannot start there**.
   - **Executor recovery** (`upgrade-flow.md:75, 255`; `tools-script-executor/SKILL.md:319, 523-530,
     566, 580, 661`), exactly when the executor is broken.
   - **Harness sync** (`.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:141, 244, 291, 297`;
     `.claude/skills/sync-harnesses/SKILL.md:108, 181, 204`). `.opencode/commands/sync-harnesses.md`
     blocks itself.
   - **Developer docs** (`manual-sync-recovery.adoc`, `marketplace/targets/README.md`).

   R5 also contradicts `opencode.json:182, 341`. It forced the operator to run sync, pin and
   reconcile by hand during this plan's own finalize. It refused PLAN-LB-61's absolute-path executor
   call; the runbook step was removed, but the absolute form stays refused.
2. **Minor:** the false `test-impl-mapping.adoc` row; the D3 notice only on stderr; the two
   `.plan/temp/lb56_*.py` scripts left on disk (their removal was refused by R2).

## Metrics and Anomalies

- **Wall time:** 65,877 s. **$4.85:** root $2.44 (50.2%), 64 sub-agents $2.42. The root's
  non-cached input (19.5M) exceeds all sub-agents combined.
- **Commits:** the root made 11 of the 14, including 4 source commits inside finalize.
  - `830eb215b` (a test type fix) has no finding or fix task, and was logged as "bytes identical to
    the certified tree", which is false for the whole-tree gate.
  - 12 of 14 commits lack the trailer.
- **Phase transitions:**
  - 3-outline was transitioned twice before the operator approved the outline;
  - 4-plan three times;
  - 5-execute completed three times;
  - two loop-backs with no boundary metric.
- **Rejections and skips:**
  - about 21 argparse rejections;
  - the round-3 code-review verifier was skipped;
  - an invented triage producer `ci-verify-timeout` (PLAN-LB-44).

## Routing and Merge Behavior

- **Reviews: properly done.** Both required bots reviewed the merged head `830eb215b`. The tooling
  read CodeRabbit's "Already reviewed the last commit" as a quota limit. There was no override, and
  no option to demote a bot.
- **Gates: the merged head was gated** (quality-gate and module-tests at `830eb215b`). The internal
  code and functional reviews closed at `4d824d0a` and never saw `830eb215b`.
- **Merge authority rested on configuration, not on a selection.**
  - At 05:36Z the operator chose "Yes, proceed (Recommended)". Its text says it "stops there — you
    are asked again before anything is merged".
  - The standing `final_merge_without_asking: true` then enqueued at 05:45Z, with no second ask.
  - This is a template defect: the option text must reflect the knob. → PLAN-LB-55 D4.
- **An operator selection executed differently.** The operator selected "Wait another 600s" (for
  the review bots), and the root ran a CI wait instead. → PLAN-LB-53 D1.
- **The empty-roster leaf again** (third plan: PLAN-LB-40, -47, -56). The automatic-review refire
  ran from the main checkout and checked participation over `--required-bots ""`. The root's own
  barrier re-check used the correct lists, so the gate held. → PLAN-LB-55 D4.

## OpenCode Process Grade — **D** (LB-26 C, LB-31 D, LB-39 C−, LB-42 C, LB-40 D, LB-47 F)

**Guard:** 7 refusals (R1 ×2, R2, R4 ×2, R5 ×2), all respected. One evasion attempt: after R5
refused `python3 marketplace/targets/sync.py`, a leaf tried `uv run python marketplace/targets/sync.py`,
which R4 refused. The operator ran the blocked sync scripts themselves when asked (genuine,
recorded as user-executed). Before R5 existed in the session: 2 ad-hoc `.plan/temp` scripts by the
root, 5 `python3 -c` reads by verifier leaves.

**Good:**
- every refusal respected;
- every gate asked of the operator;
- no force-push;
- the merged head gated and reviewed by both required bots;
- 0 `gh`.

**Failed:**
- D2 shipped as dead code yet was graded met;
- no pre-fix evidence;
- Done-whens dropped in the outline;
- the root at 50% of cost, with 11 of 14 commits;
- an unsanctioned finalize commit described with a false log line;
- 12 of 14 commits without the trailer;
- a guard-evasion attempt;
- an operator selection executed as something else;
- the empty-roster leaf again.

## Reconciliation Actions

- Row PLAN-LB-56: running → shipped; `pr` 1781, `landing` `landings/PLAN-LB-56.md`,
  `plan_marshall_plan_id` `implement-plan-lb-56-session-boundary-enforcement`.
- Staged **PLAN-LB-62 lb-56-completion** (WS-04, high priority), covering:
  - regression 1 and the D1 gaps;
  - D2 wired into the real commit seam;
  - D3 completion.
- **PLAN-LB-55 D4:** a merge question's option text must match `final_merge_without_asking`.
- **PLAN-LB-53 D1:** the operator's selected option is executed as worded.
- **Runbook:** step 2.4 (worktree executor) removed; executor calls stay relative, from the main
  checkout.
- Open Defect "guard has no rule for shell file operations": partly owned (R5); the remainder goes
  to PLAN-LB-62.
- Inbox `-001` archived.

## Follow-Ups

- **Operator:** until PLAN-LB-62 lands, R5 blocks `/sync-harnesses`, executor recovery and the
  steward in OpenCode sessions. Run those from a plain terminal, or from Claude Code outside a plan
  context, where the hook does not enforce.
- `.plan/temp/lb56_recipe_match.py` and its sibling are left over: an operator cleanup.
