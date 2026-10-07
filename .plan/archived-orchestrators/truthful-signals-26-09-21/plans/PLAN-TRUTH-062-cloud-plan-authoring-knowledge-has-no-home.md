# PLAN-TRUTH-062: Cloud-Plan Authoring Knowledge Has No Home

epic: truthful-signals
workstream: WS-01

> Staged plan spec — the SOURCE RECORD, authored BEFORE its cloud plan, per
> `doc/plans/cloud-bridge.md` § Path 1. The derived cloud plan is
> `doc/plans/truthful-signals/020-cloud-plan-authoring-knowledge-has-no-home.md`; the shared slug is
> the entire mapping. ⭐ This ordering is deliberate remediation: `PLAN-TRUTH-061` was authored in the
> reverse order and its spec had to be back-filled (see that spec's § Provenance).

## Objective

Ship `.claude/skills/author-cloud-plan/` — a user-invocable project-local skill that carries the
judgement needed to AUTHOR a cloud plan well, consumed by the orchestrator at authoring time rather
than by the cloud session at execution time. It owns authoring judgement only; the naming, prefix,
and create/sync/collect lifecycle stay owned by `cloud-bridge.md` § Path 1 and are referenced, never
restated.

## Deliverables

1. **D0 — Establish that the knowledge is genuinely unhoused, and bound the new skill against
   duplication.** Enumerate what `cloud-bridge.md` § Path 1, `doc/plans/_template/plan.md`,
   `doc/plans/README.md`, and `cloud-plan-lane/SKILL.md` each already own. Produce an explicit
   OWNED-ELSEWHERE list the new skill must not restate, and a REMAINDER list it will own.
   *Done when:* both lists exist in the skill's own § Boundary section, each OWNED-ELSEWHERE entry
   naming the file that owns it. ⛔ **If the remainder is thin — if authoring judgement turns out to
   be adequately covered by Path 1 plus the template — STOP and report that instead of shipping a
   skill to justify the plan.** A skill that mostly points elsewhere is worse than no skill.
2. **D1 — The skill, carrying the authoring judgement.** At minimum, each item stated as a rule with
   the evidence that produced it:
   - **A cloud plan must be SELF-SUFFICIENT.** A cloud VM clones from GitHub and `.plan/` is
     git-ignored, so the orchestrator ledger, landing records, and plan specs are **invisible** to
     the run. Anything the run needs is restated in the plan; a machine-local path may be named only
     to tell the run *not* to go looking for it.
   - **The run has NO operator.** No deliverable may require a mid-run decision. Anything needing
     approval is recorded for the operator, never decided — and a contract change is never
     self-approved.
   - **Give a premise-dependent plan a stop-condition deliverable.** Where scope rests on something
     being derivable, make the derivation D0 and have it HALT rather than fall back to a
     hand-maintained artifact.
   - **Wording-sensitive deliverables get a cold-read check.** Where a deliverable's value is what
     the text makes a later reader *do*, name a verification in which the sub-agent reads it cold and
     states which reading it took.
   - **Every claim carries OBSERVED / HYPOTHESIS**, a HYPOTHESIS carries its confirm/refute artifact,
     and an asserted **absence** is verified like an asserted presence — the higher-risk half.
   - **Every count in the plan is a lead**, re-derived at the moment of the claim.
   - **The out-of-scope section names why**, since that boundary is what stops mid-run drift.
   *Done when:* the skill exists, is user-invocable, and each rule carries its grounding.
3. **D2 — Wire it in at the two points where an author actually stands.** `cloud-bridge.md` § Path 1
   and `doc/plans/README.md` each gain a pointer to the new skill. ⛔ **Pointers only** — no rule from
   the new skill is copied into either file, and no rule from Path 1 is copied into the skill.
   *Done when:* both files reference it and D0's OWNED-ELSEWHERE list has no entry restated in the
   skill.
4. **D3 — Prove the skill against the two plans that produced its evidence.** Re-read
   `PLAN-TRUTH-061`'s cloud plan and this plan's own cloud plan against the new skill's rules and
   report which rules each would have caught. ⛔ **A rule that catches nothing in either is either
   unnecessary or wrongly worded — say which, and drop or fix it.** This is the plan applying its own
   criterion to its own footprint (round 8 item 18).

## Out of scope

- **Changing `cloud-plan-lane/SKILL.md`.** It is the execution contract for a different actor at a
  different moment; the two must not merge. Its three open proposals are a separate operator decision.
- **Changing the plan template's structure.** The template is the shape; this skill is the judgement.
- **A script or validator that checks a cloud plan mechanically.** Judgement first; automation only
  once the rules have caught something real.

## Expected surface

- OBSERVED: `.claude/skills/author-cloud-plan/SKILL.md` — new (asserted absence, verified: the
  directory listing of `.claude/skills/` has 14 entries and none is an authoring skill).
- OBSERVED: `doc/plans/cloud-bridge.md` § Path 1 — pointer only.
- OBSERVED: `doc/plans/README.md` — pointer only.

## Claim Labels

- OBSERVED: `.claude/skills/` holds 14 skills, none covering cloud-plan authoring — enumerated
  2026-08-08.
- OBSERVED: `cloud-plan-lane/SKILL.md` is 750 lines of EXECUTION contract, loaded by the cloud
  session as its first action; it carries no authoring guidance.
- OBSERVED: `cloud-bridge.md` § Path 1 owns naming, the `{NNN}-` prefix rules, derive-from-spec
  order, the carry-across list, and the do-not-delete-the-spec rule — read 2026-08-08.
- OBSERVED: the self-sufficiency rule is real and was applied by hand when authoring `010` (its
  Notes tell the run that the landing record is machine-local and not to look for it).
- OBSERVED: the stop-condition pattern is real and paid off — `010`'s D0 halt-if-not-derivable
  produced a config-derived reviewer population instead of a hand-kept list.
- OBSERVED: the cold-read check is real and passed — `010`'s D2 sub-agent read the text cold and
  answered DISCLOSE.
- HYPOTHESIS: the remainder after D0's subtraction is substantial enough to justify a skill —
  confirm/refute at D0 itself, which is authorised to STOP the plan.

**Disjointness:** `.claude/skills/author-cloud-plan/**` (new), plus pointer-only edits to two
`doc/plans/` files. Disjoint from every running plan — `044` (`manage-lessons`/`manage-status`),
`060` (`manage-build-server`), `042` (`pm-dev-java`), `011` (`manage-logging`/`manage-providers`) —
and from emitted `056`/`057`/`058`.

## Dependencies and Sequencing

- Depends on: none. `PLAN-TRUTH-061` has landed (#1112), so the lane contract is stable.
- Overlaps with: none in flight. ⚠ Touches `cloud-bridge.md`, which `061` also edited — but `061`
  is shipped, so this is sequential, not concurrent.
- Adjacent to: `cloud-plan-lane/SKILL.md`, deliberately untouched (see Out of scope).

## Hand-Off Command

Executes in the CLOUD lane, not the plan-marshall lifecycle:

```text
Execute doc/plans/truthful-signals/020-cloud-plan-authoring-knowledge-has-no-home.md
```

## Write-Boundary

The cloud run writes only its own `doc/plans/truthful-signals/020-…/` directory and the repository
source its deliverables name. It creates and edits NO file under `.plan/local/orchestrator/` — that
tree is git-ignored and invisible to the lane; the landing is collected locally per
`cloud-bridge.md` § Path 3.
