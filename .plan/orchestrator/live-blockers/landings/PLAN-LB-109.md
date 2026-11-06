# Landing Analysis: PLAN-LB-109 — a prescribed hand-back is recorded as a hand-back, not as an error

epic: live-blockers
workstream: WS-01
pr: #1911

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-109.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `051fda6a0b87da79087b4509dd6fdce62b148ad3` (parent `7d4182f46`), read through the `ci` abstraction as `pr_state: merged` with a green merge-group run. Landing message `rb-lb-109-execute-prescribed-yield-not-error-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule). The diff touches 34 files, 1725 insertions and 78 deletions: 25 under `marketplace/bundles/plan-marshall/skills/`, 9 under `test/`. The lane reports 3 of 4 deliverables done.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the hand-back carries a declared signal and a cause of its own | shipped-as-specified | `verification_handback` row in `execution.md:207`, the return contract and the recorder's accepted set (`manage-metrics.py`, 14 members), four-edge analyzer tests. One Done-when clause is met trivially (L1-3 below). |
| D2 — the no-progress rule cannot reclassify a prescribed hand-back; a script decides | shipped-modified | `evaluate_no_progress` (`_tasks_query.py:456-524`) in a new mode of `loop-exit-guard`, owed tasks reported separately, the "Other Errors" citation fixed (`execution.md:254`). Shipped in the order the spec asked for, and that order is itself a defect (L1-1). |
| D3 — the lessons signal counts genuine stalls only | shipped-as-specified | New `signal-scan` verb (`_signal_scan.py`), one marker string stated in `execution.md:262` and the scanner, pinned equal by a test; hand-back rows excluded (`phase-6-finalize/SKILL.md:929`). The "first and third fail at `0fb6a79b1`" clause holds only because the verb did not exist then (L2-2). |
| D4 — a measured over-ceiling module builds once per deliverable | shipped-modified | Chain-tail deferral in `manage-execution-manifest.py` (stamps `owed_rung`, `owed_rung_command`), honoured by `execute-task` and enforced in `finalize-step` (`_cmd_step.py:145-147`). The lane reports the unmeasured-arm Done-when "not met as written"; that verdict is not settled by this reading (L1-2, L2-1). |
| not a deliverable | added-unplanned | 22 paths beyond the declared surface (`landing-check` `surface_delta`: `expansion_detected`, 18 declared, 34 realized), all explained by D1–D4 or by an enumeration they changed: `manage-logging` (the new verb), `manage-execution-manifest` docs, `_cmd_step.py`, `manage-tasks.py`, the `phase-5-execute/standards/` docs, `agents.md`, `dispatch-granularity.md`, `execution-recovery.md`, `logging-gap-analysis.md`, and six tests. Six declared HYPOTHESIS paths were not touched (`_manifest_validation.py`, `_cmd_client_handlers.py` and four existing tests). |

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`), and the orchestrator re-read the points recorded as `checked` below at their `file:line` before writing them here. The reading is by reading, no build, no test run, no write. The leaf had no Grep in its envelope; it reports one read-only `git grep` against the merge commit, a break of the no-`git grep` rule, and skipped its own completion logging under the read-only instruction.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code across 34 files is depth work, and this landing's read must not share context with any other.
- **Verdict:** layer 1 findings (one major, minor); layer 2 findings (minor); layer 3 findings (one major, minor, info), no blocker.
- **Orchestrator re-read:** the rows marked "re-read" were read again at the cited lines in the merged tree. Rows marked "lead" were not re-read and are unverified leads.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (major) | The spec says a return classified as the new cause "never reaches the predicate", and also says "do not weaken the no-progress rule for a genuine stall". The first forces the hand-back check before the predicate, so a stall on a NON-owed task in the same dispatch is classified `verification_handback` and the decision line (written only on `error`, `execution.md:254-260`) never exists: B7 and Signal 3 never see it. No test combines a hand-back with a non-owed stalled task. re-read | checked | `plans/PLAN-LB-109-…md:69-70,118-120`; `_tasks_query.py:509-512`; `execution.md:242` |
| L1-2 | "Owed rung" is never defined (the compose-time command, or the per-task owed hold), so bullet 3 ("a command key with no measurement keeps today's behaviour", L105) and the Done-when ("or unmeasured, puts it on all three", L110-111) can be read as contradicting each other. That is the spec-side cause of the lane's not-met verdict. re-read | checked | `plans/PLAN-LB-109-…md:100-111` |
| L1-3 | The D1 Done-when assumes the polling detector reads boundary rows; the leaf says it reads `work.log` `[ATTEMPT]` lines only, so the clause is met trivially and no test could fail on it. lead | checked by leaf, not re-read | `analyze-logs.py:1748` |

