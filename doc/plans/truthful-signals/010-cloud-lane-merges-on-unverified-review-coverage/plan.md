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

# The cloud lane merges on unverified review coverage, and pays for it with the push cadence it mandates

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The lane's merge gate asks whether every PR comment was **handled**. It never asks whether any
reviewer **looked**. Those are different questions, and when no bot reviews, the first one is
trivially satisfied — "all comments handled" is vacuously true against an empty comment set. The
gate then reads green on a PR that received no review at all.

This is not hypothetical. On PR #1107 (`PLAN-CIS-021`, landed `f070d746b`) the true coverage was
**one reviewer of three**: `cuioss-review-bot` filed a correct and substantive finding, while
`coderabbitai` never reviewed (OSS rate limit, after its first attempt aborted on a mid-review head
change) and `sourcery-ai` never reviewed (weekly 500 000-diff-character limit). The run report
recorded CodeRabbit's rate-limit and **omitted Sourcery entirely** — so the operator-retained third
reviewer's silence was invisible in the record, and the merge proceeded with no caveat.

The mechanism has a second half, and it is the lane's own doing. Step 2 § "The remote is the only
durable storage" and Step 4 § "Commit and push" mandate a push after **every** commit, for a real
reason: a reclaimed VM re-clones from the remote, and unpushed work is lost. But each push to an open
PR (a) supersedes the in-flight `verify` run via GitHub Actions concurrency, emitting a spurious
`verify / conclusion` failure, and (b) changes the head mid-review, which aborts a bot's in-progress
review **and consumes its rate window**. The same run observed both: a `verify` cancellation on
`9d2444f` that was not a real failure, and two bots knocked out. **The durability rule and the
review-integrity rule are in direct conflict, and the contract resolves it nowhere.** A run today
either loses work or burns its reviewers, and it is not told which to prefer.

Compounding both: **a cloud run contributes nothing to the token corpus.** The lane persists no
`metrics.toon` and the report has no token or duration line, so every cloud run is silently absent
from corpus-wide figures. With token reduction the standing priority, a lane whose runs are
structurally invisible to measurement biases every aggregate computed from that corpus — and the
aggregate does not say so.

## Goal

A cloud run cannot merge while claiming review coverage it did not receive: reviewer participation is
established from the stored comment bodies, recorded per reviewer with an explicit
reviewed / rate-limited / silent verdict, and a shortfall is surfaced as an operator-visible caveat
rather than absorbed into a green gate. The push-cadence conflict is resolved by a stated rule rather
than left to each run to rediscover. And a cloud run reports what it cost, so the corpus stops
silently excluding a whole lane.

## Deliverables

1. **D0 — Establish the reviewer population, and prove the gate is currently vacuous.** Determine the
   repository's *expected* reviewer set from configuration rather than from memory or from this
   plan's prose (`.coderabbit.yaml`, the review-bot workflow, and whatever registers Sourcery), and
   record it. Then demonstrate the defect concretely: exhibit a merged PR whose comment set contains
   no review from one or more expected reviewers while the lane's merge gate was satisfied. #1107 is
   the known instance — confirm it against the stored comment bodies, do not restate this plan.
   *Done when:* the expected reviewer set is named with its configuration source, and the vacuity is
   shown on a real PR rather than argued. ⛔ If the population cannot be derived from configuration,
   say so and stop — a hand-maintained reviewer list is the defect this class keeps producing, and
   shipping one here would reproduce it.
2. **D1 — Record participation per reviewer, from the bodies.** Step 7 already requires reading both
   comment surfaces; make it also **record a per-reviewer verdict** — `reviewed`, `rate-limited`, or
   `silent` — derived from the stored comment bodies, never from a check state, a summary, or an
   absence of complaint. The report template gains the corresponding row set so a reviewer that never
   spoke is *visibly* absent instead of merely unmentioned.
   *Done when:* the report template carries a per-reviewer participation table over D0's population,
   and the contract requires it to be filled from bodies.
3. **D2 — Make a coverage shortfall a merge-gate caveat.** Add a condition to Step 8: when any
   expected reviewer's verdict is not `reviewed`, the run states the shortfall and its reason
   explicitly to the operator before arming auto-merge. ⛔ **This is a disclosure requirement, not a
   block** — rate limits are routine, outside our control, and blocking on them would strand every
   run behind a bot's quota. The defect is the *silence*, not the shortfall. The wording must make a
   run that merges on 1-of-3 say so.
   *Done when:* the merge gate names the disclosure condition, and its text distinguishes disclosure
   from blocking so a later reader cannot collapse the two.
4. **D3 — Resolve the push-cadence conflict explicitly.** State a rule reconciling "push after every
   commit" (durability) with "do not supersede an in-flight review or CI run" (integrity). The
   durability rule is load-bearing and MUST NOT be weakened — work has been lost to a reclaimed VM.
   The resolution therefore has to live on the other side: what may be batched, when a push is worth
   its cost, and what to do when a push has already aborted a review. Whatever the shape, it must be
   stated as a rule in the contract, at both sites (Step 2/4 and Step 7), and not as a lesson in one
   report.
   *Done when:* both sites carry the reconciled rule and neither can be read as licence to leave work
   unpushed.
