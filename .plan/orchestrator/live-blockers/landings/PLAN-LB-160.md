# Landing Analysis: PLAN-LB-160 — Follow-ups from the PLAN-LB-158 landing: a change-ledger row that records every path, a finalize commit whose missing row is seen, and the stale statements beside it

epic: live-blockers
workstream: WS-01
pr: #2012 (https://github.com/cuioss/plan-marshall/pull/2012)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-160-follow-ups-change-ledger-paths-finalize-record-npm-canonical-docs-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

Merge commit `b296b4726b73db5494c4ad96cdd9a57cad48d8b3` (squash; one parent `97d7a9f009495cc6b5be5ac10d26e5c49a63ac3b`, the ledger land of PR #2013), read with git; PR #2012 `merged`, merge-group run `44204502356` `success`, read through the CI abstraction. The diff is 19 paths, all modified: 1 ADR, 14 files under `marketplace/bundles/plan-marshall/skills/` (scripts, skill documents and standards), and 4 test files (`git diff --name-status --no-renames`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the `cwd-policy` document family states what the merged code does | shipped-modified | The three statements are narrowed (`cwd-policy.md:34`, `marketplace_paths.py` docstring, a new block in `doc/adr/002-…adoc`). Two files the spec did not name were edited: `marketplace_paths.py` (docstrings and comments only) and the ADR; the lane disclosed the ADR extension and its reason (the ADR carries the same exclusivity statement). The three edited documents still disagree on the main-resident set (L3-4). |
| D2 — a merge row records every path, a rename's old path included | shipped-as-specified | The merge branch enumerates with `--no-renames` (`git-workflow.py`, the first-parent branch); the non-merge branch, `--root` and the NUL split are unchanged. Pinned by `test_a_merge_commit_records_both_paths_of_a_renamed_file`, whose failure at the base depends on the host's `diff.renames` (L2-2). |
| D3 — a lossless path list | shipped-as-specified | `--changed-paths-file` (NUL-separated, `surrogateescape`) added to `append`; the comma form is unchanged; supplying both is refused (`manage-change-ledger.py:212-236`, re-read). The lane's shape choice (a file git writes with `--output`, because a typed list cannot be read back out of a shell that renders NUL as a space) is stated and reasoned. Two minor defects below (L3-2, L3-3). |
| D4 — a `6-finalize` commit whose row failed is visible to the caller | shipped-modified | Branch (a): the callers are told to read `ledger_recorded` and the docstring and skill stop claiming the boundary surfaces it. Not every post-commit return carries the outcome (L3-1), and the "do not report the step cleanly done" clause has no mechanism (L1-2). |
| D5 — npm's chained `verify` carries the canonical identity on every hop | shipped-as-specified | `_build_shared.py:115` emits `--canonical {name}` per hop and `_npm_cmd_discover.py:379` passes `verify`; `build_chained_commands` has this one caller. |
| D6 — tests pin D2–D5 and the stale comment | shipped-modified | The new tests exist, and the stale comment now names the three row owners. The phase-5 test change updates a helper that mirrored the command, not a doc-contract assertion, because the test never carried one (L1-1). Three tests are weaker than the deliverables claim (L2-2 to L2-4). |

Surface drift: the lane edited `doc/adr/002-…adoc` (disclosed) and `marketplace_paths.py`, neither named in the spec's Expected Surface. Every other declared path was touched. The two extra files are explained as D1 document-family edits.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`), and the orchestrator re-read every `checked` point recorded below at its line, plus the D4 gate site. The reading is by reading, no build, no test run, no write: what only a run could show is `not_shown_by_reading`.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with PLAN-LB-161's, which was read in its own leaf in the same drain.
- **Verdict:** layer 1 findings (two minor); layer 2 findings (three minor, three not shown by reading); layer 3 findings (four minor, no blocker, no major).
- **Re-read by the orchestrator:** `git-workflow.py` `cmd_commit` at the merge (return paths, `ledger` handling) and at the base `6b9a879` (success path); `phase-5-execute/SKILL.md` Step 10a; `manage-change-ledger.py` `_read_changed_paths_file` and the `append` refusals; `manage-change-ledger/SKILL.md` § append; `phase-6-finalize/SKILL.md` § 5f(b); `_cmd_lifecycle.py` boundary guard site; the three resident-set statements (ADR-002, `cwd-policy.md:36`, `marketplace_paths.py`); the `test_phase5_change_ledger.py` diff; the rename and finalize-row tests. **Not re-read:** `build_chained_commands`' single-caller sweep and `_build_shared.py:115`, the `test_append_*` bodies, `_ledger_core.py:119`, the first-parent pattern in `_references_core.py` and `analyze-logs.py`, and the host-dependence of git's `--output` open order.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's third HYPOTHESIS said `test_phase5_change_ledger.py` pins the `-z` and `--root` text of the changed-path command. At the base its helper ran `git diff-tree --no-commit-id --name-only -r {sha}` with neither flag and split on lines, and the file reads no document. The lane's "third hypothesis confirmed" does not hold | checked | refutes | `test_phase5_change_ledger.py:75` (the diff's removed lines, re-read) |
| L1-2 | D4(a) asks the caller not to report the step as cleanly done while the row is missing. In the `5f(b)` flow the step recorded its terminal `mark-step-done` before the dispatcher commits, so the clause has no outcome value or field to act on; the document repeats it without making it operational | checked | refutes | `phase-6-finalize/SKILL.md:1376-1379` (re-read) |
| L1-3 | The spec's second HYPOTHESIS (no consumer refuses on a finalize row's absence) is refuted for the branch because the `5-execute` boundary re-reads finalize rows after a loop-back; the docstring now says so. The guard is gated on `--completed 5-execute` and the end-marker check covers every worktree-branch commit (`_cmd_lifecycle.py:1792`, re-read); the loop-back re-entry itself was not read | not_shown_by_reading | none | `git-workflow.py:1097` |
| L1-4 | The OBSERVED premises match the base diff | checked | confirms | `git-workflow.py:1054` |

Both refuted premises are this orchestrator's authoring: the first was labelled HYPOTHESIS (verify-at-outline) and the lane marked it confirmed; the second is a Done-when clause written without checking that the step has any state left to change. **For later specs:** a HYPOTHESIS about what a test file pins names the file and symbol that confirms it, and the staging read opens that file; a Done-when that says "do not report X" names the field that carries X.

**Layer 1 verdict:** findings — 2 (L1-1, L1-2, both minor); not shown by reading — 1 (L1-3)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D2 | `git-workflow.py:1054` (`--no-renames`) | `test_a_merge_commit_records_both_paths_of_a_renamed_file` | the test pins its premise with `-c diff.renames=true` on its own git call only (`test_source_commit_gate_commit_path.py:710`, re-read); the production enumeration inherits the host config, so on a host with `diff.renames=false` the base also records both paths and the test does not fail there (L2-2, minor) | checked |
| D3 | `manage-change-ledger.py:101-129, 212-236` | `test_append_change_reads_a_nul_separated_path_file_losslessly`, `…_comma_form_still_stores_what_it_stored`, `…_refuses_both_path_inputs` | the refuse-both test asserts only `status == error` and that no ledger file exists, and the base's unknown-flag rejection is also an error with no row, so it may pass at the base for the wrong reason (L2-3, minor, whether the base's error is parseable shown only by a run); the round-trip file is written by hand, not by `git --output`, and the non-UTF-8 `surrogateescape` path is untested | checked |
| D4 | `git-workflow.py:1254-1320`; `phase-6-finalize/SKILL.md:1370`; `architecture-refresh.md:278` | `…_a_post_commit_push_refusal_still_reports_the_ledger_outcome` fails at the base (the base returned the push and gate refusals with no ledger field, `git-workflow.py` at `6b9a879`, `:1240-1255`, re-read); `…_a_finalize_commit_whose_row_cannot_be_written_reports_it` **cannot** fail against the base, which already set `ledger_recorded` and `ledger_error` on the success path (base `:1256-1272`, re-read), so it pins existing behaviour; the caller instructions at `phase-6-finalize/SKILL.md:1370` and `architecture-refresh.md:278` are pinned by no test, only by prose assertions on the docstring and the skill (L2-4, minor) | checked |
| D5 | `_build_shared.py:115`; `_npm_cmd_discover.py:379` | `test_chained_verify_carries_the_canonical_identity_on_every_hop` fails at the base; whether the existing npm tests pass, and whether `_marshalld_verifier.py` (which reads a canonical) is affected, needs a run or a further read | not re-read here; leaf: checked | not_shown_by_reading — 1 |
| D6 | the test files | the lane's counts: 12 intended failures at `6b9a879`, 29 088 passed at `686094a`, 34 132 in `verify` | not shown by reading | not_shown_by_reading |
| unexplained files | `marketplace_paths.py` and `doc/adr/002-…adoc` fit D1; `phase-6-finalize/SKILL.md:1370` and `architecture-refresh.md:278` fit D4(a) | — | none unexplained | checked |
| lane report | the lane lists two residue sites for the rename-following pattern (`branch-cleanup.md:2077`, `_footprint_resolver.py:410`); a sweep also finds the `{sha}^1 {sha}` pattern in `_references_core.py` and `analyze-logs.py`, not mentioned, and whether they follow renames was not read | — | the residue list is incomplete (not shown by reading whether those two are defects) | not_shown_by_reading |

