# Landing Analysis: PLAN-LB-58 — Verification never confirms a result over evidence it did not examine

epic: live-blockers
workstream: WS-01
pr: #1866 (`8c08b6126`, merge queue, base `main`, merged 2026-10-26T22:04:19Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-executed: it rests on the PR's tests, green CI, the
> cited failing logs and the merged diff of `sonar.py`, `derive_gate_bundles.py` and `_test_scope_divergence.py` read in full.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all five sessions **(store)** (one root session, paused by the operator
and resumed, plus four self-review sub-agent sessions), 26 h 16 min wall clock including the pause (2026-10-25T20:20Z to
2026-10-26T22:36Z; merged 25 h 44 min in). The landing message was filed at 08:30Z while the run was paused with the PR open
(`merge_state=open`) and amended after the merge (revision 1, 22:36Z); this analysis reads the amended text.

All four deliverables are delivered and the code does what the spec asked **(re-read, diff of the three core files read in
full)**: `sonar.py` compares the revision the provider reports for the pull request's analysis with the resolved head and
answers `undecidable` with `stale_analysis` (both SHAs), `analysis_revision_unavailable` or `head_revision_unavailable` instead
of a confirmed count; the link checker refuses a Markdown file in file mode; `derive_gate_bundles` takes an architecture-backed
module resolver for a non-marketplace root and still reports an unplaceable path as `unresolved`; and a footprint that adds or
edits a test file now forces `divergence_possible` and a null recommended target, with the left-out populations named. 31 files
(+1888/-130), CI green, three of three review threads resolved, main clean **(re-read)**. The lane read the Sonar provider shape
live twice instead of asserting it, found and fixed two real defects CodeRabbit raised in its own new code, and reported the
rule bend on the operator's "rebase" instruction instead of hiding it.

Debits: D1's "fails at `d17ac5bef`" clause is unmet as written (my spec's error); D3's named population tests are not in the
failing run the landing cites for them; the guard count is understated (4 in the tree against 1 reported) and so are the shell
read-class calls (3 against 1). Credits: the questions (3) and sub-agent (4) counts are exact, no spoofed identity, no
main-checkout edit, the first-run and resumed state are reported honestly, and every CodeRabbit finding was handled.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 Sonar refuses a count over an analysis of another head | shipped, one clause unmet | `_read_analysis_revision` (PR list endpoint, `commit.sha`), `_verify_analysis_revision`, `_resolve_head_revision` (both refs must agree), `_undecidable_fetch`/`_undecidable_read`; scoped to `--pr`. Failing run `python-2026-10-25-203433.log`: 15 failed, all in `test_sonar_analysis_revision.py` **(re-read, log)** |
| D2 the link checker cannot pass a file it cannot read | shipped-as-specified | file mode refuses a `.md`; failing run `pm-documents/python-2026-10-25-213337.log`: 2 failed, 1 passed (the `.adoc` control) **(re-read, log)** |
| D3 the pre-push gate derives a module population off the marketplace layout | shipped; evidence label over-claimed | `architecture_module_resolver`, `module_resolver` seam in `derive_gate_bundles`, Maven `resolve-test-scope` (`_maven_cmd_resolve_scope.py`, +166). Cited run `python-2026-10-25-214025.log`: 1 failed (`test_two_maven_modules_are_the_gate_population`) and 16 errors, all `FileNotFoundError: Module not found: …/_maven_cmd_resolve_scope.py` **(re-read, log)** |
| D4 a green scoped run states what it did not cover, and root guards run | shipped-as-specified | `_is_test_file`, `root_guards_required`, `excluded_population`; failing run `python-2026-10-25-220130.log`: 4 failed **(re-read, log)** |

Claimed `deliverables_done=3` of 4; the fourth is the D1 clause below, not a missing deliverable.

**The unmet D1 clause is the spec's error.** The spec said the second and third Sonar conditions "fail at `d17ac5bef`". The lane
ran its failing tests at its worktree base `cff686064`, and `sonar.py` changed in between (`e40f50aa1`), so no run against
`d17ac5bef` exists. The lane said so, counted 3 of 4, and did not manufacture a run. This is the third time in this epic that a
lane has caught a false "fails at X" statement of mine (LB-95's numeric-order label, LB-96's `runbook_lane resolve`
parenthetical). The cause is the same each time: a fixed SHA or a state taken from outline time that the lane's base does not
share. Specs should say "fails at the worktree base", not a SHA.

**D3's evidence.** The landing lists `test_a_fixture_reactor_reaches_the_population_through_the_architecture_resolver` and
`test_a_path_no_module_owns_is_still_reported` as `test-first` with the `214025` run. Neither name appears in that log. The log's
red is the Maven scope module missing (16 errors) and one older derive test; the named tests were added or upgraded in
self-review rounds 1 and 2 (the landing's own findings say the population proof moved to the production resolver factory in
round 1). So the named population proof is `mutation-after` or later, not `test-first`; the deliverable's behaviour is real and
covered, the label is not exact.

**Surface.** The PR edits files outside the declared surface, all documentation or wiring that the changed contract required:
`execute-task/SKILL.md`, `runbook-lane/SKILL.md`, `pyproject_build.py`, `_build_cli.py`, `verification-feedback.md` (an
operator-directed fix at the third question), `dispatch-walkthrough.md`, `findings-pipeline.md` and the four
`test_fetch_findings_*` / `test_read_open_issues.py` files. Explained in the landing; not a violation. D4's "no file surface"
statement in the spec (a claim the cleanup pass had contradicted earlier) is consistent with the footprint: it is a
`_test_scope_divergence.py` change.

## Findings by the orchestrator

