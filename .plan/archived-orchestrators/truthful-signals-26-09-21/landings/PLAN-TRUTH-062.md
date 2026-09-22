# Landing Analysis: PLAN-TRUTH-062 — Cloud-Plan Authoring Knowledge Has No Home

epic: truthful-signals
workstream: WS-01
pr: [#1117](https://github.com/cuioss/plan-marshall/pull/1117) — merged `dbe1b74f4`

> Executed in the standalone cloud lane. Every claim below re-verified first-party against
> `origin/main`, the merged diff, and the landed artifacts — the run report is a lead, not a fact.

## The question this plan was asked, and its answer

The operator asked whether cloud-plan authoring learnings belong in a separate skill. I agreed **with
a boundary condition** and staged the answer as a gate rather than as my opinion: D0 subtracts what
`cloud-bridge.md` § Path 1, `_template/plan.md`, `README.md`, and `cloud-plan-lane` already own, and
**halts the plan if the remainder is thin.**

**The gate did not fire, and the subtraction was rigorous.** OWNED-ELSEWHERE lists **twelve** entries,
each attributed to its owning file. The remainder is seven rules, of which **four are owned by no
other file**: self-sufficiency, the no-operator constraint, stop-condition deliverables, and
cold-read verification. The skill closes with the honest inverse: *"if a future subtraction ever thins
the remainder to pointers, the honest move is to delete this skill, not to pad it."*

⇒ **Answer: yes, evidenced — not by my agreement.**

## Deliverable Fidelity vs Spec

Corroborated against `git show --stat dbe1b74f4` — 5 files, +496.

| Deliverable | Verdict | Evidence |
|---|---|---|
| D0 — gate + anti-duplication bound | shipped-as-specified | § Boundary carries both lists verbatim; 12 OWNED-ELSEWHERE entries, each naming its owner. Stop condition evaluated and correctly not fired. |
| D1 — the skill | shipped-modified | `.claude/skills/author-cloud-plan/SKILL.md` (+224), user-invocable, frontmatter matching siblings. **Modified against my spec — see below.** |
| D2 — pointers at both authoring sites | shipped-as-specified | `cloud-bridge.md` +7, `README.md` +7. Pointers only; no rule copied either direction. |
| D3 — apply the criterion to its own footprint | shipped-as-specified | Per-rule table over `010` and `020`. All seven rules catch a real situation in both, so none dropped or reworded. |

## ⛔ Two authoring defects in MY spec, both found by the executing plan

Recorded deliberately, on the round-8 item-37 precedent that a landing which only confirms the
author's expectations is not doing its job.

1. **My D1 enumeration was over-scoped.** I listed claim labels, counts-are-leads, and
   out-of-scope-names-why as rules the skill should carry. D0's subtraction found all three
   **already owned** — by `_template/plan.md` and `cloud-plan-lane`. The skill correctly points to
   them and adds only the cloud-specific increment (evidence must be git-reachable; the boundary is
   the *only* drift-stopper when no operator is watching). Had D0 not been a gate, the skill would
   have restated three rules that had homes — manufacturing precisely the divergence the boundary
   condition existed to prevent.
2. **My Verification omitted a cold read of the skill itself.** Rule 4 — the plan's own
   cold-read rule — **flagged a genuine gap in the plan that authored it**: the skill is
   text-whose-value-is-what-a-later-reader-does, exactly the class rule 4 governs, yet `020`'s
   Verification specified D3 (criterion coverage) and no cold read of the skill's rules. The run
   mitigated it by instructing the Step 6 sub-agent to cold-read the skill. ⭐ **The
   self-referential blind spot D3 exists to surface, surfaced on its first use, against its own
   author.**

## Routing and Merge Behavior

**Coverage 2 of 3 — and the label suppressed only ONE bot this run, against two on #1112.**

| Reviewer | Verdict | Note |
|---|---|---|
| `coderabbitai` | `silent` | Honoured `skip-bot-review`; posted a skip notice. |
| `sourcery-ai` | `reviewed` | "I've reviewed your changes and they look great!" — zero findings. Reviewed via the draft-open race. |
| `cuioss-review-bot` | `reviewed` | "No major issues detected" — zero findings. Same race. |

⛔ **The draft-open race is non-deterministic, and that is new information.** On #1112 the label
caught CodeRabbit *and* Sourcery, leaving only PR-Agent through. Here it caught only CodeRabbit and
**both** others reviewed. Same mechanism, different outcome — so `061`'s proposal 1 is not merely
"one stray review is expected and harmless"; the number of bots that slip through is **unpredictable**,
which strengthens the case for a real fix (label-before-open) over documenting the race as benign.

- CI: `verify / conclusion` green; docs-and-skill path confirmed from git.
- `license/cla` pending (the `Claude <noreply@anthropic.com>` author identity) — **again not a hard
  gate**; the merge queue admitted and landed it, as on #1112. Two instances now.

⭐ **A premature negative was written, blocked, and correctly discarded.** The run authored a commit
recording the PR as blocked on CLA, could not push it (the queue had locked the branch), recognised
the queue's admission had *falsified* that record, and discarded the commit rather than forcing it.
The protected-branch lock accidentally prevented a wrong record from landing — but the run's own
reasoning, not the lock, is what resolved it correctly.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` → `1117`; `landing` → `landings/PLAN-TRUTH-062.md`
- [x] `plan_marshall_plan_id` deliberately empty — the cloud lane creates no plan-marshall plan
- [x] epic.md reconciled; cloud plan directory collected; resume_anchor updated

## Follow-Ups

1. **`061`'s proposal 1 is now stronger and should not be closed as "document the race".** Two runs,
   two different suppression outcomes from the same mechanism. A non-deterministic gate is worse than
   a known-broken one.
2. **`uv.lock` churn recurred — second instance**, same cause (session Python below the project
   floor). `061`'s proposal 2 is confirmed, not hypothetical. Both runs caught it themselves; a third
   may not.
3. **CLA red on every cloud run, twice non-blocking.** Still cosmetic, still permanent, still worth
   fixing at the authorship trailer.
4. **No `/sync-plugin-cache` owed** — the skill is project-local under `.claude/skills/`;
   `marketplace/bundles/` untouched. Verified from the diff.


---

## ⛔ CORRECTION 2026-08-08 — the coverage figure in this record used the WRONG DENOMINATOR

This landing reports review coverage against the **enumerated roster** (`coderabbitai`,
`sourcery-ai`, `cuioss-review-bot`). That is not the quorum. Read first-party from
`.plan/marshal.json` (`plan.phase-6-finalize.steps.plan-marshall:automatic-review`):

    required_bots = 'pr-agent'          optional_bots = 'coderabbit,sourcery'
    bot_lists_provenance = 'answered'   # a deliberate operator answer, not an unset default

Per `automatic-review/standards/bot-participation-contract.md`, an **optional** bot's silence "never
blocks" and is "not a failure". ⇒ **`cuioss-review-bot` (pr-agent) reviewing is a satisfied quorum,
1 of 1.** The "N of 3" framing above overstates a shortfall that did not exist. The operator
confirmed the classification on 2026-08-08: *sourcery stays optional for this project.*

⭐ **What the error produced that is worth keeping:** `PLAN-TRUTH-061`'s shipped disclosure derives
its population from the registry **roster** and never reads `required_bots`/`optional_bots` — so the
mechanism computes shortfalls against this same wrong denominator. That defect is real, is routed to
`review-apparatus` (`truthful-signals-022.md`), and was only visible because the arithmetic was wrong
here first.
