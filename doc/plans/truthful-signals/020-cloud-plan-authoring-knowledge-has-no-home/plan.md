> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Cloud-plan authoring knowledge has no home, so every author rediscovers it

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Two different actors touch a cloud plan at two different moments, and only one of them has a skill.
The **cloud session that executes** a plan loads `cloud-plan-lane` — 750 lines of execution contract
— as its first action. The **orchestrator that authors** one, locally, has nothing to load.

What authoring guidance exists is split and partial. `doc/plans/cloud-bridge.md` § Path 1 owns the
mechanics: naming, the `{NNN}-` prefix rules, the derive-from-spec order, what to carry across, and
the do-not-delete-the-spec rule. `doc/plans/_template/plan.md` owns the *shape* — the sections a plan
has. Neither owns the **judgement**: what makes a cloud plan survive contact with a runtime that has
no operator, cannot see the orchestrator's ledger, and cannot ask a question.

That judgement exists and was paid for. It currently lives in landing records and in whoever authored
the last plan. Concretely, from the two cloud plans run so far:

- A cloud VM clones from GitHub and `.plan/` is **git-ignored**, so the orchestrator ledger, plan
  specs, and landing records are **invisible to the run**. A plan that cites them as required reading
  sends the run somewhere it cannot go. Plan `010` handled this by hand, telling the run explicitly
  that its landing record was machine-local and not to go looking for it — knowledge written nowhere.
- The run has **no operator**. Plan `010` discovered mid-run that Step 9 forbids self-approving a
  contract change, and correctly recorded three proposals instead of shipping them. A plan whose
  deliverable needs a decision would simply stall.
- Plan `010`'s D0 was written as a **stop-condition** — derive the reviewer population from
  configuration, and halt rather than ship a hand-maintained list. It paid off: the population was
  derivable, and the fallback that would have reproduced the very defect class the plan was closing
  never got written.
- Plan `010`'s D2 was verified by a **cold read** — an independent sub-agent read the new merge-gate
  text blind and reported which reading it took (DISCLOSE, not BLOCK). For a deliverable whose whole
  value is what a later reader *does*, that is the only verification that tests the thing that matters.

None of that is in a skill. The next author either rediscovers it or ships a plan that stalls, sends
the run to an invisible path, or bakes in a fallback that defeats its own purpose.

## Goal

An orchestrator authoring a cloud plan has one skill to load that carries the authoring judgement,
and the mechanics stay where they already live. A reader can tell, for any rule, which file owns it.

## Deliverables

1. **D0 — GATE: establish the knowledge is genuinely unhoused, and bound the skill against
   duplication.** Enumerate what each of `doc/plans/cloud-bridge.md` § Path 1,
   `doc/plans/_template/plan.md`, `doc/plans/README.md`, and `.claude/skills/cloud-plan-lane/SKILL.md`
   already owns. Produce two explicit lists: **OWNED-ELSEWHERE** (each entry naming the owning file)
   and **REMAINDER** (what the new skill will own).
   *Done when:* both lists exist verbatim in the new skill's § Boundary section.
   ⛔ **STOP CONDITION — this deliverable may end the plan.** If the remainder is thin, report that
   and stop. Do not ship a skill that mostly points elsewhere; a pointer-shaped skill is worse than
   no skill, because it creates a second place to look and a second thing to drift.
2. **D1 — `.claude/skills/author-cloud-plan/SKILL.md`, user-invocable, carrying the judgement.**
   Each rule states its grounding, not just the rule. At minimum:
   - **Self-sufficiency.** `.plan/` is invisible to a cloud run; restate anything the run needs. A
     machine-local path may be named only to tell the run not to look for it.
   - **No operator.** No deliverable may require a mid-run decision; anything needing approval is
     recorded, never decided. A contract change is never self-approved.
   - **Stop-condition deliverables.** Where scope rests on a premise being derivable, make the
     derivation D0 and have it HALT rather than fall back to a hand-maintained artifact.
   - **Cold-read verification.** Where a deliverable's value is what its text makes a later reader
     do, verify by having a sub-agent read it cold and state which reading it took.
   - **Claim labels.** OBSERVED / HYPOTHESIS on every premise; a HYPOTHESIS carries its
     confirm/refute artifact; an asserted **absence** is verified like an asserted presence and is the
     higher-risk half.
   - **Counts are leads**, re-derived at the moment of the claim.
   - **Out-of-scope names why** — that boundary is what stops mid-run scope drift.
   *Done when:* the skill exists with frontmatter matching the sibling project-local skills
   (`name`, `description`, `user-invocable: true`, `mode`, `allowed-tools`) and every rule above
   carries its grounding.
