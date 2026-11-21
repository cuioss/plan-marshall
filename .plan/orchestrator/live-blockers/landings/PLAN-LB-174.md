# Landing Analysis: PLAN-LB-174 — Fix the defects the PLAN-LB-172 landing found in its own merged code

epic: live-blockers
workstream: WS-04
pr: #2042 (https://github.com/cuioss/plan-marshall/pull/2042) — MERGED as `6a2dbf90bafeba18648db65dc75549826c48a9b9`

> Landing record for one plan, from the single landing message (`-001`, filed 2026-11-21T17:40:22Z). Every figure is labelled OBSERVED (re-read by the orchestrator) or CARRIED (the lane's own statement, not re-read). A point of the leaf's that the orchestrator did not open is labelled "leaf reading, not re-read".

## Deliverable Fidelity vs Spec

The spec is `plans/PLAN-LB-174-lb172-landing-defects.md` (six deliverables). OBSERVED against git: the squash commit `6a2dbf90b` (parent `1da09fca7`, the ledger land of #2041) changes 29 files. The PR was merged through the queue (CARRIED).

**All six deliverables shipped.** `deliverables_done=6` of 6 agrees with the diff. The leaf's conformance table marks every Done-when clause `met` except four, all `partial` or borderline and none a miss of a literal clause: the `build-execution.md` exit-code table (D1), the property test not extended to the fence-only shape (D3), the status-line supplement path (D3), and the empty-delta reason token (D2, borderline).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 post-run log fault stays a launch fault | shipped-as-specified; the documents' exit-code table lags (minor) | `_build_shared.py`, `marshalld.py`, `_marshalld_supervisor.py`, `build-execution.md` and two tests in the diff (OBSERVED); the renderer, the subdir creation and the stated trust bound are the leaf's reading, not re-read |
| 2 carry-forward binds through its status | shipped-as-specified | `sonar.py`, `runbook_lane.py`, both SKILL.md files and four tests in the diff (OBSERVED); the leaf found no flag combination that renders a carried-forward read as a plain pass |
| 3 fence-only section counts, cap before allocation | shipped for the heading path; the status-line supplement path still allocates before the cap check (minor, re-read) | `runbook_lane.py:3841-3845` and `:4386-4396` (OBSERVED) |
| 4 symlinked workflow named | shipped for a symlinked FILE; a symlinked DIRECTORY and an unreadable directory are not named (layer 3, two majors of narrow reach, re-read) | `runbook_lane.py:1310-1384` (OBSERVED) |
| 5 manifest and `manage-config` refuse what they cannot read | shipped; the code, not the documents, was fixed for the caller-file reason | `_manifest_rules.py`, `manage-execution-manifest.py`, `decision-rules.md`, `_cmd_orchestrator.py` and three tests in the diff (OBSERVED) |
| 6 one owner for the re-read rule, tests that can fail | shipped; the template still restates the answers (minor) | the three documents and two tests in the diff (OBSERVED); the shared-slot hypothesis refuted, `tools-integration-ci/SKILL.md:222-241` carries the rule (CARRIED by the lane, confirmed by the leaf) |

### The merge record against the merge

OBSERVED through the CI abstraction (`ci pr view 2042`): the PR body states six deliverables, per-deliverable test evidence and an "Outside the Expected Surface" list. It matches the diff in scope, with one exception: the list names four files, and the diff has five. See Surface drift. The merge record is otherwise faithful; no correction of the body is owed on scope grounds.

### Surface drift

The spec's Expected Surface declared 33 entries (32 resolved paths and one directory). OBSERVED from the merged file list (`git diff --name-only 1da09fca7 6a2dbf90b`):

- **Changed, not declared (5):** `phase-4-plan/SKILL.md`, `workflow-integration-sonar/SKILL.md`, `test/plan-marshall/manage-config/test_orchestrator_scope.py`, `test/plan-marshall/workflow-integration-sonar/test_sonar_analysis_revision.py`, `uv.lock`. The PR body names the last four with a reason each and not the first. **The landing message says the PR body names all five (`phase-4-plan/SKILL.md` among them) and gives no reason for it; that statement is false for `phase-4-plan/SKILL.md`** (OBSERVED: the body was read in full). The spec's Standing Constraint ("no file outside the Expected Surface is touched without being named in the PR body and the landing message with the reason") is breached for that file.
- **Declared, not changed (7):** `build_server.py` (a read-only consumer, the leaf found the passthrough correct), `manage-config/SKILL.md` and `standards/api-reference.md` (the code, not the documents, was wrong), `tools-integration-ci/SKILL.md` (hypothesis refuted), `test_build_server_client.py`, `test_marshalld_supervisor.py` (existing suites held, CARRIED), `test_orchestrator_use_worktree.py` (the reason tests went to `test_orchestrator_scope.py`, which the PR body names).
- **`phase-4-plan/SKILL.md` is not a wording fix.** The edit says callers must ALWAYS forward `--commit-and-push` to `compose`, and adds "a refused `compose` ends the step — never fall through to `validate`". Its claims hold (the leaf, not re-read: `manage-config get` merges the defaults first; `compose` already refused a non-boolean value before the merge). D5's Done-when covers reconcile only, so the edit is a drive-by. OBSERVED: the same file now contradicts itself, `:752` says ALWAYS forward and the compose block at `:767` still shows `[--commit-and-push {commit_and_push}]` as optional.

## Three-Layer Analysis

- **Dispatch:** one `execution-context-level-5` leaf, read-only, on the `orchestrator.analyze` surface (resolved through `manage-config effort resolve-target`; `level-5`, source `orchestrator.effort.analyze`). Reason: reading 29 changed files across six deliverables is the depth the dispatch rule exists for; the spec crossed the edge as data (a condensed excerpt of the deliverables, Done-whens, declared surface and the PR-body claim, in the session scratchpad, since the leaf may not open `.plan/`). Its report was 15 findings, a fail-open scan, answers to five questions and 24 conformance rows. The leaf had no Grep or Glob and did not sweep `.claude/**` or `test/` for consumers of the changed values.
- **Re-read by the orchestrator before recording** (each at its `file:line`): `runbook_lane.py:3805-3845` (the section count), `:1310-1384` (workflow discovery), `:4375-4397` (the status-line supplement); `phase-4-plan/SKILL.md:752-768`; `ci pr view 2042` (the body, in full); the merged file list. Every other `checked` point of the leaf is recorded below as a **leaf reading, not re-read**.
- **Not re-read at all:** the red-at-base order of every Done-when (only a run shows it); the lane's build logs and test counts; the heading-path cap check (`runbook_lane.py:4259-4278`); the renderer of a post-run launch fault (`_build_shared.py:799-826`); the `build-execution.md` table; every `READ-ONLY-GUESS` of the leaf.

### Layer 1 — Specified

The premises hold against `78951e23c` (the leaf read the pre-merge code with `git show` where it compared). The lane settled the five hypotheses: three CONFIRMED, two REFUTED (the shared-slot rule is present; a malformed `commit_and_push` is not the documented default, only an absent key is). One spec weakness of this orchestrator's own authoring:

- **(minor, OBSERVED)** The spec's D4 Done-when names one regular workflow beside a symlinked FILE. The same class has two more members it did not name (a symlinked directory, an unreadable directory); the spec's Standing Constraint "never a passing value for an input it could not decide" covers them, so the lane met the clause and left the class half closed.

**Layer 1 verdict:** sound with one defect (spec-authoring, minor)

### Layer 2 — Implemented

Every deliverable traces to code and to a test; the leaf judged each new test to discriminate (read against the pre-fix code, nothing was run), with one exception noted below.

- **(minor, leaf reading)** `test_a_carried_forward_status_without_its_marking_is_refused` would have been refused before the fix too, as `invalid_count_status`; it discriminates on the error code only. The test that discriminates the fail-open is `test_a_carried_forward_read_never_answers_confirmed`.
- **(minor, leaf reading)** The constructed property test `test_a_body_declaring_three_never_reads_fewer_than_three_or_stops` was not extended to the fence-only shape; a separate parametrized test covers it.
- **(minor, OBSERVED)** The PR body's "a stop leaves the numbering counters untouched" holds for the heading path only; see layer 3, the supplement.
- Not shown by reading: that each new test fails at the base tree.

**Layer 2 verdict:** implemented with minor gaps

### Layer 3 — Correct

No fail-open of the three majors remains: the leaf found the carried-forward read can no longer reach either verb unmarked, and the launch-fault leg owns a post-run fault (leaf reading, not re-read). Left beside them:

1. **A symlinked workflow DIRECTORY is followed** (D4 class). OBSERVED: `_iter_workflow_files` takes `directory.iterdir()` and skips `is_symlink` entries (`runbook_lane.py:1322-1334`); `_workflow_discovery_problem` does the same on its own listing (`:1357-1364`). Neither checks the directory itself, so a tracked link `.github/workflows -> elsewhere` (or `.github`) is read as this checkout's rule. Trigger: a tracked directory link holding `skip-on-docs-only: true` and a broad `paths-ignore`. Effect: a docs-only verdict from bytes the graded tree never held. Narrow reach: it needs a tracked link in the project's CI directory.
2. **An unreadable workflows directory reads as no workflow.** OBSERVED: both functions catch `OSError` and return `[]` / `None` (`:1323-1326`, `:1358-1361`); `PermissionError` is not told from `FileNotFoundError`, and the decision reaches the architecture fallback. Pre-existing; narrow reach (a directory the process cannot list).

Minors, grouped by file; the first two are re-read, the rest are the leaf's reading and not re-read:

- `runbook_lane.py:4386-4396` (re-read): the supplement is capped on its own and its rows are built before the combined check at `:4393`; up to twice the cap of rows is minted and the counters advanced before the stop.
- `phase-4-plan/SKILL.md:752` against `:767` (re-read): ALWAYS forward against an optional flag in the compose block.
- `compose` still treats an omitted flag as `true`, and `manage-config get` crashes on a non-object `plan` or `phase-5-execute` block (`_cmd_quality_phases.py:562`) where reconcile now refuses.
- `build-execution.md:643-644`: the exit-code table maps 0 to success and 1+ to a failed build; a post-run launch fault is `status: error` with exit 0 or 1 and has no row.
- `runbook_lane.py:1888`: the empty-delta reason token is still `carried_forward_unbuilt_delta` while the sentence now says "is empty".
- `runbook_lane.py:2832`: `conflicting_revision_spellings` compares raw strings, not `_same_revision` (fails closed).
- `landing-analysis.md` restates the answers it says it does not own; `decision-rules.md:180` restates phase-4's forwarding rule.
- `analyze.md:155` names no verb for the PR read.
- `marshalld.py:801`, `:813` still require `.plan`; `:849-853` with `_ensure_private_directory` re-modes the constant's first component to 0700 (bites only if the constant moves).

**Downgraded on the re-read, NOT a defect of this plan:** the leaf's major that a section declaring `(0)` over a fence reads 0. `_count_section_findings` returns the declared count first (`runbook_lane.py:3829-3830`) and its docstring states that the declared count wins; the shape predates the merge and D3's literal clause (no declared count) is met. Recorded as a hardening candidate.

**Layer 3 not shown by reading:** the lane's `verify`, test counts, whether each new test fails at the base tree, and the leaf's queue/retry-consumer guess.

**Layer 3 verdict:** defects found — two majors of narrow reach, reported to the operator in the same turn

### Conformance to the Project's Own Rules

- Spec standing constraint "fail closed" — **deviates in two narrow places** (layer 3, items 1 and 2); the three majors it was staged for are closed.
- Spec standing constraint "no file outside the Expected Surface unless the PR body names it" — **deviates**: `phase-4-plan/SKILL.md` (OBSERVED).
- Spec standing constraint "the PR body contradicts the diff is a defect" — **deviates in one sentence**: "a stop leaves the numbering counters untouched" (supplement path), and the landing message's claim about the five named files.
- Test-first with a recorded red run — **conforms as claimed** (CARRIED: pytest node locations for every Done-when, two earlier green runs not cited because the worktree was edited while they ran); not shown by reading.
- Documentation Standards, no duplication — **deviates** (template and `decision-rules.md` restate).
- Spec: the PR #2028, #2033 and #2036 bodies untouched, the delegating-consumer case not staged — **conforms** (CARRIED; the PR #2036 body was not read again).
- Lane-reported (CARRIED): guard present, no refusal recorded; no restarts; build server `daemon_longpoll` on every build, no fallback; one accidental edit-in-flight twice, both runs recorded as invalidated and re-run (a process error, not a rule breach).

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none. Recorded as an unobserved fact, never as zero; `landing-check` reports `total_tokens` missing, so the landing is `complete: false`, and that alone is no defect (ruling of 2026-10-23).
- Duration: not supplied (`unmeasured` surface delta; `landing-check` was run without paths).
- Harness `opencode`, model `deepseek-v4.1-flash/high`, effort high, executor `0.1.2173` (CARRIED).
- Anomalies: the landing message's claim about the PR body (see Surface drift); `uv.lock` regenerated because main's dependency bumps left it stale, named in the PR body; two `module-tests` runs invalidated by an edit in flight and re-run (CARRIED).

## Routing and Merge Behavior

- Review: coderabbit (required). OBSERVED by `runbook_lane review-gate --pr-number 2042` on the merged PR: `unresolved_review_threads: 0` and `review_body_findings_total: 13`; the landing's two numbers match the re-read. `review_body_findings_handled` re-reads as 0 and is **not re-verified**: the provider cannot reproduce the number; the lane's `13/13` is a CARRIED statement, not a difference and not a false claim. The merge-gate refusal read in this re-run (`body_findings_undisposed`) is a property of the re-run without the lane's dispositions, not of the merge. Two nitpicks were declined with reasons (CARRIED); Sourcery refused twice on its own quota and is not gating.
- CI/merge: OBSERVED through the CI abstraction: state `merged`, merge commit `6a2dbf90b`; `verify / conclusion`, `verify / verify`, `verify / gate`, `generate-check` and `dependency-review` green; `SonarCloud` green (not a gate here); `CodeRabbit` `NEUTRAL`, `auto-merge` and `Sourcery review` `SKIPPED` on the final state.
- Sonar: `n/a` in the landing; not enabled for this repository; nothing to compare.
- Collisions: none observed.
- Cleanup: `cleanup_owed=false` (CARRIED).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-174 --status shipped` (`running` → `shipped`)
- [x] row `pr` stamped — `2042`
- [x] row `landing` stamped — `landings/PLAN-LB-174.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-174-lb172-landing-defects` (first written as `lb172-landing-defects`, corrected in the next call to the sender id, as row 172 carries)
- [x] epic.md narrative reconciled (a Decisions entry; the 172 Open Defects block marked shipped with its settled lead; a new Open Defects block "from PLAN-LB-174's landing")
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated
- [x] message archived (`inbox archive`), decision logged
- [ ] Layer 3 — NOT staged: reported to the operator; a fix plan is staged only on the operator's word
- [ ] `/apply-changes` — owed to the operator, not run by the orchestrator
- [ ] ledger land — NOT landed; the writes of this act ride the next `land`

## Follow-Ups

- Layer 3 (reported to the operator; staged only on the operator's word, then one plan, `lane=runbook`, grouped by module): the two narrow-reach majors in `runbook_lane.py` workflow discovery, the supplement-path allocation, the `phase-4-plan/SKILL.md` self-contradiction (and whether the drive-by edit stays), and the grouped minors above. All sit in `runbook-lane` and its documents but for the build-execution table and the `phase-4-plan` pair.
- PR body corrections: none owed on scope. The PR #2036 and #2033 body corrections remain the operator's call.
- `/apply-changes` is owed after this merge, on top of the 171/172 bundle edits.
