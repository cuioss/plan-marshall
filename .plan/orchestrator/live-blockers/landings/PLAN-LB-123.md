# Landing Analysis: PLAN-LB-123 — the delta has a workable source, the manifest records the command it decided on, and a prescribed hand-back is not reclassified

epic: live-blockers
workstream: WS-01
pr: #1933

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-123.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `323bc766cf38bb98967bc65540f9f15f489c0727`, a squash commit with ONE parent, `5cd8ccd92e03f09ea64d45b1e943a93c61c2cc14` (the ledger land of PR 1935, read with git and named in the leaf prompt). PR 1933 is `merged` (read with `ci pr queue-state`; merge-group run 42402408596 completed with success). Landing message `rb-lb-123-execute-handback-and-manifest-gaps-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 13 files, +546/−49 (`git show --stat 323bc766c`). The lane reports 5 of 5 deliverables, `self-review: clear` after three rounds, CodeRabbit reviewing the final head with no actionable comment, and a spec read from the ledger copy. The argparse surface is unchanged (no verb or flag added), so no executor regeneration is owed; a harness sync is owed (operator-run). The checkout HEAD had moved on only by ledger lands (`6e3391f9b`, `5cd8ccd92`), so every cited file reads the same as at the merge.

Surface against the spec's Expected Surface: the lane's statement "every touched file was on the spec's Expected Surface" is **false as worded**. Four touched files are not named by it: `manage-metrics/SKILL.md`, `manage-tasks/SKILL.md`, `test_cmd_resolve_narrow_target.py` and `test_manage_metrics_verification_handback.py`. Each is explained by a deliverable (the D3/D5 lock-step restatements, the D4 `_bounded_tier_fields` fixture, a doc assertion that followed the changed wording), so no touched file is unexplained. Three Expected-Surface files were not touched: `manage-execution-manifest/SKILL.md`, `test_unmeasured_rung_owed_hold.py`, `manage-tasks.py` (the last is conditional on D1 extending the row, which it did not).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the B7 text yields the delta by a followable sequence | shipped; the post-build re-entry text can still skip the snapshot (L3-3) | `execution.md:239` names the plain call before the dispatch, the plain call after, the subtraction and the resume re-derivation (re-read). The row `record-dispatch-boundary` carries no done count (`manage-metrics.py:3795-3807`; leaf), so re-derivation was chosen. `TestExecutionDocStatesTheDeltaSequence` has 2 tests; the first-dispatch refusal rests on the pre-existing absent-delta fixture. |
| D2 — the manifest records the qualifying command, a re-compose is idempotent | shipped | `manage-execution-manifest.py:1516-1524,1537-1541,1572,1577` (re-read, with the diff against the parent): the parent recorded the first orchestrator-tier command; the merge records only a qualifying one and keeps a recorded command that still qualifies. `SKILL.md:779` is unchanged and does not state the keep-recorded precedence (L2-1). |
| D3 — a hand-back whose task is not owed is shown safe or classified by a stated rule | shipped, reachable arm (stated rule) | `_tasks_query.py:620-629,656-668` (re-read): one in-progress task is credited to the return's own marker when no owed task is in flight; a further non-owed task still decides `error`. The reach of the >50,000-token case stays `not shown by reading`, as the lane says. |
| D4 — the minor edges of the evaluation and the stamp | (a)(b)(c) shipped; (d) met only by the PR text; (e) refuted correctly | (a) negative delta and tokens refused, (b) the reason keys on `handback_valid` (`_tasks_query.py:679`, re-read), (c) `measured` is a required keyword of `_bounded_tier_fields` (`_cmd_client_build.py:477-509`; leaf). (d): the diff does not touch `test_unmeasured_rung_owed_hold.py`; the "pinned by text only" statement exists only in the squash commit message, and the test docstring (`:14-18`, re-read) still claims it discriminates a one-owed-build stub (L2-4). (e): the hand counts were already named frozensets at `c394a95fb`, so the spec premise was false and the lane's refutation is right (L1-1). |
| D5 — the contradicting and transitional lines agree | shipped with residue | The cited lines are reconciled; sibling lines still say the old thing (L2-2, L2-3, L2-5). |
| executor regeneration | not owed | The diff adds no subcommand, flag or parser argument (leaf). |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit. It wrote nothing and ran nothing. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf — the read crosses 13 files and the layer-3 reach analysis of one predicate; 8 narrative claims passed one by one.
- **Verdict:** layer 1 findings (minor, info); layer 2 findings (minor, info); layer 3 findings (minor, info). **No blocker, no major.**
- **Orchestrator re-read:** L3-1 and L3-2 (`_tasks_query.py:620-629,656-668`), L3-3 (`execution.md:239,254-256,268,272`), L2-1 (`SKILL.md:779`), L2-2 (`phase-5-execute/SKILL.md:1104`), L2-3 (`execution.md:268`), L2-4 (`test_unmeasured_rung_owed_hold.py:1-19`), L2-5 (`_cmd_client_build.py:50-69`), and the manifest script change against the parent. Every other row is a lead the leaf checked and I did not re-read.
- **Prompt check.** The 8 claims went into the prompt as separate items.
- **Not read by the leaf:** CI and job logs, the PR review bodies, `analyze-logs.py` (so `phase-6-finalize/SKILL.md:929` is unconfirmed), the runtime behaviour of any fixture.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at 323bc766c) |
|---------|-------|---------|-----------------------------------|
| L1-1 (minor, leaf) | D4(e): the `== 14` and `== 8` hand counts are replaced | the spec premise is false: both were already named frozensets at `c394a95fb` | `test_manage_metrics_dispatch_termination_causes.py:136-153`; `test_qgate_doc_contract.py` at `c394a95fb` |
| L1-2 (minor, leaf) | D5: `data-format.md:1053` "reads the same two logs the code writes" | misattributed: the line is the `termination_cause` enum sentence and names no log | `manage-metrics/standards/data-format.md:1053` |
| L1-3 (info, leaf) | D4: each shape is a fixture red at `c394a95fb` | cannot hold for the mixed, missing and unreadable-manifest branches, which already failed closed at the parent | `_tasks_query.py:653-655`; `test_manage_tasks_loop_exit_guard.py:702-760` |
| L1-4 (info, re-read) | D2: the routing pass records the first orchestrator-tier command | holds at the parent (persisted as `corroborated`) | `manage-execution-manifest.py:1537-1541` against the diff |
| L1-5 (info, leaf) | D3: a `running` hand-back leaves its task `in_progress` without `verification_owed` | holds; the owed hold opens only when all steps are terminal | `_cmd_step.py:154` |

**Layer 1 verdict:** findings — two minor premise errors, the D1, D2 and D3 premises hold. The D3 token-reach half of its hypothesis stays unmeasured, so no verdict is persisted for it.

### Layer 2 — Implemented

- **Confirmed:** D1 (text and the 2 doc tests), D2 (the new class, with the matched control), D3 (`test_manage_tasks_loop_exit_guard.py:594-641`, the owed control at `:420-438`), D4(a)(b)(c), the C7 claim of no executor change.
- **L2-1 (minor, re-read):** `manage-execution-manifest/SKILL.md:779` still reads "the first QUALIFYING `module-tests` command the routing pass sees". The merged routing pass gives precedence to an already-recorded qualifying command (`manage-execution-manifest.py:1516-1524`), and that rule is stated only in a code comment.
- **L2-2 (minor, re-read):** `phase-5-execute/SKILL.md:1104` says a prescribed `running` hand-back "is never reclassified as a stall". When an owed task is in flight the credit is withheld (`_tasks_query.py:667`), so a `running` hand-back on a not-owed task beside an owed task, with delta 0 and more than 50,000 tokens, is classified `error`. The sentence overstates.
- **L2-3 (minor, re-read):** `execution.md:268` — "no non-owed in-progress task, OR …" — was not updated for the hand-back credit: one non-owed task plus a valid hand-back also makes the predicate false.
- **L2-4 (minor, re-read):** D4(d) is met only through the "or the PR states" arm; the statement lives in the commit message alone, and the test docstring still claims a discrimination it cannot make.
- **L2-5 (info, re-read):** `_cmd_client_build.py:55-57,59` still says the unmeasured branch is "the ONE place" tier and `exceeds_bash_ceiling` decouple and lists "all three reachable states"; the narrow-default path adds a further state.
- **L2-6 (minor, leaf):** the documentation-standards "no duplication" rule is deviated from: `phase-5-execute/SKILL.md:1369` says the exemption is "stated once in execution.md … not restated here" and restates the credit rule in the next sentence; the credit rule now appears in `execution.md:207,242`, `phase-5-execute/SKILL.md:1104,1369,1394`, `manage-tasks/SKILL.md:182-186`, `manage-metrics/SKILL.md:446` and `data-format.md:1053`.
- **Lane claims contradicted:** "no surface drift" (above). Not shown by reading: which fixtures are red at `c394a95fb` (reasoned from code, not run).

**Layer 2 verdict:** findings — one claim contradicted (surface), one clause met only by prose, five doc residues, the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_tasks_query.py:667` | One non-owed `in_progress` task, `owed_count` 0, a valid hand-back whose ids are all composed (any step, not necessarily that task's), delta 0, more than 50,000 tokens | The credit counts tasks and does not know which task the hand-back is about, so the dispatch is `verification_handback` rather than `error`: a genuine single-task stall beside an unrelated valid hand-back is hidden. Bounded to one task, and the docstring (`:620-629`) admits the conservative count. Whether a leaf can produce this shape is not shown. | minor |
| L3-2 (re-read) | `_tasks_query.py:667`; `execution.md:242,256` | A build that keeps outliving the wrapper bound: dispatch, `running` hand-back, re-attach, re-dispatch, repeated on the same not-owed task | The credit has no memory across dispatches, so each repeat is credited again; with the lane's own C6 residue (a successful re-attach closes only owed tasks) B7 no longer stops this non-progressing loop, which it classified `error` before the merge. Whether the loop can occur is not shown by reading. | minor |
| L3-3 (re-read) | `execution.md:239,254,272,256` | A reader of the post-build re-entry, which says to re-dispatch "WITHOUT the pre-dispatch queue peek" (the same plain call); or a resume between a dispatch's return and its evaluation | The before-snapshot step is stated only in the B7 "where" bullet, not in the dispatch block, so the re-entry can skip it; the next evaluation is then refused `no_progress_not_decidable` and the dispatch is recorded `error`. Fails closed, but forces an escalation. | minor |
| L3-4 (leaf) | `test_manage_tasks_loop_exit_guard.py:747` | the fixture `not: [valid: toon` | Whether it makes `parse_toon` raise (`_tasks_query.py:569-570`) or parse to a dict with no `phase_5` (`:573-575`) is not shown; the fixture may not exercise the parse-error branch. | info |

**Layer 3 verdict:** findings — no blocker, no major; three minor (L3-1 to L3-3), one info. None fails open in a shape normal use produces, as far as a reading shows: L3-1 and L3-2 need a leaf shape nobody showed, and both fail toward an extra dispatch, not toward a false pass of a gate.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `717839704`, `4ec071cc4`, `127903e18` and the final head `b3453af85` (no actionable comments), seven threads resolved, two (C5, C6) accepted as pre-existing residue; Sourcery (optional) refused on its own diff budget. I read no review body and no CI output: the review history and the CI result are the lane's claim and are `not_shown_by_reading`. Git and `ci pr queue-state` confirm the squash commit `323bc766c`, its subject and the merged state.

## Residue and Watches

- No major layer-3 finding, so no fix plan is staged. Under the stop rule (a fix plan only for a major that fails open or falsely blocks a gate in normal use) L3-1 and L3-2 are carried as a Watch; the doc residues (L2-1, L2-2, L2-3, L2-5, L2-6) and L3-3 ride on files (`execution.md`, `phase-5-execute/SKILL.md`, `manage-execution-manifest/SKILL.md`, `_cmd_client_build.py`) the next plan touching them carries. PLAN-LB-124 and PLAN-LB-126 touch none of the first three except `execution.md` in PLAN-LB-126; the carry is a note on PLAN-LB-126, not a deliverable.
- Settle first, if the operator stages a plan: whether a `running` hand-back's step id can name a step of a task other than the in-progress one (the leaf could not show which id a Step 11 hand-back carries), and whether a repeated `running` hand-back on one task occurs in practice.
- **Lane residue C5 (job id in the hand-back return) and C6 (a re-attach does not close a not-owed task's verification step):** named by the lane as pre-existing; the leaf found the merged code does not worsen C5 and removes B7 as a backstop for C6's loop (L3-2).
- Owed outside this plan, operator-run: a harness sync. No executor regeneration.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (one `R1` guard refusal re-issued as a single command; two read-class shell file operations self-reported) is its own account and is not re-read.
