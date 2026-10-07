envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-02T13:39:07Z

## Delegation from `review-apparatus` — 13 items from PR #1077 / #1078

**REMOVED from the review-apparatus ledger.** Sources: plan `barrier-override-not-head-bound` (PR
**#1077**, merged `2026-08-02T12:39:52Z`) and plan `correct-review-scores-as-maximally-wrong` (PR
**#1078**). Twelve sibling messages were RETAINED as review-domain; these thirteen are yours.

---

## ⛔⛔ READ THIS FIRST — four of these are REPEAT sightings of items already delegated to you

This is the signal, not the items. The following recurred in a *new* plan's finalize after already
being handed over:

| Item | Prior delegation | Sighting |
|---|---|---|
| Retrospective reads a worktree `branch-cleanup` already deleted | `review-apparatus-008` item 3, `-010` item 5 | ⛔ **THIRD** |
| `check-routing-decisions` fabricates a `mis_prune` | `-010` item 4 | **SECOND** |
| No `[DISPATCH]` line on a re-fired finalize step | `-010` item 9 | **SECOND** |
| Retrospective step ordering (17 after 16) | implied by the above | **SECOND** |

⭐ The retrospective/worktree one now has a **self-documenting** instance: during #1077's finalize,
`finalize-step-lessons-housekeeping` explicitly RETAINED lesson `2026-07-28-19-005` noting *"a
finalize-pipeline fix still cannot be self-verified by its own run"* — **and the predicted failure then
occurred in the very next step.** The apparatus wrote down what was about to break, then broke that way.

⇒ Treat these as **one ordering defect with four symptoms**, not four bugs.

---

## The thirteen

### 1. ⭐⭐ Derive the footprint from the merge commit when the worktree is gone (THIRD sighting)
`component=plan-marshall:plan-retrospective` · bug · high

`check-artifact-consistency` derives the footprint live from the plan worktree; `branch-cleanup` (step
16) deletes it before `plan-retrospective` (step 17) reads it. Reported `affected_files_recall: fail —
Recall 0%`, all nine declared files `missing`. **True recall was 100%** — merged squash `967ba03f5`
contains exactly the nine files `references.json` declared. The documented fallback
(`references.modified_files`) is legacy-only and was removed from live plans, so **no surviving source
exists**. ⛔ Produces a confident, specific, WRONG fail rather than an "unknown".

### 2. Order `plan-retrospective` before `branch-cleanup`
`component=plan-marshall:manage-execution-manifest` · bug · high

The root cause of item 1. ⭐ The framing that generalises: ordering by *"what logically concludes the
plan"* rather than by *"what each step needs to still exist"* produces destruction-before-read.

### 3. `check-routing-decisions` blames the prune predicate for a posture-cutoff drop (SECOND)
`component=plan-marshall:plan-retrospective` · bug · high

Emitted `mis_prune:sonar-roundtrip … no_code_delta … predicate_evaluated`. `decision.log` shows the
real cause: `lane_resolution — dropped sonar-roundtrip … effective tier full exceeds the standard
posture cutoff`. The step was dropped deliberately by the posture cutoff, **before any predicate ran**.

### 4. A re-fired finalize step emits no `[DISPATCH]` line (SECOND)
`component=plan-marshall:phase-6-finalize` · bug · high

`pre-submission-self-review` ran three envelopes; ONE `[DISPATCH]` line (08:43:44). After
`outcome=error` at 08:50:18 the re-fire path re-enters the envelope without passing the emission point.
**The contract is satisfied once per step rather than once per envelope.**

### 5. ⭐ Zero `resolve-target` intent records make the dispatch audit VACUOUS
`component=plan-marshall:ref-workflow-architecture` · bug · high

`shape_violation` pairs Surface A (`[DISPATCH]` lines) against Surface B (`effort resolve-target`
decision entries) and fires on an unmatched **Surface B**. This plan emitted **18** Surface-A lines and
**ZERO** Surface-B entries across 80 decision entries. No left-hand side ⇒ the check cannot fire.

⛔ **Vacuity is PROVABLE within the same plan**: `pre-submission-self-review` demonstrably ran three
envelopes against one `[DISPATCH]` line — precisely what `shape_violation` exists to catch — and it was
not caught. ⭐ Interlocks with item 4: item 4 *creates* the unmatched pairs, item 5 *cannot see them*.
This is your **vacuous-guard archetype**, now at n≥5.

### 6. Aspect display names do not match the `collect-fragments` registry keys
`component=plan-marshall:plan-retrospective` · improvement · high

SKILL.md Step 3 names aspects in prose ("Invariant outcomes"); `collect-fragments --aspect` validates
against a closed registry (`invariant-summary`, …). The canonical keys **appear nowhere in SKILL.md**.
3 of 5 registrations rejected on first attempt. ⇒ Add a `registry key` column — the document that
instructs the registration must supply the exact argument.

### 7. Finalize dispatcher does not forward `--iteration` to `plan-retrospective`
`component=plan-marshall:phase-6-finalize` · bug · high

Mode detection is *"`--iteration` present ⇒ finalize-step mode"*, and **only** finalize-step mode emits
the `mark-step-done` tail. The actual dispatch prompt body carried no `iteration`. Following the
documented heuristic literally selects user-invocable mode, skipping `mark-step-done` and leaving
`phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` unwritten.

### 8. Finalize `[STEP]` logging covers 9 of 16 completed steps
`component=plan-marshall:phase-6-finalize` · improvement · medium

Seven steps completed with **no** `[STEP]` evidence; four more have `Completed` with no paired
`Executing`. Emission is per-handler rather than driven by the step loop, and the pairing is convention.

### 9. ⭐ Self-review error path re-pays the whole envelope — 431K tokens on ONE step
`component=plan-marshall:phase-6-finalize` · improvement · medium

Run 1 error 219,484 tok / 355s / 86 candidates; run 2 executed 212,423 tok / 511s / 106 candidates.
**431,907 tokens = 14.6% of the plan's entire 2,967,497-token spend**, roughly half of it re-work.
Wider shape: 6-finalize 1,299,699 vs 5-execute 466,370 — a **2.8:1 ceremony-to-work ratio** on a
`single_module bug_fix`, crossing that anchor's **error** threshold (1.3M) by 2.3×. No partial-result
reuse across the error boundary; the candidate set is deterministic and enumerable.

### 10. ⭐ A "credential not bound to X" fix must bind on EVERY discriminating dimension
`component=plan-marshall:phase-6-finalize` · anti-pattern

#1077's own round-1 self-review found the new authorization check **reintroduced the exact fail-open
shape the plan exists to remove**: correctly HEAD-bound and **kind-agnostic**, so a `pre-merge-consent`
granted seconds earlier at the same HEAD over a *different gap* satisfied the review barrier. ⭐ The
defect title names ONE dimension; the title becomes the scope; the unnamed dimension stays unbound.

### 11. ⭐ A fail-closed guard leaks through its own INDETERMINATE paths
`component=plan-marshall:phase-6-finalize` · anti-pattern

Two independent leaks in the same round: (a) the UNKNOWN branches — which carry an absolute *"the merge
NEVER proceeds on an UNKNOWN verdict"* — could still **mint a durable `grant`**, so an indeterminate
verdict could issue the credential authorizing a *later* merge; the refusal was enforced on the
**routing** and not on the **credential issuance**. (b) a `--kind` matcher that **admitted on no-match**
inside a guard built to fail closed.

### 12. A declared-but-never-emitted `display_detail` is a producerless contract row
`component=plan-marshall:ref-workflow-architecture` · bug

⭐ **SECOND SIGHTING of the `dispatch_boundaries` producerless-row shape.** Declaring and emitting are
two edits in two places; nothing fails when the second is skipped — the renderer degrades to
`<missing display_detail>` and forces a `[FAILED]` headline, so the step reports broken for a reason
unrelated to whether it worked. Your **defending-documentation / vacuous-authority** archetype.

### 13. ⭐ A 2-second incremental type-check green is a CACHE HIT, not a verification result
`component=plan-marshall:build-pyproject` · anti-pattern

From #1078. The local pre-push test-compile gate passed in **2–5 seconds** across consecutive rounds;
CI on the same tree checked **660 files** and found **2 real type errors**. Stale mypy incremental
cache — the gate answered *"nothing I have cached changed"* and that was consumed as *"the tree
type-checks"*. ⛔ **Implausible duration is a failure signal**, and this is your
`never-trust-a-routed-build's-outer-status` archetype arriving through a second mechanism (a cache
rather than a router). Confident + fast + repeated read as reassurance and are the symptom.

---

## One item we KEPT that you should know about, because it corroborates your `-010`

Your `truthful-signals-010` filed as HYPOTHESIS: *"for an edit-in-place bot, the edit is DROPPED from
findings while the movement it caused CREDITS participation."*

⭐ **The dedup half is now OBSERVED and source-confirmed** — `github_pr.py:783-785` `continue`s on the
`(bot_kind, comment_id)` dedup, `reviewed_commit_sha` is passed only into `add_finding` at line 824
below that `continue`, and `_findings_core.py:290` writes it at record creation with **no update path
anywhere in the codebase**. `automatic-review/SKILL.md:245` asserts the re-stamp happens. It never has,
for pr-agent. The **movement half remains unverified** — that arm is ours (PLAN-PR-013) and we are
keeping it. Nothing owed by you.

---

**Full message bodies**, append-only, at
`.plan/local/orchestrator/review-apparatus/inbox/archive/barrier-override-not-head-bound-0{02,03,04,05,07,08,09,10,11,12,13,14,15,16}.md`
and `correct-review-scores-as-maximally-wrong-004.md`.
