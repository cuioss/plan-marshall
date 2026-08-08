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

# The merge gate cannot tell a required check from a decorative one

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`cloud-plan-lane` § Step 8 condition 1 reads **"All checks are green."** A repository's check set,
however, contains two different kinds of thing: contexts the branch ruleset **requires** before a
merge, and contexts that merely report — advisory bots, informational statuses, third-party badges.
The contract has no vocabulary for the difference, so it treats every check as load-bearing.

The consequence is a run that stalls on something that was never going to block it. Observed twice:
`license/cla` sat pending on PR #1112 and again on PR #1117. Both PRs showed
`mergeable_state: unstable` — **not** `blocked` — and **the merge queue admitted and landed both**.
On #1117 the run went further and wrote a commit recording the PR as blocked on the CLA; it could not
push that commit (the queue had already locked the branch) and correctly discarded it once the
queue's admission falsified the claim. The record was saved by a lock, not by the contract.

Two things follow. The narrow one: the CLA is pending because a cloud run **authors** its commits as
`Claude <noreply@anthropic.com>`, where the repository convention is a `Co-Authored-By:` trailer — so
the identity has no CLA on file. The general one, and the one worth shipping: **the gate cannot
distinguish a check it must wait for from a check it may merely report**, and greenness is the wrong
question to ask of a check set.

⛔ **What this plan deliberately does NOT do.** It does not write *"`license/cla` is not a hard gate"*
into the contract. That sentence would hardcode a repo-specific, time-varying fact: if the CLA is ever
added to the ruleset, the contract would be instructing the run to ignore a real blocker — a
suppressed caveat inside the document whose purpose is to prevent suppressed caveats. Required-ness is
**machine-readable**, so it is derived, not asserted.

## Goal

The merge gate asks the right question — *is every **required** context present on this exact head and
concluded successfully?* — and answers it from the ruleset rather than from the shape of whatever came
back. A pending non-required check is disclosed and does not block. Nothing in the contract names a
specific check as ignorable.

## Deliverables

1. **D0 — GATE: derive the required-context set from the ruleset.** Read, from the repository's
   ruleset / branch-protection configuration via this run's GitHub access path, which contexts are
   **required** on `main`, and record the list. Confirm from that list whether `license/cla` is among
   them.
   *Done when:* the required set is recorded in the report with the API surface it came from, and the
   CLA's membership is stated as read rather than assumed.
   ⛔ **STOP CONDITION — this deliverable may end the plan.** If the required set cannot be derived
   programmatically, **halt and report that**. Do **not** fall back to writing a hand-maintained list
   of required checks into the contract: a hand-kept list of what matters is the same defect class
   `010`'s D0 refused, and it would rot silently the first time the ruleset changes.
2. **D1 — Step 8 condition 1 asks about required-ness, not greenness.** Reword it so the gate is
   satisfied when **every required context is present on the exact head SHA and concluded
   successfully**, and so that a **non-required** context which is pending, failed, or absent does
   **not** block the merge but **is disclosed** to the operator alongside the § Step 8 coverage
   disclosure `010` shipped.
   *Done when:* the condition names the ruleset as the source of required-ness, distinguishes
   *disclose* from *block* in the same way condition 4 already does, and **names no individual check**.
   ⛔ Do not weaken the "present on the exact head SHA" half — a required context that is *absent* is
   the failure mode that nearly cost a merge elsewhere, and absence must never read as satisfaction.
3. **D2 — Record the CLA root cause as an operator proposal, not a fix.** In § What have we learned,
   record that cloud runs author commits as `Claude <noreply@anthropic.com>` while the convention is a
   `Co-Authored-By:` trailer, that this leaves `license/cla` permanently red on every cloud run, and
   that fixing it is an authorship-identity decision.
   *Done when:* the proposal is recorded. ⛔ **Do not change commit authorship in this run** — it is a
   decision with no operator present to make it, and the lane forbids self-approving that class of
   change.

## Out of scope

- **Writing "`license/cla` is not a hard gate" into the contract** — see Problem. Naming one check as
  ignorable is precisely the suppressed caveat this epic exists to remove, and it would be wrong the
  moment the ruleset changes.
- **Changing commit authorship or signing a CLA** — that is D2's recorded decision, and a run with no
  operator must not make it.
- **`010`'s three open contract proposals** (the `skip-bot-review` draft-open race, the `uv.lock`
  bootstrap churn, the Step-9 Bridge-row wording). They are operator-pending and touch Steps 7/8/9;
  this plan touches Step 8 condition 1 only. Silently resolving one while adjacent to it would take a
  decision the operator has not yet made.
- **`doc/plans/cloud-bridge.md`** — the merge gate is execution, not bridge lifecycle. Editing it here
  would blur a boundary two plans have just spent effort drawing.

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — § Step 8 condition 1, plus the § Report contract-check
  row **only if** it restates the condition (check; do not assume it does).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Step 8 condition 1 reads "All checks are green" and carries no notion of required-ness | OBSERVED | `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8 — **re-read it; `010` amended this section, so the wording may have moved** |
| `license/cla` was pending on #1112 and #1117, both `mergeable_state: unstable` (not `blocked`), and both landed | OBSERVED | the two PRs' merge states via the GitHub API — re-derive, do not trust this restatement |
| The CLA is pending because cloud runs author commits as `Claude <noreply@anthropic.com>` | OBSERVED | `git log --format='%an <%ae>'` on either merged cloud branch's commits |
| The required-context set is readable from the ruleset / branch-protection API by this run | HYPOTHESIS | D0 itself, which **HALTS** if it is not |
| `license/cla` is not in the required set | HYPOTHESIS | D0's derived list — ⛔ this is the plan's central premise and it is **not** assumed; if D0 finds the CLA *is* required, the observed landings need re-explaining and the plan re-scopes rather than proceeding |
| No other non-required check has stalled a run so far | HYPOTHESIS | re-read both runs' full check sets; a second instance strengthens D1's wording rather than changing it |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1 is text whose whole value is what a later reader does with it**, so it gets a **cold read**:
  have the Step 6 verification sub-agent read the reworded condition 1 with no other context and
  report (a) what it would do about a pending non-required check, and (b) what it would do about a
  required context that is *absent* from the head. The correct answers are **proceed-with-disclosure**
  and **block**. If it answers "ignore the CLA" or treats absence as satisfaction, the wording failed
  regardless of how complete it looks.
- The reworded condition must name **no individual check** — grep the new text for `cla` and confirm
  the only occurrences are in the report's evidence sections, never in the rule.
- Docs-and-skill change only; no `*.py` expected, so the build gate will likely take its docs-only
  path. Confirm from git evidence rather than assuming.

## Notes

- **Prior art, read it first:** `010` (PR #1112) shipped § Step 8 condition 4, the coverage-shortfall
  **disclosure** — deliberately a disclosure and not a block. D1's non-required-check handling should
  read as a sibling of that condition, using the same disclose/block vocabulary rather than inventing
  a second one.
- **The operator supplied the observation that motivated this plan** ("the CLA is not a hard gate") and
  it is correct as an observation. The plan implements the *general* rule it is an instance of, rather
  than the sentence itself, for the reason given under Problem. That reframing is recorded here so the
  run does not "restore" the simpler wording thinking it is being helpful.
- ⛔ **Do not go looking for the orchestrator spec or the landing records.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file.
