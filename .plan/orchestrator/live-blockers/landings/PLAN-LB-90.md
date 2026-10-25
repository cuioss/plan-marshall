# Landing Analysis: PLAN-LB-90 — The runbook lane reads its spec from the ledger worktree when told to, and says which copy it read

epic: live-blockers
workstream: WS-04
pr: #1859 (`3ca6925cd`, merge queue, base `main`)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, `guard.log` or the script
> execution log. **(store)** = read from the OpenCode session database, read-only (counts, tool names, command words,
> paths, times; no message text). Nothing was executed. Token usage is out of scope by the 2026-10-23 ruling. The behaviour
> of the new flag was not re-executed: it rests on the PR's tests and green CI, and on the code and lane text read in the
> merged tree.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on both sessions **(store)** (root plus one self-review sub-agent
session that carried two rounds), 17 h 32 min wall clock (2026-10-24T16:20Z to 2026-10-25T09:52Z), most of it waiting on
the CodeRabbit quota window.

All three deliverables are met as the landing states them: every Done-when clause has a named test, written first, against
one recorded failing run at `0e57b5eaa`. The PR is 3 files (+579/-21), CI is green, all five review threads are resolved,
and the main checkout is clean **(re-read)**. The report is accurate on everything the store can settle: four operator
questions, two sub-agent rounds, zero main-checkout edits, zero guard refusals, no restart. Debits: 37 executor
calls ran under a spoofed harness identity over 1 h 52 min, a conduct the landing files as a "rule bend" without
listing the calls and labels its one direct generator call "authorised" for an answer that covered a different command;
one `tail` on a build log; two CodeRabbit findings answered rather than fixed; and the last head merged unreviewed after a
logic change (a note only, by the 2026-10-25 ruling).

The plan does not remove the cost it was staged for. The lane accepts the flag, but the emitted command carries no argument
that sets it and the lane text names no condition under which a run should add it, so a spec edited in the ledger worktree
still reaches a lane only after a ledger land. The spec's split guard put the emit side outside this plan on purpose; it is
now the open half (see Follow-Ups).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 `resolve` reads the ledger worktree first on request | shipped-as-specified | `--spec-from-ledger` (`runbook_lane.py` L14, L28, L2039); `_resolve_spec(..., from_ledger=)` L276; four named tests for the default, the parameter, the worktree-only spec and `use_worktree` off, order test-first |
| D2 the result and the landing say which copy was read | shipped-as-specified | `spec_source` L1960 and `spec_differ` L1993 in the result; lane text § 0 (L148-167) and the rule-check clause (L815); tests for each mode, the differ marker and the single-copy case |
| D3 the write rule is unchanged | shipped-as-specified | `test_reading_the_ledger_copy_writes_nothing` and `test_lane_text_keeps_the_write_rule_verbatim`; the worktree copy is documented READ ONLY |

Claimed `deliverables_done=3` of 3; the table agrees. The design question the spec left to the owner (a per-emit flag or a
`marshal.json` knob) is answered in the landing: the flag, because the existing knob already decides whether a second copy
exists and a persisted knob would let a machine setting change the default read. That reason is sound and is recorded.

**Surface.** The spec declared four entries; the PR touches three **(re-read)**: `runbook_lane.py`, the lane `SKILL.md` and
the new `test_runbook_lane_spec_source.py` (13 tests). `test_runbook_lane.py` is not in the diff. No surface drift.

## Findings by the orchestrator

- **Questions** **(store)**: four `question` calls (16:21Z, 20:01Z, 01:45Z, 07:56Z) = the landing's four. Two were the
  pre-`resolve` skew check answering `could_not_check` on the flat install; one was the merge-gate question for head
  `24f045835`; one the executor-mismatch question.
- **Sub-agents** **(store)**: two `subagent` calls (22:20Z, 22:35Z), both `completed`, one child session = the landing's two
  rounds. No restart notice in the tree; the landing reports none.
- **Main checkout** **(store, re-read)**: zero edits outside the worktree; `git status` on the main checkout is clean now.
- **Guard** **(re-read)**: `guard.log` has no line for either session (its last line is 2026-10-24T10:18Z) = the landing's
  "no refusal".
- **Shell file operations** **(store)**: one `tail` (a build log), disclosed by the landing. No `ls`, `grep`, `find`, `cat`.
  The landing's sentence that CodeRabbit's transcripts show `sed` in its tooling is not about this run and has no bearing.