**Layer 1 verdict:** findings — 3 (one major).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `manage-metrics.py` (member), `execution.md:207`, `phase-5-execute/SKILL.md:1392` | `TestEveryDeclaredCauseIsAccepted` (parametrized over the constant) | none | checked (test not re-read) |
| D2 | `_tasks_query.py:456-524` | `test_plan_25_shape_is_the_handback_cause_not_error`, `TestLoopExitGuardReportsOwedTasksSeparately` | none | checked (tests not re-read) |
| D3 | `_signal_scan.py`, `manage-logging.py` | `TestSignal3CountsGenuineStallsOnly`, `TestTheWriterAndTheScannerShareOneMarker` | L2-2 | not_shown_by_reading |
| D4 | `manage-execution-manifest.py:1440-1510`, `execute-task/SKILL.md:316`, `_cmd_step.py:145-147` | `TestMeasuredOverCeilingDefersToTheChainTail`, the fourth-task regression | L2-1 | checked (tests not re-read) |

- **L2-1 (unborne claim):** the lane says that in the unmeasured arm "the rung is on NONE of the three tasks". `execute-task/SKILL.md:316` says an absent stamp "branches on the live tier exactly as above", so a leaf still hands the wider run back when its live tier resolves to `orchestrator`. The leaf reads the unmeasured key as resolving `orchestrator` (`_cmd_client_build.py:401`, **lead, not re-read**), which would leave the owed hold on all three tasks and make the Done-when satisfiable; only a leaf-side test is missing (the compose test checks compose state only). The lane's reading concerns the compose-time commands. So `deliverables_done=3` rests on an ambiguous reading, and the lane's own residue (a spec edit owed) stands.
- **L2-2 (weak test, lead):** the D3 hand-backs-only test cannot fail on an exclusion regression, because hand-back boundary rows never feed `signal_3_count` (`_signal_scan.py:185`). The lane's mutation evidence fails the genuine-reclassification test, not this one. Neither file re-read.
- **L2-3 (lead):** the spec names `manage-metrics reconcile-ledgers` as a reader of the boundary row and asks one check per edge; the diff tests only `analyze-logs`. Whether `reconcile-ledgers` reads the cause was not read by the leaf.
- **L2-4:** the lane says "no surface drift was found". The diff adds 22 paths beyond the declared surface (see the fidelity table); the lane's own claim of no drift is contradicted, though each added path is explained.
- **L2-5 (info, re-read):** the CodeRabbit major fix is borne out — a stamp the decision moves is rewritten before the empty-command skip (`manage-execution-manifest.py:1464-1473`).
- Red-at-base runs, the mutation logs and every per-head test run are `not_shown_by_reading`.