5. **D4 — Report what the run cost.** Add a cost line to the run-report template — at minimum tokens
   and wall-clock duration for the run, with its source named. ⛔ **The figure MUST carry its
   population**: a cloud run's number is not comparable to a plan-marshall `metrics.toon` total
   unless the two count the same things, and a bare number that looks comparable is worse than none.
   If they cannot be made comparable, the line says so in the report rather than implying parity.
   *Done when:* the template carries the cost line with an explicit population qualifier, and
   `cloud-bridge.md` § Collect step 5 requires the landing record to carry it forward.

## Out of scope

- **Blocking a merge on bot participation.** See D2 — disclosure only. A rate limit is not a defect
  and must not strand a landing.
- **Reducing push frequency to protect reviewers.** D3 resolves the conflict without weakening
  durability; trading work-loss risk for review cleanliness is the wrong direction and is
  deliberately excluded.
- **Building a metrics pipeline for the cloud lane.** D4 is a reported figure with a stated
  population, not instrumentation. A real cloud-metrics substrate is a separate plan.
- **The plan-marshall-side collect verb.** See Notes — the `ci pr create` gap is real and separately
  filed; do not fix it here.

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — Step 7 (participation recording), Step 8 (merge-gate
  disclosure), Steps 2/4 and 7 (push cadence), and the § Report template (participation table, cost
  line).
- `doc/plans/cloud-bridge.md` — § Path 3 Collect step 5, so the landing record carries the
  participation verdicts and the cost line forward after the plan directory is deleted.
- ⚠ HYPOTHESIS: a configuration file registering the expected reviewer set (`.coderabbit.yaml` is
  referenced by CodeRabbit's own run configuration as `Repository: cuioss/coderabbit/.coderabbit.yaml`
  — possibly an org-level repo, not this one). D0 settles where the population actually comes from.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The merge gate asks only whether comments were handled, never whether a reviewer participated | OBSERVED | `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8, conditions 1–3 (read 2026-08-08) |
| Step 7 already forbids trusting a check state or a summary as evidence of participation — so the fix extends an existing principle rather than introducing one | OBSERVED | same file § Step 7, item 2 ("a green check is not evidence that a reviewer participated") |
| The lane mandates a push after every commit | OBSERVED | same file § Step 2 "The remote is the only durable storage", § Step 4 "Commit and push" |
| On #1107, coverage was 1 of 3: cuioss-review-bot reviewed; coderabbitai rate-limited; sourcery-ai rate-limited | OBSERVED | stored comment bodies via `ci pr comments --pr-number 1107`, read 2026-08-08 — not a summary, not a check state |
| The #1107 run report omits Sourcery entirely | OBSERVED | `report-01.md` § Findings → CI / PR review (names only cuioss-review-bot and CodeRabbit) |
| Rapid successive pushes superseded the in-flight verify run and aborted a bot review mid-flight | OBSERVED | same report § Findings → CI / PR review (`9d2444f` cancellation; CodeRabbit's aborted first attempt) |
| The lane persists no metrics and the report template has no cost line | OBSERVED (asserted absence) | `.claude/skills/cloud-plan-lane/SKILL.md` § Report template — enumerated its sections; none carries tokens or duration |
| The expected reviewer set is derivable from configuration rather than a hand-maintained list | HYPOTHESIS | D0 settles it against `.coderabbit.yaml` / the review-bot workflow registration. ⛔ If it is not derivable, D0 stops the plan rather than shipping a hand-maintained list |
| A cloud run's token figure can be made comparable to a `metrics.toon` total | HYPOTHESIS | D4 settles it; if not comparable, the report says so instead of implying parity |

## Verification

- The participation table and the cost line are exercised by **this run's own report** — the plan
  changes the template it must then fill, so a template that cannot be filled honestly is caught
  before merge rather than by the next run.
- D2's disclosure wording is verified by reading, not executing: it must be impossible to read the
  merge gate as blocking on a rate limit. Have the Step 6 verification sub-agent read D2's text cold
  and state which of the two it thinks the rule does — if it says "blocks", the wording failed.
- ⛔ **Every count this plan states is re-derived at the moment of the claim**, not copied from this
  file. The `1 of 3` figure, the reviewer population, and the section enumeration are all leads.
- No Python changes are expected, so the build gate will likely take its docs-only path — confirm
  that from git evidence rather than assuming it.

## Notes

- **Prior art in this exact contract.** #1108 fixed a Step 8 ↔ Step 9 ordering defect found the same
  way (a run hit it, and the contract was amended). #1105 closed two further lane-contract gaps. This
  plan continues that line; read both before scoping, since they touch the same steps.
- **The source incident** is `PLAN-CIS-021` (#1107, landed `f070d746b`; report finalization in #1108
  and #1109). Its landing analysis, which survives the plan directory's deletion, is at
  `.plan/local/orchestrator/code-intelligence-substrate/landings/PLAN-CIS-021.md` — **machine-local
  and NOT visible from a cloud session.** Everything this plan needs from it is restated above; do
  not go looking for it.
- **Related but deliberately not in scope:** `ci pr create` requires `--plan-id` and exposes no
  `--description`, so the *local* collect step's bookkeeping PR cannot be opened through the
  sanctioned CI abstraction. That gap was hit while collecting CIS-021 and is filed separately in the
  truthful-signals ledger. It is a plan-marshall-side defect; this plan is cloud-lane-side.
- **This is the truthful-signals archetype in its purest form**: a gate reports a confident green
  while suppressing the caveat that makes it wrong. The fix is disclosure, never suppression of the
  underlying condition.