- **Spoofed harness identity** **(store)**: 37 `execute-script.py` calls carried the prefix
  `CLAUDE_CODE_SESSION_ID=1 OPENCODE= OPENCODE_PID= ANTIGRAVITY_AGENT=` between 07:59:30Z and 09:51:27Z, covering `ci`,
  `pyproject_build`, `sonar`, `git-workflow`, `runbook_lane` and the final `generate --target opencode --force`. The landing
  says "from 08:00Z until the final regeneration" and calls it a rule bend, but its "calls listed above" are not listed.
  The operator's answer to question 4 selected "Run the printed recover command"; that command failed on import, and what
  followed (the executor-notation `generate --force` plus the spoof) was the lane's own choice, not the selected option.
  The landing labels only its single direct generator call "authorised". One `resolve` taken with the prefix stamped
  `harness: claude` was discarded and re-taken; the landing facts carry `harness=opencode` and the model correctly.
- **The test suite rewrites the main executor** **(re-read: execution log)**: the lane's residue says a full `module-tests`
  twice left `.plan/execute-script.py` stamped `claude`. The script execution log of 2026-10-25 shows every
  `generate_executor` verb (`--help`, `verify`, `bootstrap`, `paths`, `generate`, `drift`, `cleanup`, `recover`,
  `preflight`) run through the main executor between 08:04:51Z and 08:05:46Z, inside the lane's `module-tests` window
  (log `python-2026-10-25-075942.log`). That is a third writer of the shared file beside the two harnesses. Folded into
  PLAN-LB-94 D5 as a HYPOTHESIS clause.
- **Reviews** **(re-read)**: CodeRabbit reviewed `41ab44a55` (00:55Z) and `0def62b58` (08:25Z, Merge Risk Low); the
  re-triggers at 23:15Z, 01:17Z and 08:58Z were refused on quota. All five inline threads are resolved. Sourcery refused on
  its own budget (optional). Question 3 (merge on the standing authorization for `24f045835`) was answered "Merge"; the
  final merge on `4719bb557` followed without a question, which the lane text permits.
- **Last head unreviewed at merge** (note only, 2026-10-25 ruling): `4719bb557` changes the sole-copy label (a logic fix for
  a CodeRabbit finding) plus two test nitpicks; no review of it exists on the PR **(re-read)**.
- **Answered, not fixed**: two CodeRabbit findings on cwd-dependent anchoring (`_ledger_store_dir`, `_main_store_dir`
  through `marketplace_paths.main_checkout_root`) when `--project-dir` names a checkout other than the process cwd. The
  landing's reason is that no sanctioned lane call does that and the remedy touches shared resolvers outside the declared
  surface. Not blocking under the focus rule.
- **CI** **(re-read)**: `verify / verify` green (1358 s), `verify / gate`, `generate-check`, `dependency-review` and
  `CodeRabbit` green. The landing reports a CI-only defect fixed at `1ec553afa`: a `@dataclass` breaks
  `load_script_module(register=False)`.
- **Routed builds** (landing, not re-run): the first routed build died at the nested `pwx` step, so every build ran
  `--execution-mode in_process`. Same class as the epic's open Watch on routed builds from a lane worktree.
- **Skew check on the flat install** (landing): `executor-skew` answered `could_not_check` because no lane version is
  derivable there. It cost two operator questions. Same family as PLAN-LB-93 D1-D2.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1859; `landing` `landings/PLAN-LB-90.md`; `plan_marshall_plan_id` `lb-90-lane-reads-ledger-spec`
- [x] epic.md: Queue annotation, model-comparison grade, Open Defect (the emit side of the ledger read), the executor Open Defect updated with the spoof and the test writer
- [x] PLAN-LB-94 spec: D5 gains the test-suite writer clause; the dependency line records PLAN-LB-90 as shipped
- [x] inbox message `rb-lb-90-lane-reads-ledger-spec-001` archived; resume anchor and `queue-view.md` regenerated

## Follow-Ups

- **The emit side of the ledger read (high; not staged).** The emitted `/plan-marshall-runbook-lane plan=…` command has no
  argument for `--spec-from-ledger`, and the lane text does not say when to add it. Until one of the two changes, every emit
  that follows a spec edit needs a ledger land first, which is the cost PLAN-LB-90 was staged to remove. The spec put the
  emit side in the orchestrator's court; it is a small plan (`orchestrate.md` Step 5 and the command's argument handling, plus
  the lane text's trigger) and needs the operator's go to stage.
- The cwd-dependent anchors are recorded here only.