3. **D2 — Wire it in at the two points where an author actually stands.** `cloud-bridge.md` § Path 1
   and `doc/plans/README.md` each gain a pointer.
   *Done when:* both reference the skill, **pointers only** — no rule copied in either direction, and
   no OWNED-ELSEWHERE entry from D0 restated inside the skill.
4. **D3 — Apply the skill's own criterion to its own footprint.** Re-read plan `010`
   (`git show 86c5b7532` — it is deleted from the working tree, so read it from history) and **this
   plan** against the finished rules, and report per rule which of the two it would have caught.
   *Done when:* the report carries that per-rule table. ⛔ **A rule that catches nothing in either
   plan is unnecessary or wrongly worded — say which, and drop it or fix it.** Do not pad the rule
   list to look complete.

## Out of scope

- **`cloud-plan-lane/SKILL.md`.** It is the execution contract, for a different actor at a different
  moment. Merging authoring into it would make every cloud run load guidance it can never use. Its
  three open contract proposals are a separate operator decision and are not touched here.
- **The plan template's structure.** The template is the shape; this skill is the judgement.
- **A mechanical validator for cloud plans.** Judgement first. Automation only once these rules have
  demonstrably caught something.

## Expected surface

- `.claude/skills/author-cloud-plan/SKILL.md` — new.
- `doc/plans/cloud-bridge.md` — § Path 1, pointer only.
- `doc/plans/README.md` — pointer only.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `.claude/skills/` holds 14 skills and none covers cloud-plan authoring | OBSERVED (asserted absence) | directory listing of `.claude/skills/`, enumerated 2026-08-08 — **re-derive it, do not trust this count** |
| `cloud-plan-lane/SKILL.md` is the execution contract and carries no authoring guidance | OBSERVED | that file, read 2026-08-08 (750 lines) |
| § Path 1 owns naming, prefix rules, derive-from-spec order, carry-across, do-not-delete-the-spec | OBSERVED | `doc/plans/cloud-bridge.md` § Path 1 |
| Plan `010` applied the self-sufficiency rule by hand | OBSERVED | `010`'s § Notes, in history at `86c5b7532` |
| `010`'s D0 stop-condition prevented a hand-maintained reviewer list | OBSERVED | `010`'s report `report-01.md` § D0, same commit |
| `010`'s D2 cold read returned DISCLOSE | OBSERVED | same report, § Findings → verification sub-agent |
| The remainder after D0's subtraction justifies a skill | HYPOTHESIS | D0 itself, which is authorised to stop the plan |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half: an
unverified absence produces work against something that already exists.

## Verification

- **The skill is exercised by D3 against real plans**, including this one — the plan applies its own
  criterion to its own output, which is the failure mode a criterion-driven sweep is most blind to.
- **D0's two lists are the anti-duplication proof.** After the skill is written, re-check that no
  OWNED-ELSEWHERE entry appears as a rule inside it. A restated rule is the defect, not a convenience.
- Docs-and-skill change only — no `*.py` expected, so the build gate will likely take its docs-only
  path. Confirm that from git evidence rather than assuming it.

## Notes

- **Prior art, and read it first:** plan `010` (PR #1112, merged `86c5b7532`) shipped the lane's
  review-coverage disclosure and produced most of the evidence above. Its plan and report are deleted
  from the working tree (collected) but live in that commit.
- **Authoring order matters and is the reason this plan exists in the shape it does.** Its
  orchestrator spec was written *before* this file, per § Path 1. Plan `010` was authored the other
  way round and its spec had to be back-filled; for the interval between, the work was invisible to
  the ledger — no queue row, no slot, unseen by any disjointness check.
- ⛔ **Do not go looking for the orchestrator spec or the landing records.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file — which is the
  self-sufficiency rule the plan is about, applied to itself.
