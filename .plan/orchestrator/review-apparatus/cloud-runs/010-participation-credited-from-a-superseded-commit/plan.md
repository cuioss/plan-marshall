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

# Participation is credited against something that is not the merge candidate, so a tree the required bot never saw can merge

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

The pre-merge barrier asks *"did the required bot participate on this PR?"* while the artifact that
actually merges is **one commit**. When a loop-back, a rebase, or a force-push moves HEAD after the
reviews, the per-PR answer stays `yes` and the barrier passes — for a tree no required reviewer ever
saw. This is a **false positive**: unlike every other participation defect in this epic, whose worst
outcome is a needless loop-back, this one merges unreviewed code.

**The mechanism, read first-party in merged `main`.** The currency qualifier is
`marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` §
`_has_update_movement`, and it is a **two-arm** predicate:

```python
def _has_update_movement(comment, observed_keys, bot_kind) -> bool:
    comment_id = str(comment.get('id') or 'unknown')
    if (bot_kind, comment_id) not in observed_keys:
        return True                                          # ARM 1 — first presence
    updated_at = str(comment.get('updated_at') or '')
    created_at = str(comment.get('created_at') or '')
    return bool(updated_at) and updated_at != created_at     # ARM 2 — edit movement
```

**No commit SHA is consulted on either arm.** `observed_keys` is the plan's own accumulated
observation ledger — the stored-findings keys unioned with the sidecar's noise-dropped keys — and it
is persisted after each fetch. The consequence is stated as design intent in the module's own comment:
*"the record only ever closes that arm on a LATER fetch."*

Two distinct defects follow, and they need different remedies:

1. **The credit is anchored to nothing durable.** A review of commit N satisfies the gate at commit
   N+1, because the predicate never asks which commit was reviewed.
2. ⭐ **The verdict is not idempotent — it depends on how many times you look.** The first fetch
   *consumes* the first-presence credit, so a second fetch of the same unedited comment **at the same
   HEAD** must flip `participated` → `participated_stale`. Fetch once and the PR merges on `true`;
   fetch twice and it blocks on `false`. Same bot, same comment, same tree.

The anchor the predicate needs **already exists and is simply not consulted**: `reviewed_commit_sha`
is fetched and stamped onto every finding at ingestion time in the same module.

## Goal

A participation credit is evaluated against the commit being merged, and yields the same answer however
many times it is evaluated. A required bot whose only review predates the merge candidate does not
satisfy the barrier; a bot that declined to review is recorded as having declined and does not count
toward quorum; and neither verdict changes because the predicate was run a second time.

## Deliverables

1. **D0 — GATE, mutates nothing: derive the site population and the anchor per site.** Enumerate every
   site that credits participation or consumes a participation verdict, and for each report **(a)**
   which commit, if any, the credit is compared against, and **(b)** whether the predicate is
   **idempotent** — does re-running it on unchanged inputs return the same answer.
   ⛔ **Report per site, never one answer for the system**: this plan's own evidence has two sites
   giving opposite answers, so a single global answer is proof the derivation was not done.
   ⛔ **This deliverable HALTS the plan.** If the site population cannot be derived from the tree —
   by call-graph, by grep over the participation symbols, by the registry — **say so and stop.** Do
   **not** hand-write the site list and proceed: a hand-maintained list of the sites that must stay in
   sync is the same defect class this plan is closing.
   *Done when:* a table exists naming every site, its anchor, and its idempotence verdict, and the
   enumeration method is stated so a reader can re-run it.

2. **D1 — resolve the contradiction D0 surfaces, and state one rule.** The currency test demonstrably
   withholds credit in one place and demonstrably failed to prevent a merge in another. Both cannot
   follow from one contract. Output is a **single stated rule** for which commit participation is
   credited against, applied at every D0 site.
   ⚠ If the derivation genuinely cannot settle which behaviour is correct, **record the alternatives
   and the evidence for each as a proposal in the run report and stop there** — do not pick one. There
   is no operator on this run to ratify a semantics choice.
   *Done when:* the rule is stated in `bot-participation-contract.md`, or the run report carries the
   proposal and D2–D3 are reported as not attempted.

