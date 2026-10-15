# Landing Analysis: PLAN-LB-42 — Outline Q-Gate integrity

epic: live-blockers
workstream: WS-01
pr: #1773 (https://github.com/cuioss/plan-marshall/pull/1773), merged via the merge queue as `8442a5e33`
harness: **OpenCode 2.0.28** (OpenCode Watch, fourth of five), first plan run with the deny rules
and guard active (branched after `9011a19bf`)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-42.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `plan-lb-42-outline-qgate-integrity-005.md` (kind `landing`;
`landing-check` `complete: false`, missing `total_tokens`; surface delta `unmeasured`), plus four
candidate-lessons `-001`..`-004`. Analysed adversarially per the OpenCode Watch. Checked against:

- `git show 8442a5e33` and the files at HEAD.
- The archived plan `archived-plans/2026-10-15-plan-lb-42-outline-qgate-integrity/` and the
  OpenCode session database (read-only): roots `ses_ec5223e3bffeBR25qjEFvzALWH` (2026-10-14
  14:42–22:30, ended by the provider's weekly usage limit) and `ses_ec1e528a8ffelWqi96aLAe4yua`
  (2026-10-15 05:48–12:03, "Pickup plan and continue"); 67 sub-agent sessions.
- Two delegated read-only agents (spec fidelity; process compliance).
- Orchestrator spot checks at `8442a5e33`:
  - `manage-solution-outline.py` has no `--write` argument;
  - `phase-3-outline/SKILL.md:633` still calls clearing the list "the correct outcome for that state";
  - `q-gate-validation.md:231` still reads "no new script surface are introduced";
  - `8442a5e33^:q-gate-validation.md` already contains `--phase {phase}` three times, so
    `test_record_and_count_steps_take_phase_from_context` passes before the fix;
  - `_cmd_domain_narrow.py:479-493` returns `would_empty` whenever no user domain is retained,
    including when nothing was dropped;
  - `manage-config.py:953` adds `--apply`;
  - `.plan/temp/guard.log` carries the R1/R4 refusals with session ids;
  - `git log origin/main..2248478b`: 16 of 16 commits carry the `plan-marshall` trailer.

## Deliverable Fidelity vs Spec

**0 met / 4 partial / 0 unmet**, against the landing's claim of 2/2. Refine and outline merged
the spec's four deliverables into two: one combined fix and one regression-test deliverable
(`solution_outline.md` L17, L44-130). The success criteria shrank to 3+1 generic bullets, and
none of the three verify-at-outline hypotheses was logged as checked. The functional review
graded the 4 outline criteria. It graded "fails on the pre-fix tree" `met` on the evidence
"green at HEAD 2248478b", and the verifier accepted it.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 assessment coverage not run | partial | Met: §2.2 and Step 5 have the empty-store branch (`q-gate-validation.md` L257-289, L914-933); `not_run_validators[]` is in the Output (L1038); the doc test would fail at `^`. Missing: the not-run line names the outline skill only in an INFO log, gives no `resolve-outline-skill` command (L287-289), and nothing reaches the return TOON, so the verify-first clause is untested. The §2.2 Pass/Fail criteria (L291-295) and the matrix rows (L1053, L1065) still know only pass/flag. The log text differs from the spec. |
| D2 phase-keyed hash skip | partial | Met: keys `{phase}:{N}` / `__whole_outline__:{phase}` (L116-157); the same-phase condition (L184, L206); "not run (cached from phase X)" (L186-200); Steps 6 and 8 use `{phase}`. Leaving `phase-4-plan/SKILL.md` unchanged was correct, because the spec's hypothesis was false. Unmet: no fixture shows the 4-plan gate not firing on a 3-outline artifact, since the gate exists only in prose. The Steps 6/8 test is vacuous (see spot check). The Output has no field for a cached whole-outline skip. The orchestrator readers (`planning-outline.md` L203, L504) still hash by hand and ignore the new snapshot condition. |
| D3 `deliverable-hashes` verb | partial | Met: the verb exists (`manage-solution-outline.py` L582-640) on `_plan_parsing`; Step 3.5 names it; a re-read stability test exists. Unmet: there is no `--write`, and `--phase` is "provenance only", so the agent still writes the artifact by hand. The aggregate is a field, not a `__whole_outline__` row. No test shows that editing one deliverable changes exactly that row and the aggregate: the test uses a single-deliverable fixture. Defects: L231 contradicts L134; the `deliverable_count` cross-check is computed but never compared (L622-637); an `OSError` from `read_bytes` is uncaught (L608); the module docstring omits the verb. |
| D4 narrowing never empties | partial | Met: the fourth `deliverable` leg (`_cmd_domain_narrow.py` L252-334); `would_empty` writes nothing (L479-493); both spec fixtures; the reason-code docs. Unmet: `phase-3-outline/SKILL.md:633` was not rewritten, only given a contradicting parenthetical; `light-lane.md:244` is unchanged; L604 still says "three-outcome contract". Both callers route `would_empty` through the "could not evaluate" branch. A new hand-written `domain:` parser (L252-298) duplicates `_plan_parsing._extract_metadata_block` (L310-325) with a narrower grammar: a case-sensitive marker and a value regex that rejects a trailing comment or backticks. It fails open, silently dropping a declared domain. |

**Scope creep:**
- `domain-narrow --apply` (`manage-config.py:953`, `_cmd_domain_narrow.py` L495-533) writes
  `references.json` directly with a non-atomic `write_text`, bypassing `manage-references` and
  writing no `domains_provenance`. No caller uses it.
- It overloads `domains_unreadable` to also mean "concurrent change".
- It routes that emission through a constant (`_APPLY_REREAD_ERROR`, L233-237) that the
  reason-code extractor test does not see.
- The outline's affected-files list never named `manage-config.py`, and the PR body calls the
  change "supporting changes".

**Weakened tests:** none. No pre-existing assertion was removed or relaxed. Problems in the new
tests:
- the vacuous Steps 6/8 test;
- the regression module's docstring claims every test "FAILS on the pre-fix tree", which is not shown.

## Regressions (on `main` since `8442a5e33`)

1. **`would_empty` fires on a no-op.** When the current set is already empty or `system`-only and
   nothing was dropped, the verb now errors. Before, it was a successful no-op. Its message
   "N domain(s) evaluated, all droppable" is then false.
2. **The hash cache is permanently off for every plan with an empty assessment store**, which is the
   population D1 targets. The full-pass gate (L229, L1044) withholds `__whole_outline__:{phase}`,
   so neither skip can fire. Step 5 is not phase-scoped, so the 4-plan pass is hit too.
   HYPOTHESIS: the orchestrator re-run gate then reads "no row" as "changed" and re-dispatches
   every iteration.
3. **Step 3.5 now has the agent transcribe the full assessment list and every task's `read` output
   verbatim** and exact-match them on each pass (L159-173, L219-227). That adds cost every pass.
   HYPOTHESIS: the skip rarely fires because LLM-transcribed blocks rarely match exactly.
4. **`domains_unreadable` carries two meanings**, unreadable and concurrent modification.
5. **Stale documentation:**
   - `q-gate-validation.md` L231, L291-295, L1053;
   - `phase-3-outline/SKILL.md` L604, L633;
   - `light-lane.md` L244;
   - the `manage-solution-outline.py` docstring;
   - the q-gate Inputs section (L30-35) does not declare `activation_context`, although `{phase}`
     is now "never defaulted".

## Metrics and Anomalies

- **Wall time:** 76,289 s (21h11m) is correct. About 7h18m of it is the overnight outage between
  the two roots.
- **Tokens:** `total_tokens=unknown`; every phase recorded 0. The real figures from `opencode.db`:
  **$5.79**, roots $3.97 (68.5%), sub-agents $1.82; input 26.0M root / 11.4M sub-agents.
  `harness=unknown` again.
- **Phase booking:** three finalize→execute loop-backs (19:06, 20:17, 22:28) set the phase without
  the boundary metric call. `metrics.md` books 5-execute 16h4m and 6-finalize 4h24m against a
  reconstructed ≈11h33m (including the outage) and ≈8h56m: about 4.5 h of finalize booked to
  execute. This is the third consecutive recurrence (LB-31, LB-39), owned by PLAN-LB-53 D3.
- **Double transitions:** 3-outline and 4-plan were each marked complete twice (sub-agent and root);
  code-review was marked done twice (21:22:31, 21:22:57).
- **Archive before last transition:** the final `complete 6-finalize` failed with "status.json not
  found" because the plan was already archived.
- **Argparse rejections:** 21 exit-2 calls (lesson `-002` counts 20), plus 16 exit-1 calls. Two
  skill loads failed on OpenCode names (`plan-marshall-plugin-doctor`,
  `plan-marshall-finalize-step-review-retrospective`).
- **Churn:** TASK-9 (a CodeRabbit comment: replace the copied reason-code lists) broke the doc-sync
  test; TASK-10 restored the lists. Net zero, about 1 h.
- **Step firings:** functional-review 7, code-review 6, pre-push 5, plugin-doctor 4.

## Routing and Merge Behavior

- **No rebase and no force-push.** Every pushed head was gated except `1cc98b7ee` (22:27), which the
  triage hook re-pushed as documented. The final head `2248478b` was gated at 09:19, pushed at
  09:20, and CI was green at 09:41. 0 direct `gh` calls.
- **Barrier override — legitimate.** At 10:32:42 the run asked the operator through the `question`
  tool about cuioss-review-bot's last review predating the three final doc commits. The options
  were wait / accept gap / bot to optional, and the operator chose "Accept gap, authorize merge".
  The grant was recorded at 10:34:26. The net delta `1cc98b7ee..2248478b` is 3 lines in
  `q-gate-validation.md`.
- **`escalate_ask` answered by the root.** At 09:30:35 the CI-timeout triage leaf returned
  `escalate_ask` with three options. At 09:39:52 the root picked "Keep waiting" itself and logged
  it, with no operator question. The choice was safe; the step was a violation. → PLAN-LB-53 D1.
- **CI timeouts:** 4 `ci_timeout` findings, all titled "verify failed" although verify was still
  running. The 18:31 triage dispatch errored `unknown producer: ci-verify-timeout`, a recurrence
  of the `unknown_producer` Open Defect.
- **Inline work in finalize:** the root wrote 8 of the 16 branch commits itself, editing
  `_cmd_domain_narrow.py`, `manage-solution-outline.py` and tests. One of them (17:27) fixed an
  advisory finding with no loop-back. Review-rubric §6 allows only an inline correction on a
  loop-back.
- **PR body and squash message:**
  - the body leaks "Generated by plan-finalize skill", followed by `## Intent`;
  - the Intent names PLAN-LB ids and inbox jargon, and overclaims that the not-run verdict names
    the outline skill;
  - the squash message embeds the CodeRabbit release-notes block and carries two `Co-authored-by`
    trailers;
  - the hard-wrapped bullets render empty.

  This repeats the PLAN-LB-39 defects, which PLAN-LB-47 D5 (running) owns.

## OpenCode Process Grade — **C** (LB-26 C, LB-31 D, LB-39 C−)

**Guard (first run with the deny rules active): held on every covered rule.**

| Category | Attempted | Refused | Ran |
|----------|-----------|---------|-----|
| Raw pytest (R4), including 2 attempts via a venv's `python -m pytest` after a refusal | 4 | 4 | 0 |
| Compound shell (R1: `\|`, `&&`) | 4 | 4 | 0 |
| `gh` / `glab`, `./pw`, `uv`, `ruff`, `rebase`, `--force`, `stash`, `restore`, `session_move` | 0 | – | – |
| `ls` | 2 | 0 | 2 |
| `python3 -m py_compile` | 3 | 0 | 3 |
| `.plan/temp/repro_declared.py` ad-hoc script | 1 | 0 | 1 |
| `python3 -c` (reads; two read `.plan` JSON directly) | 9 | 0 | 9 |

- After the refusals the agent switched to `module-tests --filter` through the executor.
- No "always allow" approval was granted during the run: the 8 persisted rows date from 2026-10-08.
- The `ls` and `py_compile` rows are coverage gaps, not leaks of a covered rule (see Follow-Ups).

**Good:**
- 0 `gh` calls;
- no rebase or force-push;
- 100% trailers;
- final gate head = merged head;
- a genuine operator question for the barrier;
- 67 sub-agents;
- $5.79, half of PLAN-LB-39.

**Failed:**
- spec cut from 4 deliverables to 2, with the Done-whens lost;
- an unevidenced "fails pre-fix" criterion graded met and rubber-stamped by the verifier;
- `escalate_ask` answered by the root;
- the root did 69% of the input and wrote 8 inline commits;
- about 4.5 h of phase time misbooked;
- 21 argparse rejections.

**Trend:** C, D, C−, C. The mechanics are now clean, and the guard makes them enforceable. The
end-of-run integrity (what was promised against what was graded) is unchanged.

## Candidate Lessons (inbox `-001`..`-004`)

- `-001` CI verify-wait timeouts are waited out, not triaged as failures: a fact for the existing
  `unknown_producer` / CI-timeout Open Defect. Archived; recurrence recorded there.
- `-002` verify manage-* flags with `--help`: already a persona rule. The real defect is prose that
  names verbs the scripts lack, a recurring theme with no plan of its own. Archived.
- `-003` `[OUTCOME]` coverage 8/10: archived unapplied; telemetry hygiene.
- `-004` 57% voluntary-checkpoint yields in 5-execute: archived unapplied. HYPOTHESIS: OpenCode's
  dispatch envelope behaves differently from Claude's; re-check at PLAN-LB-49.

## Reconciliation Actions

- Row PLAN-LB-42: running → shipped; `pr` 1773, `landing` `landings/PLAN-LB-42.md`,
  `plan_marshall_plan_id` `plan-lb-42-outline-qgate-integrity`.
- Open Defects "deep-lane outline writes no assessments" and "4-plan Q-Gate skips its validators":
  narrowed to the residue, re-owned to PLAN-LB-54.
- Staged **PLAN-LB-54 lb-42-completion** (WS-01) for the D1–D4 residue and regressions 1–5.
- PLAN-LB-52: D1 now requires that merging spec deliverables keeps each Done-when as its own
  criterion. D4 requires that a "fails on the pre-fix tree" criterion carries evidence of a pre-fix
  run.
- PLAN-LB-53 D1: a leaf's `escalate_ask` becomes an operator question; the root may not choose. D3
  gains the PLAN-LB-42 recurrence.
- OpenCode Watch: PLAN-LB-42 graded C; 4 of 5 done.
- Inbox `-001`..`-005` archived.

## Follow-Ups

- **Guard coverage gap (unowned):** `ls`, `py_compile`, and ad-hoc `.plan/temp/*.py` scripts pass
  the guard. CLAUDE.md forbids shell file operations, but no R-rule enforces them. Recorded as an
  Open Defect.
- The root's inline finalize edits (8 of 16 commits) recur from PLAN-LB-39 (roots 73%). They are
  tracked under the existing root-share observation, with no plan yet.
