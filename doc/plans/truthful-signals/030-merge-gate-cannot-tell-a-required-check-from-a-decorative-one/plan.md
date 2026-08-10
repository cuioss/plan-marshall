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
4. **D3 — The documented merge command is wrong for this repository.** § Step 8 documents
   `gh pr merge {N} --squash --auto`. On a merge-queue repository the queue owns the merge strategy, so
   passing `--squash` is **rejected** — the command errors with *"The merge strategy for main is set by
   the merge queue"* and auto-merge is **not armed** (`autoMergeRequest` stays `null`). The working
   form is `gh pr merge {N} --auto`. Correct the documented command and state why the strategy flag is
   omitted.
   *Done when:* the command in § Step 8 is the one that works, with a one-line reason. ⛔ **Re-derive
   the failure before editing** — run the documented form against this run's own PR and record what it
   returns; if it succeeds here, this deliverable is refuted and drops rather than shipping on a
   restated claim.
5. **D4 — Warn that the build gate can leave lockfile churn, and stage explicitly.** A `./pw` run under
   a session interpreter older than the project floor rewrites `uv.lock`; `git add -A` then ships it
   into a deliverable commit. Observed in **two consecutive runs**, both of which caught it only
   because they looked. Add the hazard to § Step 4/5 and state the rule: **stage the deliverable paths
   explicitly, never `git add -A`**, and check for stray lockfile churn before committing.
   *Done when:* the hazard and the staging rule are stated where a run commits.
6. **D5 — The Step-9 Bridge row forbids a change a deliverable can legitimately require.** Its wording
   ("Nothing under `doc/plans/` outside this plan's own directory was changed") collides with a plan
   whose declared surface includes a shared lane doc. Reword it to prohibit **status/bookkeeping**
   writes outside the plan directory, explicitly permitting declared-deliverable edits to shared lane
   docs.
   *Done when:* the row's wording matches its intent and no longer contradicts a legitimate deliverable.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables, at the split presumption. **No
split** — D0/D1 are the substance and D2–D5 are single-paragraph corrections to the *same file, mostly
the same section*, each carrying its own evidence. Splitting would produce a second plan that edits the
same skill for one paragraph, which is worse: two PRs racing one file. If D0 halts, D3–D5 still stand
on their own evidence and the run says so rather than abandoning them.

## Out of scope

- **Writing "`license/cla` is not a hard gate" into the contract** — see Problem. Naming one check as
  ignorable is precisely the suppressed caveat this epic exists to remove, and it would be wrong the
  moment the ruleset changes.
- **Changing commit authorship or signing a CLA** — that is D2's recorded decision, and a run with no
  operator must not make it.
- **The `skip-bot-review` draft-open race** — `010`'s first proposal, and the one of its three that is
  **deliberately still excluded**. It needs a design decision (document the race as expected, versus
  restructure PR creation so the label exists before the `opened` event fires), and evidence now shows
  the race is **non-deterministic**: on #1112 the label suppressed two of three bots, on #1117 only
  one. A run with no operator must not pick between those options — per the no-operator rule, it would
  be authoring a decision it cannot make. `010`'s proposal stands; this plan does not touch it.
  *(`010`'s other two proposals — lockfile churn and the Bridge row — are D4 and D5 above: both are
  wording corrections with no decision in them, and the operator has approved folding them in.)*
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
| § Step 8 documents `gh pr merge {N} --squash --auto` | OBSERVED | that file § Step 8 — re-read it |
| `--squash` is rejected on this queue-gated repo and leaves auto-merge unarmed | OBSERVED | observed on PR #1111: *"The merge strategy for main is set by the merge queue"*, `autoMergeRequest: null` afterwards, and `--auto` alone then reported "already queued". ⛔ **D3 re-derives this against its own PR before editing** |
| `./pw` rewrites `uv.lock` under a session interpreter below the project floor, and `git add -A` ships it | OBSERVED | both prior cloud runs' reports; reproducible by checking `git status` after the build gate |
| The Step-9 Bridge row's wording forbids a declared-deliverable edit to a shared lane doc | OBSERVED | that file § Step 9 contract-check table, Bridge row |

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
