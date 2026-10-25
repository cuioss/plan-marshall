# Landing Analysis: PLAN-LB-94 — One executor serves every harness

epic: live-blockers
workstream: WS-04
pr: #1861 (`ee00687b8`, merge queue, base `main`, merged 2026-10-25T17:58:57Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`
> or the script execution log. **(store)** = read from the OpenCode session database, read-only (counts, tool names,
> command words, paths, times; no message text). Nothing was executed except the read-only checks named. Token usage is
> out of scope by the 2026-10-23 ruling. The behaviour of the new executor was not re-executed: it rests on the PR's
> tests (32 226 in the final `verify`), green CI and the merged tree read for the retired and the new symbols.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all four sessions **(store)** (root plus three self-review
sub-agent sessions), 8 h 02 min wall clock (2026-10-25T10:29Z to 18:31Z; merged 7 h 30 min in).

All five deliverables are delivered in the merged tree. The landing reports `deliverables_done=4` because it grades D5
against a spec sentence that is false ("each fails at HEAD except the last": two of its five components already passed at
HEAD). That is an error in the spec, mine, and the landing disclosed it instead of inflating the evidence: those two are
reported as forward guards with order `none`, the rest as `mutation-after`. On the behaviour the plan was staged for, the
merged tree agrees with the landing: `_EXECUTOR_TARGET` is gone from the template and survives in the generator only as the
legacy-stamp reader (L3378-3390), `GENERATED_FOR` and `_HARNESS_ROSTER` are in both, `executor_target_mismatch` is in
neither **(re-read)**. The PR is 19 files (+2418/-1108), CI is green, all three review threads are resolved, Sonar `0`
re-read on the PR, and the main checkout is clean **(re-read)**.

Debits: the order of evidence is `mutation-after`, never test-first (the landing says so, no claim of fail-first);
the guard refused three calls and the landing reports one; seven shell read-class calls ran against two disclosed; the last
head merged unreviewed after a logic change (a note only, by the 2026-10-25 ruling); the consumer-project half of D1 was
found by review, not by the spec. The run lived through the bug it fixes: its first question and its first half hour went on the
wrong-harness executor and a missing spec, and two more questions on the `could_not_check` skew answer.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 generation does not depend on the invoking harness | shipped-as-specified, plus one review-found half | `GENERATED_FOR` sentinel, fixed roster in `_INSTALLED_ROOTS` / `_INSTALLED_VERSIONS`, one resolver body in `templates/harness_independent_resolver.py.template`; byte-identity test over 3 targets x 4 ambient signals (`mutation-after`). The consumer-project half (canonical install base) was not in the spec; two tests, order `none` |
| D2 no harness refuses another's executor | shipped-as-specified | `executor_target_mismatch` retired for a target difference; recovery refusal kept for an unreadable executor; one `note:` line on a foreign-install hit; the LB-43 D5 suites rewritten, not deleted |
| D3 mappings and surfaces not bound to an install | shipped-as-specified | suffix from the script's own `/scripts/` segment (the four nested entries follow the tree); `PYTHONPATH` from the resolved root; a surface carries the script path and SHA-256 and a mismatch is ignored; rejection control arm present |
| D4 staleness and version per runtime harness | shipped-as-specified | per-harness version map read by `preflight`, `executor-skew` and steward `upgrade`; empty entry never borrows another harness's version (`fallback_on_empty` added after CodeRabbit) |
| D5 convergent regeneration; no workflow regenerates on a harness difference | met, spec premise wrong | no-change regeneration leaves bytes and mtime; interleaved generations converge; the lane, steward and finalize texts carry no mismatch trigger. Two components passed at HEAD already (forward guards) |

Claimed `deliverables_done=4` of 5; the table puts it at 5 of 5 with a corrected D5 premise.

**Surface.** The spec declared ten entries (three of them HYPOTHESIS); the PR touches 19 files **(re-read)**. Drift beyond
the declared surface: `script-shared/scripts/plugin_registry.py` and `marshall-steward/scripts/upgrade.py` (both named in
the PR body, both readers of the same stamp), `test_executor_version_split_regression.py`,
`test_generate_executor_behavior.py`, `test_marker_free_resolution.py`, `test_preflight_staleness_derivation.py`. The two
production files are the same defect's second readers; the four tests followed the contract change. Drift is explained, not
a surface violation.

## Findings by the orchestrator

