> ⛔ **TRANSFERRED OUT 2026-09-17 — this spec is RETIRED and must not be launched from here.**
> Its substance now lives at
> `.plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-01-retrospective-quality-chain-and-assessments-graded-at-report-time.md`
> (epic `post-run-quality`, WS-01), which carries all 11 deliverables and points back at this file and at
> PLAN-TRUTH-123 / PLAN-TRUTH-130 as the audit record. This file stays on disk unchanged below the line —
> a superseded spec is never deleted. Its queue row is `parked` because `queue --transition` cannot write
> the `transferred` status the ledger already contains (see PLAN-TRUTH-143 D9).
> ⚠ **D10's dependency runs the other way**: PLAN-TRUTH-146 (the unified ledger vocabulary) STAYS in this
> epic, and PLAN-PRQ-01 consumes it.

# PLAN-TRUTH-152: The retrospective quality chain has no score, and assessments are graded at report time

## Objective

The quality chain produces no score, so a disabled gate is indistinguishable from a clean one — the two
outcomes an audit most needs to tell apart. The same reporting surface then grades a recorded action against a
mutable stored judgement read at REPORT time rather than at action time, so a correct action is graded a
violation the moment the judgement behind it changes. Merged because both live in `plan-retrospective` and the
archived-retrospective auditor, and because a score computed over mis-graded assessments is worse than none.

## Deliverables