3. **D2 — re-key the currency test onto HEAD identity.** Replace the observation-history term in
   `_has_update_movement` (and every other site D0 names) with a comparison against the merge
   candidate's SHA, using the `reviewed_commit_sha` **already stored** rather than adding a new
   observable. A review whose reviewed-SHA is an ancestor of the merge candidate is **stale evidence**,
   not absence and not participation.
   ⭐ This fixes both defects at once: an SHA comparison is idempotent, so the observer effect
   disappears with the same change.
   *Done when:* re-running the predicate twice on unchanged inputs returns the same verdict, proven by
   a test, and no participation path reads `observed_keys` as a currency signal.

4. **D3 — a bot that declines is recorded as `declined`, and `declined` does not count toward quorum.**
   ⛔ **Independently required, not a sub-clause of D2.** The two halves catch disjoint failure sets:
   D2 catches *a review anchored to a dead SHA*; D3 catches *no review at all, reported as
   participation*. A refusal at first pass leaves **no reviewed-SHA to compare**, so there is nothing
   stale for D2 to detect — there is nothing at all.
   *Done when:* a bot publishing a refusal or an incremental-review decline resolves to a distinct
   `declined` state that the quorum predicate excludes, with a test for each of the two refusal shapes.

5. **D4 — tests, each verified to FAIL before the fix.** (a) A required bot whose only review predates
   the merge candidate does not satisfy the barrier. (b) A required bot that reviewed the merge
   candidate does. (c) ⭐ **Idempotence:** evaluating participation twice at an unchanged HEAD, with the
   observation ledger written between the two evaluations, returns the same verdict — this is the
   regression for the observer effect and it fails today. (d) The site set D0 enumerated is
   **population-derived**, non-empty, and every member asserted; copy the derivation pattern from
   `test/_shared/_dispatch_roster.py`.
   ⛔ **Prove discrimination by mutation.** A review-bot fix in this tree has previously shipped a test
   that passed both before and after the change. A test that does not fail pre-fix is not evidence.

## Out of scope

- **Re-reviewing on every commit.** It trades a soundness defect for a cost and rate-limit defect, and
  this epic already carries a permanently unrecoverable diff-size refusal that more review traffic
  makes worse. The fix is to compare the credit against the right commit, not to generate more credits.
- **Widening what counts as participation so the barrier passes.** That is the failure mode this epic
  is named after and the exact inverse of this plan's purpose.
- **Flipping `re_review_on_loopback` as the remedy.** One of the observed mechanisms is a bot that
  *declines*; re-triggering it produces another decline, not a review. The remedy is D3's `declined`
  accounting, not more triggering.
- **The landing-message composition site**, owned by a separate plan in this epic. Two plans staged
  against one seam is the duplicate-spec trap.
- **Changing the cloud lane's own merge gate.** This plan changes the plan-marshall pre-merge barrier,
  which is a different gate from the one governing this run — and a run must never amend the contract
  that governs it.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the
  participation derivation, `_has_update_movement`, and the `reviewed_commit_sha` stamp.
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the
  classifier that consumes `stale_participation_bots` and `refused_bots`.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` —
  where the stated rule from D1 lands.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the
  pre-merge barrier's participation predicate.
- `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and
  `test/plan-marshall/automatic-review/test_review_completeness.py` — the test surfaces.
- ⚠ **`test_review_completeness.py` was already edited by a recent landing** (two cases migrated to the
  widened participation record). Re-read it before scoping D4 rather than assuming the pre-migration
  shape.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `_has_update_movement` is a two-arm predicate consulting no SHA, and the first fetch consumes the first-presence arm | OBSERVED | `github_pr.py` § `_has_update_movement` and the participation loop that calls it — read both, including the comment about closing the arm on a later fetch |
| `reviewed_commit_sha` is already fetched and stamped on findings | OBSERVED | `github_pr.py` § `cmd_fetch_findings`, the head-SHA fetch immediately after the participation loop |
| A required bot resolving to `participated_stale` already blocks as `absent` does | OBSERVED | `bot-participation-contract.md` § *Severity by classification* |
| The HEAD-currency test is applied **inconsistently across sites** — a second currency-blind participation path exists | HYPOTHESIS | The site enumeration D0 produces, read from `github_pr.py`, `review_completeness.py`, and the barrier's own authorization path. ⛔ Settle it by reading the code, not by reading a contract doc that restates the same inference |
| The barrier inherits a findings read from an earlier step rather than re-reading at the barrier, so a review arriving between the last fetch and the merge is invisible | HYPOTHESIS | The finalize step ordering and the barrier's findings-read call site — whether it re-queries or consumes a prior step's result |
| No consumer depends on per-PR participation semantics in a way D2 would break (an asserted **absence**) | HYPOTHESIS | Enumerate the barrier's callers. ⛔ An asserted absence is verified exactly as an asserted presence and is the higher-risk half — an unverified absence here means shipping a change that silently breaks a caller |
| `participation_requires_update` is a **per-bot registry flag**, so "inconsistent application" may resolve to "consistent application of a flag whose value differs per bot" | HYPOTHESIS | The registry records in `automatic-review/scripts/bot_registry.py` — check the flag's value per bot at D0 **before** concluding a rogue path exists |