- **Questions** **(store)**: three `question` calls (20:20Z, 01:13Z, 21:47Z) = the landing's three (`executor-skew`
  `could_not_check`; the fourth self-review round and `verification-feedback.md`; the main executor "broken by another session").
  The free-text "pause here" and "rebase from main and continue" are the operator's.
- **Sub-agents** **(store)**: four `subagent` calls (00:03Z, 00:24Z, 00:56Z, 06:25Z), four child sessions, all completed = the
  landing's four rounds. No restart notice in the tree.
- **Guard** **(re-read)**: `guard.log` holds four lines for the five session ids: R1 at 22:01:20Z on 10-25 (a `cat >> … <<'EOF'`
  heredoc, root session, the one the landing reports), and three R1 lines in review children: a `python3 - <<'EOF'` heredoc and a
  `git diff … | grep` pipe at 00:26Z and 00:28Z, and a `git ls-files | head` at 00:57Z. The landing reports one; the other three
  sit in the self-review sessions and are not mentioned.
- **Shell read-class calls** **(store)**: root session `grep` 1, `tail` 1, `wc` 1, plus the refused `cat` heredoc; none in the
  children. The landing reports "one shell `grep`". The `tail` and `wc` are undisclosed.
- **Identity** **(store)**: no `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix on any executor call. No spoofed identity.
- **Main-checkout edits** **(store)**: 0 tracked-file edits outside the worktree `lb-58-verification-truth` (158 worktree edits,
  26 under `.plan/temp`). Main is clean **(re-read)**.
- **Sonar** **(re-read)**: a plan-less `read_open_issues --pr 1866` now returns `undecidable` with
  `analysis_revision_unavailable` (analysis revision blank, head `8c08b6126`). That is the merged gate working as written: a
  merged PR carries no analysis entry to compare. It also means the orchestrator's post-merge "Sonar 0 re-read" can no longer
  confirm a count; for this landing the figure is the lane's own `step.sonar-roundtrip.open_issue_count=0` at its head, plus
  green CI. The lane reports confirmed live reads at `809449a3a` and `6d745640d`.
- **PR threads** **(re-read)**: three review threads, five comments, all resolved. CodeRabbit's first review (`20b7f4cce`, 17:41Z)
  raised two real defects in the lane's own new code (`_git_rev_parse` ran in the process directory instead of the routed
  checkout; `_resolve_head_revision` preferred the local ref and fell back to `HEAD`), both fixed in `809449a3a` with tests. Its
  second review (`809449a3a`, 19:20Z) raised one (a push after the last fetch is invisible locally); the lane answered it with
  the reason (not fixable without a provider call, every locally observable inconsistency fails closed) and the thread was
  resolved.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `20b7f4cce` and `809449a3a` (the walkthrough carries
  `coveredCommitId = 809449a3a`, `kind = reviewed`). The merged head `6d745640d` is a merge of `main` and drew no review after
  the re-trigger; the standing authorization applies, a note only. Sourcery refused on diff size (150 000 characters).
- **Executor broken by another session** **(re-read, execution log)**: at 21:47Z the lane found the main checkout's executor
  unusable and the operator regenerated it (log: a `generate` at 21:47:28Z, 24.9 s). The previous regeneration in the log is
  mine at 16:58Z, after the harness sync, and it worked at the time. What changed it in between is not shown by anything I read;
  the LB-97 lane started at 19:37Z. Recorded as unexplained. Nothing seen since.
- **Routed builds from a worktree** **(re-read, landing §8)**: routed builds answered `exit_code -1` with an empty inner log, so
  every build ran `--execution-mode in_process`. Fifth landing to report it (LB-55, LB-53, LB-82, LB-96, LB-58). The Watches
  condition has been met since the third.
- **Local gate**: whole-tree `module-tests` runs reported two 300 s `pytest-timeout` aborts in `test_harness_shape_guards.py`
  under load, green in isolation (37/37); CI's `verify` (1729 s on the final head) is the authority. Same pattern the Watches
  entry already records.
- **Rule bend (landing §7)**: the operator asked to "rebase from main"; a rebase is forbidden and would need the forbidden
  force-push, so `main` was merged in instead and the landing says so. Correct handling.

## Design effect worth knowing

A footprint that edits any test file now returns `divergence_possible: true` and no recommended scoped target, because the
root-level guards sit outside every module. Every lane that touches a test will be told to run the whole tree. Local whole-tree
`verify` already hits its bound in this repository (1411 s) and the lanes fall back to the split form, so the new rule makes the
split form the normal case for test edits. It is the intended fail-closed direction and CI stays the authority; it is not a
defect.

## Open Items

- D1's `d17ac5bef` clause: not evidenceable; closed as a spec error.
- `execute-task` hardcodes the `build-pyproject` notation for its per-task gate, so a Maven consumer's task-time gate cannot
  reach the new Maven `resolve-test-scope` verb (the finalize gate resolves it dynamically). Medium; not staged.
- A push that lands after the last fetch is invisible to the local Sonar head check; fails closed on every locally observable
  inconsistency, and both call sites push or fetch before reading. Residue, not a defect.
- `commit.sha` is documented as the analysed commit; its meaning under a genuinely stale scan awaits the first real occurrence.
- The post-merge Sonar re-read in the orchestrator's landing procedure cannot confirm a count any more (above).
- The fix is source-only here until the next `/sync-harnesses` (the sync of 2026-10-26 predates this merge).

## Reconciliation actions

- Row PLAN-LB-58: `shipped`, pr `1866`, landing `landings/PLAN-LB-58.md`, plan id `rb-lb-58-verification-truth`.
- Inbox message `rb-lb-58-verification-truth-001.md` archived (revision 1 is the amended text).
- Epic: queue annotation, the lessons-ingest entry marked fixed in source, Decisions entry, model-comparison entry, Watches
  entry updated.