11 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive the mechanism population, settle the disposition→point mapping against the real corpus, and enumerate every surface that grades a recorded action against a mutable stored judgement.** ⛔ Settle the mapping against the REAL corpus, not against an assumed distribution. (PLAN-TRUTH-123 D0 + PLAN-TRUTH-130 D0.)
2. **D1 — The coordinator: ONE script, one entry point, two consumers.** (PLAN-TRUTH-123 D1.)
3. **D2 — The scoring core: signal presence first, yield second, and the two are NEVER folded into one number.** Folding them is what makes a disabled gate read as a clean one. (PLAN-TRUTH-123 D2.)
4. **D3 — Consumer 1: the corpus quality report, and the first run's README complement.** (PLAN-TRUTH-123 D3.)
5. **D4 — Consumer 2: augment the per-plan `plan-retrospective` output.** (PLAN-TRUTH-123 D4.)
6. **D5 — An assessment carries an effective-from instant, and the report joins on it.** (PLAN-TRUTH-130 D1.)
7. **D6 — Supersession is recorded, not overwritten.** (PLAN-TRUTH-130 D2.)
8. **D7 — An operator override is distinguishable from drift, at the report.** (PLAN-TRUTH-130 D3.)
9. **D8 — Close the outline write-back gap.** (PLAN-TRUTH-130 D4, member 2.)
10. **D9 — The tests, and they are the deliverable that outlives the rest.** Plus matched controls for every assessment-grading member. (PLAN-TRUTH-123 D5 + PLAN-TRUTH-130 D5.)
11. **D10 — CONSUME the unified vocabulary — do not build it.** ⛔ PLAN-TRUTH-123's D6 recorded that its D8-class work MOVED to the vocabulary plan. That plan is now PLAN-TRUTH-146: this plan CONSUMES the vocabulary and must land after it. Building a second vocabulary here is the duplication this merge exists to prevent. (PLAN-TRUTH-123 D6.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-123 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md` § `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: no | evidence: Pointer at PLAN-TRUTH-123 Claim Labels: 23 verdicts including THREE contradicted (indices 9,12,14). Not yet re-scoped. Note: PLAN-TRUTH-152 is itself transferred out to post-run-quality PLAN-PRQ-01, so this spec's own scope is already moving.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-130 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-130-an-assessment-is-read-at-report-time-and-grades-a-correct-action-as-a-violation.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-130 Claim Labels: 8 top-level bullets, only 7 verdicts (one unsettled), 5 unverifiable.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — carried from PLAN-TRUTH-123
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — carried from PLAN-TRUTH-123
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — carried from PLAN-TRUTH-123
- `.claude/skills/audit-archived-plan-retrospectives/checks/` — carried from PLAN-TRUTH-123
- `doc/analyzis-cloud-plan/` — carried from PLAN-TRUTH-123
- `test/plan-marshall/plan-retrospective/` — carried from PLAN-TRUTH-123
- `test/plan-marshall/audit-archived-plan-retrospectives/` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — carried from PLAN-TRUTH-123
- `marketplace/bundles/plan-marshall/skills/manage-findings/**` — carried from PLAN-TRUTH-130
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/**` — carried from PLAN-TRUTH-130
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/**` — carried from PLAN-TRUTH-130
- `marketplace/bundles/plan-marshall/skills/manage-references/**` — carried from PLAN-TRUTH-130
- `test/plan-marshall/manage-findings/**` — carried from PLAN-TRUTH-130
- `test/plan-marshall/plan-retrospective/**` — carried from PLAN-TRUTH-130

## Dependencies and Sequencing

⛔ Sequenced AFTER PLAN-TRUTH-146, which builds the vocabulary D10 consumes. D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md` (PLAN-TRUTH-123)
- `PLAN-TRUTH-130-an-assessment-is-read-at-report-time-and-grades-a-correct-action-as-a-violation.md` (PLAN-TRUTH-130)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-152-the-retrospective-quality-chain-and-assessments-graded-at-report-time.md"
```

## ⭐ FOLDED 2026-09-13 — TWO RETROSPECTIVE-ASPECT FINDINGS FROM `plan-pr-046`'S LANDING (PR #1477)

Forwarded via `review-apparatus` (`inbox/review-apparatus-038.md`), originating from `plan-pr-046`'s own
finalize. Expected Surface presumed unchanged — already covered by the `plan-retrospective/scripts/` and
`plan-retrospective/scripts/**` entries above; NOT independently re-derived against the specific aspect
files in this checkout (leads, not instructions, per the forwarding message).

1. **`check-manifest-consistency` grades `branch_cleanup_changes` FAIL over a post-merge empty diff that
   is the NORMAL state at finalize order 995** (the plan is already merged by then), while reporting
   `diff_available: true` — so the verdict reads as a checked negative rather than an unobservable one.
   The sibling `check-outline-vs-shipped` resolved 31 realized paths through the SAME shared resolver in
   the same run, so the evidence was reachable. Remedy: `indeterminate` with the reason, or reuse the
   sibling's resolver.
2. **`permission-prompt-analysis` returns an empty list from the reduced transcript, which cannot carry
   permission prompts by construction** (5 of 1810 messages kept). That run correctly recorded
   `coverage: not_evaluated` rather than a clean-looking empty list — a design item, not an incident. Open
   question for D0: read an unreduced channel, or retire the aspect; publishing `not_evaluated` forever
   is honest but means the aspect never answers.

## ⭐ FOLDED 2026-09-15 — A THIRD SIGHTING OF THE POST-MERGE FALSE-FAIL, PLUS TWO NEW RETROSPECTIVE PIPELINE BUGS

Forwarded from `plan-truth-148-002.md`, `review-apparatus-041.md` § C-002, `plan-truth-157-001.md`, and
`plan-truth-157-003.md`. Expected Surface unchanged — `plan-retrospective/scripts/` (directory +
recursive glob) already covers all four.

**Third independent sighting of the post-merge empty-diff false FAIL** (`check-manifest-consistency`),
now confirmed on `plan-truth-148` with exact figures: first run (`--base-ref origin/main` post-merge)
`files_total: 0`, `branch_cleanup_changes: fail`; second run (`--diff-file` with the 27 paths the shared
resolver recovers) `files_total: 27`, same rule `pass`. `git show --name-only` on the landed commit
confirms the 27 paths. `review-apparatus-041` § C-002 independently names this the SAME defect
transferred from `PLAN-PR-046` (`review-apparatus-038` item 1) — three sightings, one remedy, unchanged:
resolve the footprint through the shared resolver when no `--diff-file` is supplied (as the two sibling
scripts `check-routing-decisions`/`check-outline-vs-shipped` already do), and never emit `fail` from an
empty oracle — `indeterminate` when `oracle_available: true` and the diff is empty.

**Two new pipeline bugs, from `plan-truth-157`'s own retrospective measuring itself:**
- `extract-chat-signal` emits its `reduced_transcript` field as a multi-line string that is TOON-hostile
  — the format cannot round-trip it cleanly. Fix: emit it as one quoted scalar.
- `analyze-logs` publishes only a `top_tags` SAMPLE for the aspect it is asked to grade, with no total
  count — so `logging-gap` analysis reading that aspect cannot tell a genuinely small population from an
  unmeasured one. Publish the VERIFY tag count alongside the sample.

## ⭐ FOLDED 2026-09-17 — THREE RETROSPECTIVE PRODUCERS THAT PUBLISH A CONFIDENT FIGURE OVER AN UNREAD POPULATION

Forwarded from `truth-166-architecture-refresh-migration-churn-002.md`, `-004.md` and `-005.md` (PR #1501,
all first-party from that run's own retrospective). Expected Surface unchanged — `plan-retrospective/**`
and `plan-retrospective/scripts/**` already cover all three.

1. **`check-manifest-consistency` diffs a `base_ref` that is structurally empty by the time it runs.**
   `plan-retrospective` is finalize step 17; `branch-cleanup` — which merges the PR — is step 13, so the
   plan's changes are already in `origin/main` when the aspect runs. It reported `files_total: 0` with
   `diff_available: true` and FAILED its `branch_cleanup_changes` rule ("the observed diff is empty … so no
   implementation file changed") for a plan that shipped a 26-path footprint. ⛔ Two sibling aspects in the
   SAME run got it right (`footprint_source: resolved`, 26 paths), so the run contains a 0-vs-26
   disagreement in which the wrong aspect is the one self-reporting `available`. The skill's canonical
   block makes the wrong path the default by instructing `--base-ref` whenever `--diff-file` is absent.
   Remedy: route through the shared footprint resolver as the siblings do; an empty-but-available diff must
   never assert that nothing changed.
2. **`extract-chat-signal` violates the no-flush-left-multiline MUST its own sibling contract states.**
   `references/chat-history-analysis.md` forbids flush-left continuation lines containing a colon, because
   `parse_toon` re-reads them as phantom top-level keys; the pre-pass emits `reduced_transcript` in exactly
   that shape (`operator-decision:`, `user:`, `<command-name>…:`). Every Tier-1 discriminator read healthy
   while the payload behind the gate was absent. Adjacent: `reduced_bytes: 298684` sits beside a delivered
   payload of ~2.6KB — the two fields measure different quantities. Remedy: emit a quoted scalar with
   escaped newlines or hand back a path; make `reduced_bytes` describe the delivered payload; bind the MUST
   to fragment PRODUCERS, not only fragment authors.
3. **`analyze-logs`'s `build_time` emits a bare `0` where its own consumer rule says `unavailable`.**
   `references/plan-efficiency.md` already carries "Absent is not zero" in full — but as a CONSUMER duty,
   while the producer published `total_build_seconds: 0.0`, `build_count: 0` for a plan whose same fragment
   reports 28 build calls totalling 3,975,160ms (folded global logs: 123 calls, 51.7% of all script time).
   Its sibling blocks in the same fragment DO publish a population (`cost_rollup`) or a could-not-look
   reason (`artifact_emission`), so the omission is local, not a house style. Remedy: publish the
   population read and emit `unavailable`, or omit the key entirely as `scope_creep_check` omits
   `residual_count`; keep the consumer rule, which stops being load-bearing once the producer is honest.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
