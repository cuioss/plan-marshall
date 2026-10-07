# PLAN-28: lessons-housekeeping-plugin-doctor-contract

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Operator-surfaced 2026-07-21 after fixing PR #924 (the symptom); **the root-cause
> contract contradiction is orchestrator-VERIFIED against source** (see Verified Evidence). Third
> confirmed occurrence of the same defect. Re-ground line citations at outline (current as of the
> 2026-07-21 tree).

## Objective

Two shipped contracts give the lessons-housekeeping finalize step **mutually contradictory** orders,
and the collision leaves promotion edits stuck with no push path. Reconcile the two contracts, and give
the step a committable path for the source edits it makes — so a promote-then-retire disposition can no
longer wedge a PR.

## Verified Evidence (orchestrator, 2026-07-21)

- **The step's contract MANDATES a lesson-id citation in skill prose.**
  `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`: line 25 ("cross-referencing the
  originating lesson id"), line 149 ("cross-referencing the originating lesson id so the promoted rule's
  provenance stays traceable"), and line 155 ("include a short `(extends lesson {id})` /
  `(promoted from lesson {id})` cross-reference") — writing that citation into the governing skill's
  `standards/*.md` / `references/*.md`.
- **The lint FORBIDS exactly that.** `pm-plugin-development:plugin-doctor` rule
  `no-lesson-id-in-skill-prose` (`scripts/_analyze_lesson_id_in_skill_prose.py`; rule-catalog +
  rule-provenance entries) rejects lesson IDs in skill prose — the same `standards/`/`references/` scope
  the contract targets. So the step, followed literally, produces a guaranteed `quality-gate` failure.
- **The failure wedges the PR with no push path.** The promotion `Edit`s land in source docs during
  finalize; the lint failure fails verify, and the edits sit uncommitted — PR #924 was stuck since
  07-17 (and had fallen behind main) until hand-repair.
- **Provenance is ALREADY captured elsewhere.** `SKILL.md:164` — the retirement tombstone records the
  `{target}` the residue was promoted into ("the tombstone records where the knowledge went"), plus a
  decision-log entry (Step 5). So reverse-traceability does not depend on the in-prose citation.
- **Recurrence n=3:** #924 (verified merged, `3e7ecd42f`), #958 (verified merged, `0577437b1`), and
  this session's own housekeeping. Captured as lesson `2026-07-21-10-001`.

## Deliverables

### D1 — reconcile the two contracts (one wins; state which and why)

Make the housekeeping contract and the `no-lesson-id-in-skill-prose` lint agree. **Confirm the direction
at outline** — the leading candidate, given the tombstone already records provenance, is to **drop the
in-prose `(promoted from lesson {id})` mandate** from the housekeeping contract (SKILL.md:25/149/155) and
rely on the tombstone + decision-log for traceability; a structured (non-prose) provenance channel is an
option if outline finds prose-free provenance insufficient. The alternative — relaxing the lint to permit
a designated provenance form — must justify why skill prose should carry transient lesson IDs against the
rule's original rationale (check `rule-provenance.md`). **Acceptance:** the step's documented procedure,
executed literally, produces NO `no-lesson-id-in-skill-prose` finding; provenance of a promoted rule
remains recoverable (tombstone names the target; the lesson id is recoverable from the tombstone/decision
log). Whichever side moves, the other's rationale is preserved or explicitly superseded in writing.

### D2 — give the step a committable path for its source edits

The promote-then-retire disposition edits governing-skill source docs mid-finalize; those edits need a
commit+push path rather than being left dangling on a verify failure. **Confirm the seam at outline** —
candidates: fold the promotion edits into the plan's own finalize commit/PR, or emit a follow-up PR for
them. Respect the finalize flow's existing commit/push mechanics (do NOT invent a parallel one).
**Acceptance:** a promote-then-retire run leaves NO uncommitted source edit behind — the promoted rule is
either committed within the plan's PR or carried by an explicitly-emitted follow-up PR; a failure mid-way
leaves a clean tree (the atomic-by-convention posture in SKILL.md:203 is preserved), never a wedged PR.

### D3 — structural guard so the two contracts cannot silently re-diverge

Add the check that keeps the housekeeping contract and the lint in agreement (e.g. a plugin-doctor rule
or a cross-reference test asserting the step's documented promotion form does not embed a lesson id in
prose). Mirror the guard pattern PLAN-13 #950 / PLAN-16 #945 used for their contract violations.
**Acceptance:** a future edit that re-introduces a lesson-id-in-prose mandate to the housekeeping step (or
a lint change that re-forbids the reconciled form) is caught structurally, not by a fourth stuck PR.
Retire lesson `2026-07-21-10-001` on landing.

## Out of scope / do NOT expand
- The `manage-lessons remove` tombstone mechanics beyond what D1's provenance decision needs.
- Other plugin-doctor rules or the broader lessons-housekeeping workflow (dedup/adaptation/retain
  dispositions) — this plan is the promote-then-retire ↔ lint collision only.
- Re-litigating whether promotion should happen at all — it should; this fixes HOW it records provenance
  and commits its edits.

## Absorbs
- Operator-surfaced defect "lessons-housekeeping ↔ plugin-doctor contradiction, edits left uncommitted"
  (2026-07-21, n=3: #924/#958/this session) → D1/D2.
- Lesson `2026-07-21-10-001` (the captured recurrence) → retired at D3.

## Expected Surface
- `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` (contract — lines 25, 149, 155, 164, 203) (D1/D2)
- `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_lesson_id_in_skill_prose.py` +
  `references/rule-catalog.md` + `references/rule-provenance.md` (the lint — only if D1 moves the lint side) (D1)
- the finalize commit/push seam (phase-6-finalize or the step wrapper) for the D2 push path
- a structural guard (plugin-doctor rule or cross-reference test) (D3)
- lesson `2026-07-21-10-001` (retire at D3)
- tests: literal-step-procedure-produces-no-lint-finding; promote-then-retire-leaves-clean-tree;
  guard-catches-reintroduced-prose-citation

## Dependencies and Sequencing
- Depends on: none.
- **Surface-disjoint from the launched trio (PLAN-20/21/22)** and from PLAN-23/24/25/26/27 — it touches
  the housekeeping step + the lesson-id lint + the finalize push seam, none of which overlap
  `maven.py`, `github_pr.py`, `manage-locks`, or the phase-5 leaf surface. **Startable in parallel with
  anything currently in flight.**
- Meta-project-only (the housekeeping step is a project-local `.claude/skills/` skill).

## Size / split guard
3 deliverables — under the ~6 presumption. D1 is a bounded contract-reconciliation decision; D2 reuses the
existing finalize commit/push seam; D3 is a single guard. No split anticipated. If D2's push-path proves
to need finalize-flow changes larger than a seam reuse, ship D1+D3 (the contradiction is resolved and
guarded) and stage D2 as a follow-up, recorded as an epic decision.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-28-lessons-housekeeping-plugin-doctor-contract.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-28.md is recorded}
