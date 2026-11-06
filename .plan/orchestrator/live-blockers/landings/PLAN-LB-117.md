# Landing Analysis: PLAN-LB-117 — a stall beside a hand-back is decided, the delta has a source, the owed-rung bookkeeping holds

epic: live-blockers
workstream: WS-01
pr: #1918

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-117.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `c394a95fb63fb2ea151db569fcf7368465ef3b39`, a squash commit with ONE parent, `3404d904c8500c9ef0a6f2f301bff33a64fc3152` (the merge of PLAN-LB-114, read with git and named in the leaf prompt). Landing message `rb-lb-117-execute-handback-fix-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule); its surface delta is `unmeasured`, so the surface was read from the diff: 28 files, +943/−145 (`git show --stat c394a95fb`). The lane reports 5 of 5 deliverables done, `self-review: clear` after four rounds, a spec read from the ledger copy. The merge is the lane's claim for CI and reviews; git confirms the squash commit and its subject.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a stall beside a hand-back is decided; the hand-back's step ids are checked | shipped, with a regression lead (L3-3) | `evaluate_no_progress` now consults the predicate before the hand-back and checks the named ids against the manifest's list (`_tasks_query.py:613-631`, re-read). The decision line is orchestrator prose (`execution.md:256-262`), so the Done-when's "decision line written" has no test and cannot have one. |
| D2 — `completed_tasks_delta` has a source; an absent input is not zero | shipped-modified | The refusal is as specified: `_int_arg` keeps absence apart from `0` and the evaluation is refused as `no_progress_not_decidable` with the queue verdict kept as `queue_status` (`_tasks_query.py:438-461, 478-487`, re-read). The source is named, `done_count` (`:396, :406`, re-read), but the documented sequence cannot be followed (L3-1). |
| D3 — the owed rung is defined once; the unmeasured arm is tested on the leaf side | shipped | The definition is in `manage-execution-manifest/SKILL.md` (leaf). `exceeds_bash_ceiling` is now `measured and … > ceiling` (`_cmd_client_build.py:405-408`, re-read). The leaf-side test covers `finalize-step`'s hold, not the leaf's choice to pass the flag (L2-1). |
| D4 — one tail command per deliverable | shipped-modified | Stale stamps are now cleared per (deliverable, command) and a second command does not overwrite the first. The command that is recorded is not always the command the decision was taken on (L3-2). |
| D5 — contradicting documentation lines agree | shipped as specified, not re-read | Doc read by the leaf; the leaf found residual drift in three lines (see L3-7). |
| not a deliverable | not measurable | `landing-check` surface delta `unmeasured`. The lane names two files outside the declared surface and says both were required; the leaf did not find an unexplained one. |
| executor regeneration | corroborated | `git diff 3404d904c c394a95fb -G 'add_parser|add_argument' --stat` is empty (orchestrator), so no verb or flag was added and the lane's "not owed" holds. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing; the orchestrator re-read the points marked `re-read` at their `file:line` in the merged tree. It was a reading only: no build, no test run, no write. The leaf had no Grep and enumerated the readers of `exceeds_bash_ceiling` with git-only reads.

- **Dispatch:** one read-only leaf per landing — the read crosses 28 files and must not share context with the other landing read in the same firing.
- **Verdict:** layer 1 findings (two minor); layer 2 findings (minor and info); layer 3 findings (**two major, one major lead**, minor, info), no blocker.
- **Orchestrator re-read:** L3-1, L3-2, L3-3 (code half), L3-4, L3-5, L3-6 (code), L2-1, L2-3, L1-1 and L1-2 (code). Every other row is a lead the leaf checked and I did not re-read.
- **Correction of the leaf's return.** The leaf graded L2-1 `major`; I carry it as minor, with the reason below. It also wrote that the lane listed `test_a_handback_alone_stays_the_handback_cause` as red at base; the lane's own narrative calls that test a control, green at base. The leaf's wording came from my prompt, which compressed three tests into one "red at base" clause. That finding is dropped.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (minor, re-read) | D1 says a hand-back "exempts only the owed task(s) it names", but a hand-back names step ids, not tasks. The implementation is the old owed-task subtraction plus a classification order; no link from a step id to a task exists or is checked. | checked | `_tasks_query.py:613-619` |
| L1-2 (minor, re-read) | D1 says the ids are checked against the manifest's list "for the deliverable". The manifest carries one plan-wide `phase_5.verification_steps` list, so an id composed for another deliverable is accepted. | checked | `_tasks_query.py:549-552` |
| L1-3 (info) | D3's rule "an unmeasured command above the ceiling must not defer" was not decidable from the stamp alone at the base: an unmeasured stamp above a low ceiling showed `exceeds=true`. The leaf confirmed the bug at the base; the fix is the `measured` gate. | checked (base read by the leaf) | `_cmd_client_build.py:405-408` (merged form, re-read) |
| L1-4 (info) | The standing constraint names a `PLAN_MARSHALL_HOME` fixture; `test/conftest.py` has none (`plan_context` isolates through `PLAN_BASE_DIR`). | checked (leaf), not re-read | `test/conftest.py:2297-2326` |

**Layer 1 verdict:** findings — 2 minor, 2 info.

### Layer 2 — Implemented

- **L2-1 (minor, re-read; the leaf graded major):** the D3 leaf-side tests call `cmd_finalize_step` with `owed=True` for every task themselves (`test_unmeasured_rung_owed_hold.py:87, :111, :118`), so they exercise the hold `finalize-step` keeps, not the leaf's choice to pass `--verification-owed`. They are red only under a mutation of `finalize-step`, which is what the lane says (mutation-after) and what the Done-when asks ("fails against a stub that puts the hold on a single task"). The leaf side stays pinned by document-text assertions only; there is no test of prose behaviour that could be written. Not carried as major because the Done-when as written is met.
- **L2-2 (minor, leaf, not re-read):** untested branches: a hand-back naming a mix of valid and unknown ids, a missing or unreadable manifest (`_tasks_query.py:531-551` fail-closed paths), and a non-empty `verification_handback_unknown_steps`.
- **L2-3 (info, re-read):** the standing constraint "counts come from an enumeration, not a hand list" is met by a named frozenset (`test_manage_metrics_dispatch_termination_causes.py:136-160`), which the leaf grades as a hand list. It compares the constant's membership with a declared set, so a member added forces a deliberate edit; the spec's literal "the constant they count" would be a tautology. I carry it as a wording gap in the spec, not a defect. The second site (`test_qgate_doc_contract.py:58-91`) was not re-read.
- **L2-4 (info, leaf):** the decision-line Done-when ("with the decision line written") is traced to `execution.md` prose only; the marker text says "reclassified voluntary_checkpoint as error" (`execution.md:261`), accurate to the provisional cause the call passes.
- **L2-5 (info, leaf, not re-read):** the claim "the only production consumer of `exceeds_bash_ceiling` is the deferral" holds for cross-module code (every tracked file enumerated); the producer also selects the hint from it, so the hint for an unmeasured over-ceiling stamp changed to `_HINT_UNMEASURED`.
- Red-at-base for the stall-beside-hand-back, unknown-step, both not-decidable, and `done_count` tests was established by the leaf reading the base code, not by a run; the per-head test and verify runs are the lane's claim, `not_shown_by_reading`.

**Layer 2 verdict:** findings — 2 minor, 3 info.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `execution.md:239, 247-254`; `_tasks_query.py:396, 406` | Any B7 evaluation, above all the first one of a plan | The document says both done counts come from "the loop-exit-guard call below", but that call takes `--completed-tasks-delta` as input, so the current count is known only from the call that needs it. The first dispatch has no previous snapshot, and the old "or 0 on first iteration" rule was removed (`:239-240`). The code is fine: a plain call reports `done_count` (`:396, :406`), and the pre-dispatch peek is a plain call (`:270-275`). What is missing is the sequence: snapshot with a plain call before the dispatch, subtract after. The snapshot also lives only in orchestrator context, so a resume loses it. An orchestrator that follows the text literally either has no delta (refused, "no dispatch may be classified from that result", `:254`) or invents one, which is what D2 forbids. | major |
| L3-2 (re-read; effect derived by reading, not run) | `manage-execution-manifest.py:1343-1362, 1517-1551` | One task listing an unmeasured module-tests command B first and a measured over-ceiling command A second | The decision pass admits a command only when its tier is `orchestrator` AND `exceeds_bash_ceiling` is true (`:1359`), so A decides. The routing pass records the FIRST module-tests command whose tier is `orchestrator`, qualifying or not (`:1517, :1543-1551`), so B is recorded as `owed_rung_command`. A re-compose re-measures the recorded command (`:1346-1352`): B does not qualify, the dropped commands are gone, the task leaves its group, its stamp is cleared as stale, and the chain tail moves to an earlier task. The re-compose is not idempotent. `manage-execution-manifest/SKILL.md:779` describes the qualifying-command rule, not the code (leaf, line not re-read). | major |
| L3-3 (code re-read; precondition not settled) | `_tasks_query.py:613-631`; `phase-5-execute/SKILL.md:1104` | A `running` hand-back (or the Step 11b/11c hand-backs) from a dispatch whose task is `in_progress` without `verification_owed`, with delta 0 and more than 50,000 tokens | The predicate now decides before the hand-back, and subtracts only tasks held open with `verification_owed` (`:613`). A hand-back whose task is not owed counts as in-progress and the dispatch is classified `error`, which the prior order prevented. The `running` text says the leaf "leaves the verification uncut" and names no owed flag (`phase-5-execute/SKILL.md:1104`). `execution.md:242` assumes every hand-back's task is owed. Whether that task is `in_progress` at the return, and whether such a dispatch burns that many tokens, I did not establish; the text of the Step 11b/11c hand-backs was not read. | major (lead) |
| L3-4 (re-read) | `_tasks_query.py:478-487, 615` | A negative `--completed-tasks-delta` (a done task reopened) or a negative token figure | `type(value) is int` accepts any integer; `predicate_holds` needs `delta == 0`, so a negative delta reads as progress and suppresses a genuine stall. Fail-open on an invalid input, against the owner's fail-closed rule. | minor |
| L3-5 (re-read) | `_tasks_query.py:625-627` | `--verification-handback` with an empty or unknown step list and a holding predicate | The reason `no_progress_predicate_holds_beside_handback` is chosen on the bare flag, so it names a hand-back that was not a valid one. | minor |
| L3-6 (re-read, one reader not read) | `_cmd_client_build.py:486, 533, 538` | A narrow-unit resolve that falls through to the default stamp above a low ceiling | `_bounded_tier_fields` passes `measured=True` (`:486`), so a stamp that is only a default reports `exceeds_bash_ceiling` true, against the contract that an unmeasured command carries false (`resolve-command.md:18`, leaf). The leaf says the deferral does not use narrow-unit resolves (`manage-execution-manifest.py:1179-1189`, not re-read); whether the default can exceed a ceiling I did not read (`_narrow_default_stamp`). | minor |
| L3-7 (leaf, not re-read) | `_tasks_query.py:617-619`; `_cmd_client_build.py:58-67`; `phase-6-finalize/SKILL.md:929`; `phase-5-execute/SKILL.md:662-665, 1394`; `manage-metrics/standards/data-format.md:1053` | — | A mixed valid and unknown id list is wholly invalid (fail closed, per the spec); the module docstring still labels the unmeasured hint "within ceiling"; the retrospective reads `script-execution.log` and `work.log`, not only the first; `:662-665` still says "its deliverable's rung" after the grouping moved to (deliverable, command); `:1394` names no cause for a stall that reclassifies a hand-back; the line "the handed-back task never counts toward the predicate" holds only for an owed task. | minor / info |
| L3-8 (leaf, not re-read) | `manage-execution-manifest.py:1249-1277, 1371-1390`; `_cmd_step.py:146-151` | A dependency cycle; a `null` verification | `_chain_order` terminates (a visited set; cycles fall to number order), each task joins one (deliverable, command) group so each group has one tail, and every other `verification` reader is guarded. | info |

**Layer 3 verdict:** findings — two major (L3-1, L3-2), one major lead (L3-3), L3-4 to L3-6 minor, the rest minor and info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `10e9c11d4` and `f2ac8d61a`, refusing on quota for the later heads, and the standing authorization applied for the final head `a5d23e4ed`; Sourcery (optional) refused on its own 250,000-character budget. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `c394a95fb` and its subject. The lane's account of CodeRabbit's three findings on the last review (the outside-diff `0` substitution, the queue-verdict overwrite, the broad `except`) is its own; the code at `_tasks_query.py:449-461` and `:531-543` shows the refusal that keeps `queue_status` and the narrowed `except`.

## Residue and Watches

- The three major findings want a fix plan; it is staged on the operator's word only. They share the surface of this plan (`execution.md`, `_tasks_query.py`, `manage-execution-manifest.py`, and the tests beside them), so the fix plan is a candidate to run ahead of the plans that share those files.
- L3-3 is to be settled first at that plan's outline: is a `running` or Step 11b/11c hand-back's task `in_progress` without `verification_owed`? If so, D1's order produces a false `error` on a prescribed yield.
- Harness sync is owed outside this plan, operator-run (the spec's Dependencies section states it).
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule breaks (one `git add -A`, three own argparse rejections, `tail` and `wc` on logs, two guard refusals) are the lane's own account and are not re-read; no restart and no model switch were reported.