**Layer 2 verdict:** findings — 4 (minor/info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `execution.md:239`; `_tasks_query.py:424-427` | `completed_tasks_delta` is "read from the prior `record-dispatch-boundary` row", which the lane's own report says carries no done count; the orchestrator has no stated source and substitutes `0`, or omits the flag, which `_int_arg` also turns into `0` | A dispatch that completed tasks but used more than 50,000 tokens beside a non-owed in-progress task is reclassified `error`, a false positive that feeds Signal 3. (The "no done count" premise rests on the lane report and the leaf's fixture headers, not re-read.) | major |
| L3-2 (re-read) | `manage-execution-manifest.py:1494-1508` | A task with two orchestrator-tier `module-tests` commands (two modules) | `owed_rung_command` is the last such command, so the next compose re-measures the wrong one; the "exactly one `chain_tail`" invariant the CodeRabbit fix targets can break. (Effect inferred from the code; not run.) | minor |
| L3-3 (re-read) | `manage-execution-manifest.py:1458-1460` | A two-module deliverable where module B is re-measured below the ceiling and A still qualifies | Staleness is decided by deliverable, grouping by (deliverable, command): B's `deferred` and `chain_tail` stamps survive, against `manage-execution-manifest/SKILL.md:772` (not re-read). | minor |
| L3-4 (lead) | `manage-execution-manifest.py:1250` | Group {2,3} where task 2 depends on task 5 outside the group | `_chain_order` ignores dependencies through outside tasks, so the chosen tail can run before a deferred task's change exists. | minor |
| L3-5 (code re-read, occurrence unknown) | `_cmd_step.py:145` | `--verification-owed` on a task record with `verification: null` | `.get('verification', {})` returns `None` and `.get('owed_rung')` raises `AttributeError`. Whether such records occur was not read. | minor |
| L3-6 (re-read) | `_tasks_query.py:438-453,424-427` | `--consumed-tokens` without `--completed-tasks-delta` | One input turns the mode on and an absent integer is `0`, so the classification leans towards `error`. | minor |
| L3-7 (re-read) | `_tasks_query.py:505` | A return with `verification_handback true` and any step id | Step ids are not checked against `phase_5.verification_steps` or the tier, so a stalled leaf can exempt itself from B7. | minor |
| L3-8 (re-read) | `execute-task/SKILL.md:314` vs `:316` | A leaf reads the heading literally | The heading says hand back "only when this task carries the deliverable's owed rung", while L316 says an absent stamp also branches on the live tier. | minor |
| L3-9 (re-read) | `execution.md:207-208` | A non-empty `pending_verify_steps` without the discriminator | Row 208 says a non-empty list is "the hand-back cause above, never this one", yet row 207 requires the discriminator, so the return matches no row. | minor |
| L3-10 (partly re-read) | `phase-5-execute/SKILL.md:1394` | — | "These two are the ONLY yields" contradicts the four sanctioned points at L136 and the three-outcome list at L1373 (L136 and L1373 not re-read). | minor |
| L3-11 (L929 re-read, refutation lead) | `phase-6-finalize/SKILL.md:929` | — | "kept consistent with the retrospective analyzer's failure-marker set … stay aligned" is said to be unsupported: the retrospective count comes from `script-failure-analysis.py`, which reads other logs and counts only exit codes 1 and 2. | minor |
| L3-12 (lead) | `_signal_scan.py:164` | A `[FAILED]` or `script_failure` line with no three-part notation | Goes to `unattributable_count`, so Signal 3 can under-count against the prior prose scan; that count gates lessons capture. | minor |
| L3-13 (lead) | `manage-tasks.py:485` | `--provisional-cause` typo | Any string is echoed back and fails only later at `record-dispatch-boundary`. | minor |
| L3-14 (lead, not shown) | `_cmd_client_build.py:400` | A configured, unmeasured value above the ceiling | `exceeds_bash_ceiling` comes from the stamp alone, so an unmeasured command could defer, against bullet 3. `timeout_get` for unmeasured keys was not read. | minor |
| L3-15 (re-read) | `phase-6-finalize/SKILL.md:925` | — | Transitional wording in current-state documentation ("the pre-fix behaviour"); `_signal_scan.py:15` and `manage-metrics.py:126` carry the same history (not re-read). | info |
| L3-16 (lead) | `manage-execution-manifest/SKILL.md:772`; `_signal_scan.py:206,74` | — | A dropped rung command is not restored when the stamp clears; every B7 reclassification counts as one notation; a log is read whole with graceful error paths. | info |

**Layer 3 not shown by reading:** L3-14 — whether `timeout_get` can return an unmeasured value above the ceiling; and every runtime property (the manifest bookkeeping under real compose runs, B7 against a real dispatch).

