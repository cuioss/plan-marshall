# Landing Analysis: PLAN-LB-153 — A phase-5 hand-back commit gets its own change-ledger row

epic: live-blockers
workstream: WS-01
pr: #1999 (https://github.com/cuioss/plan-marshall/pull/1999)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-153.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-153-phase5-handback-commit-rows`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `6a16e216b12616de813a2be522e6e0008ce2ce90` through the merge queue, branch
`fix/lb-153-phase5-handback-commit-rows`. Message `rb-lb-153-phase5-handback-commit-rows-001.md` carries
`total_tokens=unknown` (out of scope under the standing ruling) and `self-review:budget-exhausted` (see Follow-Ups).

## Deliverable Fidelity vs Spec

Corroborated with the CI abstraction (`ci pr view`: `merged`, merge commit and head branch as stated) and a read of
`workflow-integration-git/scripts/git-workflow.py` and the two SKILL.md files on `origin/main`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a marked phase-5 hand-back commit has one row owner under one id, no commit gets two rows | shipped-as-specified | merged `git-workflow.py`: `commit` takes `--record-change` (usage line); `_HAND_BACK_COMMIT_DELIVERABLE_ID = 'handback-commit'` (`:1022`, no trailing digit, so `deliverable_number` never maps it to an outline deliverable); `_record_commit_change(..., finalize_phase)` records a `6-finalize` commit unconditionally and a phase-5 commit only when marked (`:1057-1123`); an unmarked phase-5 commit records nothing, so Step 10a's append stays that commit's single row (re-read) |
| D2 documented recovery for `execute_commits_unrecorded`, tests for gate-rewrite, style-fix and two-deliverable commits | shipped-as-specified (lane-reported) | the recovery text in `execution.md` and the parametrized tests are the lane's report; not re-read here. The mutation evidence names two mutations (M1: 2 failed / 28 passed, M2: 5 failed / 25 passed) with daemon job ids |

The merge-commit case is a scope addition the spec did not list: `_commit_changed_paths` enumerates a merge commit's first-parent diff
(`:1033-1054`) so a merge commit no longer records an empty `changed_paths`. It came from a CodeRabbit finding and is a fix to the same
row writer, not a new surface.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the change centres on one function and its helper, both read in full on the
merged tree. By reading: no build, no test run.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | Hypothesis: the verb cannot tell a Step 10a commit from a hand-back commit without a caller-supplied marker | checked | confirms | the only discriminators were `phase`/`staged`/`step`; the merged docstring states why the marker is needed (`:1071-1075`) |
| L1-2 | OBSERVED: `_record_finalize_change` recorded only in `6-finalize` | checked | confirms | the base function is renamed `_record_commit_change` and now takes `finalize_phase` |

**Layer 1 verdict:** no refuting finding.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | `git-workflow.py:1009-1123` | mutation-after: M1 pins `record_change` to `False` (2 failed) | none | checked |
| D2 | `execution.md` § Execute Phase Completion (lane-reported) | mutation-after: M2 forces `_sha_is_recorded` to `False` in `manage-status/scripts/_cmd_lifecycle.py` (5 failed) | `_cmd_lifecycle.py` is the mutation target, not edited | not re-read |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `git-workflow.py:1100-1105` | a phase-5 commit marked `--record-change` that also names `--step` | the row takes the step id, not `handback-commit` — intended (a named step wins), recorded only because the docstring states it for the finalize case | info |
| L3-2 | the lane's own residue | a caller passes `--record-change` on a Step 10a commit and then appends its own row | two rows for one commit: no code-level backstop, only a documented caller contract | minor, lane-recorded |
| L3-3 | `manage-change-ledger/SKILL.md` Integration table and Prohibited list | reading the contract | still names `git diff-tree` as the only source of `changed_paths`; the merged code uses a first-parent `git diff` for a merge commit (re-read) | minor, documentation |
| L3-4 | `manage-change-ledger/SKILL.md` Integration table, `manage-status` row | reading the contract | the row names only the ready-to-run `remap` invocation, not the per-SHA `append_invocations` the refusal now also carries (re-read) | minor, documentation |
| L3-5 | `workflow-integration-git/SKILL.md` ~line 250 | reading the resolver note | says every non-`merge_lock` resolution is cwd-relative, while `_record_commit_change` writes `{worktree}/.plan/work/change-ledger.jsonl` from the named tree (lane-reported; the sentence at that line is quoted, the contradiction is the lane's reading) | minor, documentation |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (the lane reports 34003 tests at the
last head) and both mutation runs. No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-2 is a documented contract rather than a code gap; L3-3 to L3-5 are the three
documentation items the lane left open.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only | conforms | the merged docstrings state present behaviour |
| `pm-dev-python:python-core` | explicit exception handling, no bare `except` | conforms | `OSError` and `ImportError` named (`:1109-1122`) |
| CLAUDE.md Workflow Discipline | no shell file operations | deviates (self-reported) | the lane read a daemon job log with `head`; the guard did not flag it |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: one self-reported shell file read (`head` on a job log) with no guard line for the run; twenty-four routed builds, all
  `daemon_longpoll`, no fallback and no killed job; one whole-tree run carried a collection error from a gitignored `target/` tree absent in
  a fresh worktree, fixed by generating the claude target; CodeRabbit was rate-limited and the lane followed the quota policy (waited 90
  minutes, re-triggered, escalated to a full review once).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited, `review_complete_after_handling`) reviewed `4b1c6947` (four findings, all fixed) and then
  `88e026f8` (four findings, all fixed). Sourcery (optional) refused on quota. The lane's standing review authorization applied and
  `review-gate` confirmed it per reviewer. Not independently re-run here.
- CI/merge: green on the pushed heads per the lane; queue merge; two base merges.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-154, -155, -156 and -157 on disjoint surfaces; no collision reported.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-153 --status shipped`
- [x] row `pr` stamped — `1999`
- [x] row `landing` stamped — `landings/PLAN-LB-153.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-153-phase5-handback-commit-rows` (from the sender)
- [x] `epic.md` narrative: one Watch for the three open documentation items
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- No executor regeneration is owed (a verb flag was added to `commit`; the executor maps scripts, not argparse surfaces). A harness sync is owed for the edited bundle sources.

## Follow-Ups

- **Three documentation items (L3-3 to L3-5)** — recorded as one Watch; nothing staged. Self-review is `budget-exhausted`: round 2 ran after the
  merge and stopped there, so these were not iterated. Whether a small completion plan carries them is the operator's word.
- **Advisory items from the lane** (`execution.md:558-559` causal sentence now imprecise, a hardcoded `'.plan'`, a ledger-binding test assertion that cannot fail for the defect it names, two scenario names that are behaviourally identical, a fixture whose "worktree" is a repo subdirectory, one stale docstring in `_ledger_core.change_record`) — recorded here, no plan.
- **Archived message `lessons-routing-087.md:24`** cites the renamed `_record_finalize_change`; it sits under `.plan/orchestrator/` and is an archived record, left as written.