**Layer 2 verdict:** findings — 3 (L2-2, L2-3, L2-4, minor); not shown by reading — 3

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `git-workflow.py:1243, 1254, 1259, 1314-1319` | `git rev-parse HEAD` fails after a successful `6-finalize` commit, so `commit_hash` is `None` and the row is never attempted | with `--push` the error goes through `_with_ledger_outcome(err, {})`, which adds nothing, so no `ledger_recorded` rides it; without `--push` the success return carries `ledger_recorded: false` with no `ledger_error` and `commit_hash: None`, so the WARNING the caller is told to log can name neither. This contradicts `SKILL.md:205` ("rides on every return made AFTER the commit exists"). Re-read at the merge. Fails visible, not silent (a `false` flag is returned), and `rev-parse` failing right after a commit is a rare repository fault | minor |
| L3-2 | `phase-5-execute/SKILL.md:812-819` | the documented Step 10a form reuses one fixed path (`{plan_id}-changed-paths.nul`) for every deliverable, never removes it, and does not say to check git's exit status before the append; the `diff-tree` call fails before git opens `--output` (for example a bad `-C` path) | the previous deliverable's file stays in place and `append --changed-paths-file` stores those paths against the new SHA with `success`; when git fails after opening the file it is truncated and an empty list is stored, which the verb accepts (`manage-change-ledger.py:120-129`). Re-read the document and the verb; when git opens `--output` is git-internal and not shown. The git failure itself is visible to the agent that ran the command | minor |
| L3-3 | `manage-change-ledger/SKILL.md:246`; `manage-change-ledger.py:125, 227-231` | an unreadable `--changed-paths-file` | the document says it is "refused with `changed_paths_file_unreadable`"; the code returns code `invalid_input` and carries that token only as a message prefix, and the message always quotes the non-merge `diff-tree` form even for a merge row. Re-read both. The document also says "is a new flag", which is transitional wording | minor |
| L3-4 | `doc/adr/002-…adoc:200`; `cwd-policy.md:36`; `marketplace_paths.py:16-19` | a reader looking up the main-resident set | the ADR block says "the six corpora above remain the main-resident set" (and its six include `orchestrator`), `cwd-policy.md` says "a bounded set of five" and that `orchestrator` is not a member, and the `marketplace_paths.py` docstring lists six that include `harness/` and not `orchestrator`. All three were edited in this landing and still disagree. Re-read at the three sites | minor |