**Layer 3 verdict:** findings — 16 (one major, 13 minor, 2 info), no blocker.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | Current state only, no transitional information | deviates | `phase-6-finalize/SKILL.md:925` (re-read) |
| CLAUDE.md § Documentation Standards | No timestamps or version history | conforms | changed doc lines read by the leaf; not re-read |
| CLAUDE.md § Documentation Standards | No duplication, cross-reference | conforms | `phase-5-execute/SKILL.md` B7 restatement is now a pointer (leaf) |
| plugin-script-architecture | New verbs use `add_plan_id_arg`, `allow_abbrev=False`, kebab-case flags | conforms | leaf, diff of `manage-logging.py` |
| Spec constraint | Do not weaken the no-progress rule for a genuine stall | deviates | L1-1 (re-read) |
| Spec constraint | The owed hold stays; `loop-exit-guard` refuses a clean exit | conforms | `_tasks_query.py:385-404` (leaf; not re-read) |
| Spec constraint | Counts come from an enumeration, not a hand list | deviates | `== 14` and `== 8` hand counts in two tests (leaf; not re-read) |
| Spec D2 | The B7 citation names a section that exists | conforms | `execution.md:254` (re-read) |

## Metrics and Anomalies

- Tokens: `unknown` (not measured by the harness; recorded as unobserved).
- Duration: not reported.
- Anomalies: the build server was unreachable for the first half of the run, so every build ran in process (`in_process_fallback`, about 20 submissions, none routed); two bound expiries (`verify` at 1555 s, `module-tests` at 1500 s) were recorded and the gate completed through the split form. Corroboration against the session database was not done. Lane rule breaks as the lane discloses them: one guard refusal (`git grep` by the round-2 sub-agent), a refused heredoc edit, six read-class shell calls, and a commit trailer amended before its push.

## Routing and Merge Behavior

- Review (read from the PR): CodeRabbit reviewed `c7cac74c4` at 11:22 (one nitpick in the body, on `manage-tasks/SKILL.md`; the walkthrough's merge-risk note names the chain-tail double-ownership the lane calls the major), answered both later `@coderabbitai review` triggers (11:44, 12:37) with "Review rate limited", and filed a second review at 11:46 (not read). One review thread exists; its resolved state and the second review's body were not re-read, so "CodeRabbit confirmed the fix and resolved its thread" is an unverified lead. Sourcery refused both triggers on the 150,000-character limit.
- CI/merge: green on every head per the lane; merged through the merge queue (merge-group run completed with success); the merged head `032ac10db` is a merge of `origin/main`. No collision recorded with a running plan.
- Standing review authorization was applied by the lane (a qualifying CodeRabbit review on `c7cac74c4`, one re-trigger after the last push); consistent with the PR comments read.
- Sonar: `n/a` at both facts; the project has no Sonar, nothing to compare.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-109 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-109 --field pr --value 1911`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-109 --field landing --value landings/PLAN-LB-109.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-109-execute-prescribed-yield-not-error` (the sender's `{plan}`)
- [x] epic.md narrative reconciled (Queue annotations entry, Open Defect for the layer-3 major and the spec premise, Watch for the owed executor and the unverified review thread)
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- **Layer-3 defects reported to the operator in the same turn, nothing staged.** The two majors (L1-1, L3-1) sit on the very mechanism this plan was staged to make deterministic; staged as a fix plan only on the operator's word.
- **Spec edit owed (my spec's fault):** L1-2 and the lane's residue — the D4 unmeasured-arm Done-when. Recorded in epic.md; the shipped spec is not rewritten.
- **Not staged, under the focus rule:** the `verify` `timeout_seconds` sitting below the project's full-suite runtime (the lane's residue); Sourcery's 150,000-character limit; the documentation contradictions L3-8 to L3-11 and L3-15 (fold into a fix plan if one is staged).
- **Owed, operator-run:** none for this landing beyond the standing executor regeneration; the daemon path was never exercised by this run.
