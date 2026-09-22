# PLAN-TRUTH-170: The finalize seam records less than it does, and enforces less than it documents

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-18 from the corpus-wide lessons sweep. Four lessons, four plans, none previously owned;
all preserved verbatim at `.plan/local/orchestrator/truthful-signals/lessons/{id}.md`.

## Objective

**Four independent gaps in the finalize seam, each one a rule that exists in prose and not in the
machinery.** They share a shape: the run does something the record does not capture, or the document
states a constraint nothing enforces.

- A re-fired step's `--outcome done` **without `--force`** silently discards the prior firing, so the
  step record under-counts exactly the steps that re-fire most.
- `[OUTCOME]` / `[DISPATCH]` lines are lost on re-dispatch, so the dispatch audit's arithmetic reads
  healthy against a denominator it never saw.
- `mark-step-done` **documents** an 80-char ASCII `display_detail` ceiling and enforces none of it.
- The commit seam's stage-specific-files rule is **prose**, backed by a whole-tree porcelain read, with
  no mechanical staging boundary — a CWE-200 shape: a commit can carry what nobody chose to stage.

⭐ None of these is a wrong number. Each is a record that is quietly incomplete, which is the harder half
of this epic's theme: an absence that reads like a clean reading.

## Deliverables

Seven deliverables (D0–D5 plus the two absorbed at D4a/D4b), re-derived after the 2026-09-18 cleanup
merge rather than summed: `-156`'s D0 collapses into this spec's D0, which already derives the
step-record population. D0 is a gate.

**D0 — GATE: derive the re-fire population and the enforcement gap population.** Enumerate (a) every
finalize step that can re-fire and whether its terminal call carries `--force`, and (b) every constraint
the finalize docs state that no code enforces. ⛔ Publish both with sizes; the four members below were
found one at a time.

**D1 — A re-fired step's record is additive, not last-write-wins.** Sweep every re-fireable step's
terminal `--outcome done` branch for the missing `--force`, and make the step record able to represent
*fired N times* rather than *fired*.

**D2 — Every completed task emits its `[OUTCOME]` line, including on re-dispatch.** A channel that
under-records lowers its own confidence silently; publish the emission population alongside the count so a
gap is visible rather than inferred.

**D3 — The `display_detail` ceiling is enforced where it is documented.** 80 chars, single line, ASCII,
no trailing period — rejected at the call, not described in a standard.

**D4a — ABSORBED from PLAN-TRUTH-156: `mark-step-done` derives `head_at_completion` itself and stops
accepting it as an input.** A value the caller supplies is a value the caller can get wrong — and a step
record whose HEAD was supplied rather than observed cannot be used to establish what the tree looked like
when the step finished, which is exactly what `PLAN-TRUTH-169` D6 wants to read it for. D0's population
derivation absorbs `-156`'s: every `mark-step-done` call site currently supplying the value.

**D4b — ABSORBED from PLAN-TRUTH-155 D10: `assert-step-recorded --require-terminal` passes on a STALE
record from a prior firing.** The same defect family as D1 — a step record that cannot represent *fired
again* lets a re-fire be satisfied by its own predecessor. It moves here because its subject is the step
record, not the documentation surfaces `-155` otherwise sweeps.

**D5 — The commit seam gets a mechanical staging boundary, plus controls.** Replace the prose rule with an
allowlist the commit step applies, so what is staged is derived from the plan's footprint rather than from
whatever the working tree happens to hold. Controls: a re-fire is visible in the record, an over-long
`display_detail` is refused, and a commit attempting an unlisted path fails loudly.

## Claim Labels

Each is OBSERVED by the plan that filed the cited lesson; all four are preserved in this epic. ⛔ Re-ground
each at HEAD before scoping (verify-at-outline for all).

- OBSERVED (lesson `2026-09-03-05-001`): re-fireable finalize steps carry a terminal `--outcome done`
  branch with no `--force`.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-03-05-001 present; settling re-fireable finalize steps carry a terminal --outcome done with no --force requires the population sweep D0 owns, not run here.