- **Questions** **(store)**: four `question` calls (10:30Z, 10:43Z, 10:55Z, 13:44Z) = the landing's four. Q1 reported two
  blockers, a missing spec and a wrong-harness executor; the operator answered "plan did land by now, regenerate and recheck".
  That is the emit-side gap staged as an Open Defect, seen live: the operator started the plan before the ledger land (PR
  #1860) finished, and the lane could not read the spec from the main checkout.
- **Sub-agents** **(store)**: three `subagent` calls (12:25Z, 12:42Z, 13:10Z), three child sessions, all completed = the
  landing's three self-review rounds. No restart notice in the tree; the landing reports none. The rounds found 14, 12 and 11
  items, several major (the executor-skew verdict read the target-independent stamp; flat-sourced nested entries were not
  rewritten; a blank per-harness version fell back to another harness's version); the self-review state is honestly
  `budget-exhausted`, not `clear`.
- **Main checkout** **(store, re-read)**: zero edits outside the worktree (179 worktree edits, 14 under `.plan/temp/`);
  `git status --short` on the main checkout is clean now.
- **Guard** **(re-read)**: `guard.log` lines 198-200 are this session's: R1 at 10:29:48Z (`ls -la .plan; ls -la
  .plan/orchestrator 2>/dev/null; ls -la doc/plans 2>/dev/null`, a lane hunting for the missing spec), R1 at 10:43:24Z
  (`git branch -r --sort=-committerdate --format=%(refname:short)`; the `%(` is likely read as a substitution, a guard false
  positive on a plain git format) and R5 at 17:13:45Z (`python3 .plan/execute-tool.py`). The landing says "one guard
  refusal" and names only the R5. Undercount of two.
- **Shell file operations** **(store)**: `ls` 1, `wc` 1, `tail` 3, `grep` 2 = 7 read-class calls. The landing reports "one
  `grep` and one `tail`". Undercount of five (one of them the refused `ls`). Also one `printenv` and one `date`, not
  read-class.
- **Spoofed identity** **(store)**: none. Every `generate_executor` and executor call carried an empty prefix, against 37 in
  PLAN-LB-90. The conduct the previous landing debited did not recur.
- **Direct generator calls** **(store, re-read)**: the store shows `recover --target opencode`, then `generate --target
  opencode` twice by path at 10:41:57Z to 10:42:37Z, and a `preflight` through the executor notation at 10:55Z. The landing
  says the generator ran by direct path "twice (generate, then preflight)". The count is off by one and the order is
  not as described; the substance (the printed recover command failed with `ModuleNotFoundError: argparse_surface`, the
  repository-source generator was used) matches the epic's open defect.
- **The test suite as a third writer** **(re-read: execution log)**: not reproduced. The log of 2026-10-25 shows 22
  `generate_executor` lines, 21 of them at 07:59Z to 09:51Z (PLAN-LB-90) and one, a `preflight` at 10:55:06Z, the LB-94
  lane's own; none falls inside the LB-94 run's `module-tests` / `verify` windows (11:08Z to 11:16Z and later). The landing refutes the hypothesis as a live defect through the autouse `_plan_base_dir_sandbox` and a new
  assertion that the checkout executor's bytes and mtime are untouched. The earlier LB-90 observation is neither explained
  nor contradicted: LB-94 rewrote the LB-43 D5 suites in the same window, so those may have been the writer. Not verified.
- **Reviews** **(re-read)**: CodeRabbit reviewed `bd2e5bdd5` (16:43Z, Merge Risk Moderate); the re-trigger at 17:16Z was refused
  on quota (two notices). Three actionable findings and one nitpick: a target-scoped empty version read as a broken
  executor (major, fixed in `00be9a82d` via `fallback_on_empty`), a missed `$XDG_CONFIG_HOME/opencode/skills` root (fixed), a
  swallowed test header (fixed), the hardcoded roster (nitpick, answered with a roster-vs-registry drift test; the reason
  given, that emitted bytes must not move when `target_context` reorders signals, is sound). All three threads resolved.
  Sourcery refused on size, optional.
- **Last head unreviewed at merge** (note only, 2026-10-25 ruling): `00be9a82d` carries the `fallback_on_empty` logic fix;
  no review of it exists on the PR **(re-read)**. The merge followed the standing authorization (a handled qualifying review,
  one recorded re-trigger, every other gate green).
- **CI** **(re-read)**: all 11 checks green or skipped (`verify / verify` 1677 s, `verify / gate`, `generate-check`,
  `dependency-review`, `CodeRabbit`; the Sourcery check skipped). The landing reports `verify` green on `bd2e5bdd5` and
  `00be9a82d` (32 224 and 32 226 tests).
- **Sonar** **(re-read)**: `read_open_issues` on PR 1861 answers `confirmed`, 0 open issues = the landing's
  `open_issue_count=0`.
- **Routed builds** (landing, not re-run): the first routed build produced an empty daemon job log; every later build ran
  `--execution-mode in_process`. Same class as the epic's open Watch on routed builds from a lane worktree.
- **Skew check on the flat install** (landing): `executor-skew` answered `could_not_check` with an empty version; the lane
  asked twice and proceeded and recorded. Same family as PLAN-LB-93 D1-D2.

## Open at the landing

- **The merged executor is not the live one.** The main checkout's `.plan/execute-script.py` was regenerated this session
  from the installed `0.1.2007` generator (the pre-LB-94 contract). It carries the old stamp until the harness installs are
  synced and the executor is regenerated once from the merged template: the operator step the spec names after the merge.
  The landing says the executor was regenerated during the run and the harness sync "remains owed". Until then a session of
  the other harness can still meet `executor_target_mismatch` and flip the file.
- **D4's `executor_target` metadata is the constant `any`** by design; it no longer distinguishes harnesses (documented).
- **cwd-reachable tree versus the runtime harness's own install:** the own install still wins; documented, not changed.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1861; `landing` `landings/PLAN-LB-94.md`; `plan_marshall_plan_id` `rb-lb-94-one-executor-all-harnesses`
- [x] epic.md: Queue annotation, model-comparison grade, the executor Open Defect marked shipped with the live-effect residue, a Decision entry
- [x] inbox message `rb-lb-94-one-executor-all-harnesses-001` archived; resume anchor and `queue-view.md` regenerated

## Follow-Ups

- **Operator step:** `/sync-harnesses` (all three), then one regeneration of the main executor from the merged template; only
  then is the stamp war ended in practice. The Claude registry pin (`0.1.2004` against `0.1.2007`) is a separate repin that
  needs the operator's word.
- **Admission:** PLAN-LB-93 no longer overlaps an in-flight plan; `blocking_count` is 0 across 94 specs. Its D1-D2 stand
  (the recovery refusal for an unreadable or absent executor still prints the recover command, and that command must start in
  the flat install), but its premise names `executor_target_mismatch` as the refusal that prints it, and a target
  difference no longer produces that refusal. Re-ground the spec against `ee00687b8` before emitting.
- **The emit side of the ledger read** (high; not staged) stays open and was hit again by this run's first question.