**Layer 3 not shown by reading:** the leaf marked as not shown: whether the base's argparse rejection is a parseable error TOON (L2-3); when git opens an `--output` file relative to a failing `-C` (L3-2); that the `5-execute` boundary re-runs over finalize commits on re-entry (L1-3). The orchestrator adds that it did not read `_cmd_lifecycle.py` past the guard site.

**Layer 3 verdict:** findings — 4 (L3-1 to L3-4, all minor, no blocker or major); not shown by reading — 3

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| persona-plan-marshall-agent | `git -C` only on a tree handed in through `--project-dir` | conforms | `git-workflow.py:1054`; `manage-change-ledger.py:123` resolves a relative file against the process cwd and every documented example passes an absolute path |
| persona-plan-marshall-agent | plain `git` in a phase-5 cwd-pinned context | deviates | `phase-5-execute/SKILL.md:817` and `execution.md:578, 590` keep `git -C {worktree_path}`; a pre-existing form the landing retained |
| CLAUDE.md § Workflow Discipline | one command per Bash call in documented procedures | conforms | `phase-5-execute/SKILL.md:812-819` puts `mkdir` and `git diff-tree` in separate blocks |
| CLAUDE.md § Documentation Standards | no dates, versions or history; current state only | deviates | `manage-change-ledger/SKILL.md:246` says "is a new flag" (transitional); the `git-workflow.py:1150` docstring cites the plan deliverable "D4" in production code. No dates or changelogs were added |
| CLAUDE.md § Documentation Standards | AsciiDoc `xref:` cross-references | deviates | the ADR-002 block cites `cwd-policy.md` as a backticked path, not `xref:`; the file's existing References section uses the same style |
| pm-dev-python | typed signatures; no bare `except`; no mutable default | conforms | `_read_changed_paths_file(raw_path: str \| None) -> tuple[list[str] \| None, str \| None]`; the new handler catches `OSError` only; `cmd_commit(args)` is untyped but pre-existing |
| persona-module-tester | tests follow AAA | conforms | the new tests arrange, act once, then assert |
| persona-module-tester | no assertion on prose that is not a contract | deviates | `test_the_docstring_no_longer_claims_the_boundary_surfaces_a_finalize_row` and `test_the_commit_changes_flow_tells_the_caller_to_read_ledger_recorded` assert wording; the spec's D6 asked for the first |

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none; out of scope under the ruling of 2026-10-23, so no defect.
- Builds: 16, none degraded, none killed, none retried; one waited 686 s behind another job of the same worktree (per-worktree serialization, not a fault). Per-head runs are the lane's account and were not re-run here.
- Anomalies: the main checkout's executor (0.1.2149) refused the resolve-supplied build command because its embedded surface lacked `--canonical`; the lane asked, the operator selected "Regenerate the executor, then continue", and the regeneration ran through `generate_executor` (342 scripts). This is the debt the epic already records for `--canonical`, surfacing in a lane. The lane read build log files from `/home/oliver/.plan-marshall/marshalld/job-logs/`, outside the repository root, and disclosed it as a deviation; no credential file, config directory or environment dump was read. Not corroborated here: the session store and `guard.log` were not read, so "no guard refusal" and the disclosed rule check are the lane's account.
- **The orchestrator's own leaf:** the three-layer leaf disclosed that it once used git's `grep` subcommand against the merge commit to find line numbers, which this repository's file-operation rule forbids. It read the object store only and wrote nothing; every later lookup went through `architecture search` and Read. Recorded so it is not lost, not a finding against the landing.

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 1 body finding and 1 handled. `runbook_lane review-gate --pr-number 2012` on the merged head returns `unresolved_review_threads: 0` and `review_body_findings_total: 1`, which agree. `review_body_findings_handled` is **re-verified**: the lane's progress file holds exactly one `finding:` line (`coderabbit inline inline-1 — 68efebb`), matching the claim. The bare re-run reports `handled: 0` and `merge_allowed: false` only because it holds no dispositions input, which is the gate working. CodeRabbit (required, `quota_limited`) reviewed `fa60436` with a readable coverage marker, both its findings (one inline thread, one outside-diff body finding) were fixed in `68efebb`, and on the merge head it published a rate-limit notice; the standing authorization applied on the lane's account (not re-read here). Sourcery (optional) refused on its own quota twice and does not gate.
- CI/merge: merged through the merge queue (`b296b47`, merge-group run `success`); the base merge `107928a` is the lane's account.
- Sonar: `sonar_open_new_issues: n/a` — Sonar is not enabled for this project (ruling of 2026-10-28), so no figure was collected or required.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-160 --status shipped`
- [x] row `pr` stamped — `2012`
- [x] row `landing` stamped — `landings/PLAN-LB-160.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-160-follow-ups-change-ledger-paths-finalize-record-npm-canonical-docs` (from the sender)
- [x] epic.md narrative reconciled against the queue rows
- [x] Watches opened for the minors and the residue; no Open Defect (no blocker, no major)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **Layer-3 minors (reported to the operator at once, not fixed, not staged).** L3-1 to L3-4 above; the focus rule is high and blocking only and none fails open on an observed input, so they are one Watch and ride a later plan only if it edits the same files.
- **Consumer projects.** `--changed-paths-file` is a new flag on the `append` verb's argument surface: every consumer project regenerates its executor on upgrade before the documented Step 10a command works there, and on this repository `/apply-changes` is owed (the debt the epic already records for `--canonical`).
- **The rename-collapse class outside this plan's surface** — `branch-cleanup.md:2077`, `_footprint_resolver.py:410`, and two more sites the lane did not list (`_references_core.py`, `analyze-logs.py`, not read for rename-following): one Watch.
- **The Done-whens and hypotheses this orchestrator authored wrongly (L1-1, L1-2)** are recorded in Layer 1 for later specs.