- OBSERVED (lesson `2026-09-04-08-007`, KEEP of its cluster): `[OUTCOME]` is lost on self-re-dispatch;
  member `2026-09-05-07-004` (a re-fire emitting no `[DISPATCH]`, leaving the audit blind) retired as
  redundant of it. ⚠ Three recurrences across three plans.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-04-08-007 present; [OUTCOME]/[DISPATCH] loss on re-dispatch is a runtime-emission property, not observable from source read-only.
- OBSERVED (lesson `2026-09-05-06-001`): `mark-step-done` does not enforce the `display_detail` ceiling it
  documents.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_mark_step.py handles display_detail at 18 sites (307, 452-511) with NO length, ASCII, single-line or trailing-period check - a pattern probe returns ZERO hits. The documented ceiling is unenforced.
- OBSERVED (lesson `2026-09-08-22-001`): the finalize commit seam's stage-specific-files rule is prose, not
  a mechanical allowlist; the porcelain read is whole-tree.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: git-workflow.py:2295 runs git status --porcelain with no pathspec (whole-tree) and the file carries no staging allowlist derived from a footprint. CAVEAT: established by absence of an allowlist at the commit seam, not by sweeping every commit-seam doc.
- ⚠ HYPOTHESIS: the four are independent rather than one under-recording cause — ⛔ D0 decides; if they
  share a cause, D1–D4 collapse and the plan shrinks (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Independence-vs-common-cause question the spec itself hands to D0.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` — the step docs whose terminal branches D1 sweeps (D0, D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the dispatcher's step-record and emission contract (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — `mark-step-done` and its validation (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` — the commit/staging seam (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — the `[OUTCOME]` emitter (D2)
- OBSERVED: `test/plan-marshall/manage-status/` and `test/plan-marshall/workflow-integration-git/` — D5's controls
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `mark-step-done`'s parameter surface (D4a; absorbed from PLAN-TRUTH-156)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — `assert-step-recorded` (D4b; absorbed from PLAN-TRUTH-155 D10) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md` — `pr_number` stamped at create-pr and never reconciled against the PR that actually merged (D0, D1; folded 2026-09-22)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Shares `phase-6-finalize/**` with `PLAN-TRUTH-145`, `-147`, `-158` and `post-run-quality` PLAN-PRQ-04
  and PRQ-06 — the last two are **cross-epic and invisible to both gates**. Check that epic's queue before
  launching.
- ⚠ D3 touches `manage-status/scripts/`, which `PLAN-TRUTH-156` (mark-step-done derives HEAD) also owns.
  Sequence; if `-156` lands first, D3 builds on its validation path rather than adding a second one.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-170-the-finalize-seam-records-less-than-it-does-and-enforces-less-than-it-documents.md"
```

## ⭐ FOLDED 2026-09-22 — a stamped `pr_number` surviving only in a `display_detail` prose sentence, D0/D1's exact shape

Inbox lesson `2026-09-21-08-004` (relayed via `lessons-handling-26-09-22-01`): `create-pr` stamped
`pr_number: "1555"`; the operator closed it unmerged and landed as `#1557`+`#1558` instead, recorded only
in a `display_detail` prose sentence. This spec's own Objective states the shape verbatim: "None of these
is a wrong number. Each is a record that is quietly incomplete." Surface added above (`create-pr.md`).

⚠ **Split, do not let one fold swallow both halves.** The RECORDING half (above) is D0/D1's. The
CONSUMING half — *"four of sixteen retrospective aspects could not grade the plan because every footprint
tier resolved against the dead PR"* — is **PLAN-TRUTH-174** D2's exact shape (a three-state `comparison`
that reports its unresolvable state instead of silently not grading). Sequence 170 → 174, or split the
lesson's two halves explicitly if both launch independently.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
