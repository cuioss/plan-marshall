# Landing Analysis: PLAN-LB-88 — A spliced command, a `cd` inside it and the repository's own commands get the same R5 verdict on both harnesses

epic: live-blockers
workstream: WS-04
pr: #1840 (`8e3d57bcd`, base `main`, merge queue)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> **(re-read)** = read again by the orchestrator in git, the CI abstraction or the run's evidence files.
> **(store)** = read from the OpenCode session database, read-only (counts, tool names, command words and times; no
> message text). Nothing below was executed except read-side git, `ci`, orchestrator verbs and read-only queries. The guard
> code itself was NOT re-executed: whether the new rows really close the holes rests on the PR's tests and CI.
> Token usage is out of scope by the 2026-10-23 ruling and is not analysed.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all four sessions **(store)**, 16 h 47 min wall clock, with an
idle notice at 05:01Z that an operator message ended at 05:28Z **(store)**.

All four deliverables are met as the landing states them, with named test rows whose red runs it cites by log and sha (the
test modules exist with the sizes below; the row contents were not read); the PR's own footprint is guard, hook, wrapper
table, new test modules and docs **(re-read)**. The report is accurate where it
could be checked: the one guard refusal it names is the only one in the tree, the two operator questions match the store,
and no file was edited outside the worktree. What holds the grade down: the lane text was loaded once at 15:15Z and not
re-read across a server restart (20:19Z) or the idle notice; the last head (`c5a041315`) carries new logic, the fix for two
major CodeRabbit findings, that no reviewer saw; and the report under-lists its read-class shell calls (it names one `grep`
and one `wc`; the root made two and two plus five `df`).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 Spliced-command walk reads the grammar it claims, or refuses | shipped-as-specified | `guard.js` +462, `claude_pretooluse_hook.py` +614, `r5-wrappers.json` +58, `test_guard_shell_constructs.py` (341 lines) **(re-read: diff stat)**; the landing names grouping rows, `-o pipefail -c`, here-string, script file, `fish`/`csh`/`tcsh`, and the wrapper x construct cross-product are in the tests. Two clauses carry `order=none` (added after the baseline run); the landing says so. |
| D2 `cd` inside a splice is applied; executor admission has no vacuous or over-wide case | shipped-as-specified | `test_guard_cwd_and_worktree_scope.py` (221) **(re-read)**; `_orchestrator` refused, `{plan}` admitted; the payload cwd is never the allow-list root. Both outline decisions (unversioned candidate stays accepted; the lane marker's 24 h whole-checkout scope is intended) are recorded in `pretooluse-enforcement.md` (+153) **(re-read)**. |
| D3 Same verdict on both harnesses for the repository's own commands; absent table refuses a spliced interpreter | shipped-as-specified | `test_guard_documented_commands.py` (136) **(re-read)**; `./pw generate` agrees on both; the `git grep` decision is recorded. |
| D4 The statements about the enforcement scope are true | shipped-as-specified | `CLAUDE.md` changed (1 line) and `test_guard_enforcement_scope_docs.py` (82) **(re-read)**. |

Claimed `deliverables_done=4` of 4; the table agrees.

**Surface.** The spec declared 8 entries; the diff has 14 files (+1971/-202). Added: `doc/developer/opencode.adoc`
(the R2/R4/R5 rows it describes), `_guard_node_harness.py` and several test modules under the declared directory.
Declared but untouched: `deployed-layout.json` and `deployed_layout.py`. The shipped spec is not edited.

## Code Defects and Residue

Documented boundaries the run left (all from the landing, none re-executed): a `git -C ... grep` is refused by the Claude
hook and is outside what the OpenCode guard enforces; a shell spawn is not identified when the wrapper table is missing
(the raw scan still refuses the interpreter); the script-file floor reads up to 1 MiB and does not recurse into a script
a script runs. The previous C1-C3 holes (grouping keywords, options before `-c`, here-strings, `cd` in a splice) are the
ones D1/D2 cover. By the focus rule these residual boundaries are accepted, not staged.

## Metrics and Anomalies

- Duration: 2026-10-22T15:15:04Z to 2026-10-23T08:02:18Z **(store)**. An idle notice at 05:01Z and an operator message at
  05:28Z (the sync instruction).
- Server restart at 20:19:44Z **(store)**. The lane skill was loaded once, at 15:15:07Z, and never again: **not re-read
  after the restart or the idle notice** (PLAN-LB-85 re-read 25 s after its restart).
- Sessions: root plus three self-review sub-agents, all `completed`, none killed **(store)**.
- Sonar: the run read `read_open_issues` five times **(store)** (00:52Z, 04:57Z, 05:31Z, 05:34Z, 06:17Z); the landing
  carries `open_issue_count=0`, `open_issue_rules=none`. The first runbook landing with a measured count written by the
  run itself. The loaded lane text was the pre-#1839 text; the run reached the Sonar read through the operator-selected
  refresh and the merge of `main`.
- `landing-check`: `complete: false`, `missing_keys` = `total_tokens` (out of scope; not a defect).
- Operator questions **(store)**: 2 (00:55Z stale Sonar surface: refresh; 07:16Z cleanup after the main checkout had one
  unstaged `.plan/marshal.json` change); both match the landing.

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed `d4093ea29` and `f058d4e43`; all 4 review threads are resolved **(re-read)**.
  Re-trigger on `c5a041315` at 06:18Z was refused on quota. Sourcery (optional) refused, not gating.
- **Last head unreviewed.** `c5a041315` fixes two MAJOR findings (attached redirection operators bypassed the floor and R2)
  by changing both tokenizers: new logic in security-critical code, covered by CI and the run's own rows only. It merged
  under the standing authorization after one refused re-trigger, without a question. The 2026-10-23 ruling says the plan
  retries the re-review and asks the operator if the quota blocks it; this merge predates the ruling, so it is a datapoint,
  not a breach. Recorded as a Watch.
- CI: `verify / verify` 1254 s green, generate-check green, merged through the merge queue **(re-read)**. One earlier head
  (`55ec1f4a5`) had 16 `TimeoutExpired` under machine load in untouched modules; later heads were green.

## Report Contradictions

1. **Guard log:** exactly one refusal line belongs to the tree (`17:49:48Z` R1, the round-1 sub-agent's `ls-files | head`),
   as the landing says **(store)**. Matches.
2. **Read-class calls:** the landing names one `grep -nE` and one `wc -l`; the root made `grep` 2, `wc` 2 and `df` 5
   **(store)**; round 3 made one `ls`. Small under-report; the landing places the `ls` in round 2.
3. **Files outside the worktree:** none **(store)**: 157 edits in the worktree, 14 under `.plan/temp/`, 11 PR-body writes.
4. Everything else the landing states about questions, sub-agents and the Sonar reads matches the store.

## Reconciliation Actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-LB-88 --status shipped`
- [x] row `pr` stamped — `--set-row PLAN-LB-88 --field pr --value 1840`
- [x] row `landing` stamped — `--set-row PLAN-LB-88 --field landing --value landings/PLAN-LB-88.md`
- [x] row `plan_marshall_plan_id` stamped — `--value lb-88-lb-79-completion`
- [x] epic.md: R5 Open Defect and its Watch retired; the Sonar-read Open Defect retired; Watch for the unreviewed last head
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- None staged. The residual guard boundaries are accepted under the focus rule.