⚠ **Every count in this plan is a lead, not a trusted number.** The site count, the number of
mechanisms, and any line reference must be **re-derived against the tree this run clones**. The
observations behind this plan span several months of landings, and the tree has moved since; a baked-in
number that no longer matches is worse than no number.

⛔ **Do not go looking for `.plan/`.** The orchestrator ledger, the plan specs, and the landing records
that evidenced this plan are git-ignored and **absent from your clone**. Everything this run needs is
in this file. Paths under `.plan/` appear here only so you know not to search for them.

## Verification

- Run the repository's full verify. Read the result payload's `status` and `errors[]` — the build
  wrapper exits 0 even on failure, so a zero exit code is not evidence.
- **Mutation-prove every test in D4.** For each, confirm it fails against the pre-fix behaviour before
  accepting it. State in the report which ones were proven this way and how.
- **Idempotence check, run twice explicitly.** Evaluate participation at a fixed HEAD, let the
  observation ledger be written, evaluate again, and assert the verdicts match. This is the check that
  distinguishes this plan from a pure SHA-anchoring change.
- ⭐ **Cold read of the contract text.** D1 writes a rule into `bot-participation-contract.md` and D3
  introduces a `declined` state. Have the pre-PR verification sub-agent read the changed text **cold**
  — without this plan — and report, in its own words: (a) which commit a credit is evaluated against,
  and (b) whether a `declined` bot blocks, is disclosed, or is ignored. If the cold reading does not
  match what D1 and D3 intended, **the wording failed**, however complete the diff looks. Report the
  reading verbatim.

## Notes

- **Sequencing.** This plan overlaps other staged plans in this epic on `github_pr.py`
  (one claims `cmd_pr_wait_for_comments`, another claims `fetch_findings`, this one claims the
  participation *comparison*) and on `branch-cleanup.md`'s barrier predicates. The boundary is
  plausible but unverified — **confirm it at D0** before assuming disjoint functions. Do not run this
  concurrently with those plans.
- **Six mechanisms converge on one outcome**, and D2 must not be scoped to any single one. They differ
  in *how* the anchor goes stale and agree completely in *what the barrier then does wrong*: a
  loop-back adding a commit after the reviews; a force-push rewriting the reviewed SHAs away; an
  incremental-review model refusing to re-review after a loop-back; `reviewed_commit_sha` frozen at
  record creation with no update path; a refusal at first pass leaving nothing to compare; and the
  observation-ledger consumption described under Problem. A fix aimed at loop-backs alone leaves the
  rest live.
- **The recorded-but-ignored bit.** On one PR the registry recorded `matched: true` alongside
  `head_sha_verified: false` — the deciding bit was computed, written down, and then ignored by the
  consumer. ⭐ The sharp edge is not the missing review (incremental review is the bot's documented,
  correct behaviour) but that **a match which cannot name the SHA it matched still satisfied the
  coverage obligation.** Locate that consumer at D0.
- **Detect and obtain are one pair.** A required bot that triggers only on `opened` / `reopened` /
  `ready_for_review` / on-demand `/review` — never on push — cannot be re-invited by a loop-back that
  pushes. Shipping only the detector converts a silent false green into a **permanent hard block** and
  would strand every loop-back. If D2 lands without a path to obtaining a fresh review, say so
  explicitly in the report rather than declaring the plan complete.
- **The highest-risk diff is the least reviewed.** Fixes written under loop-back pressure, addressing
  defects a reviewer just found, arrive after every bot has had its turn. A barrier that credits
  participation per-PR cannot see this at all — that is the outcome this plan exists to change.
