envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T12:36:27Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# A green `CodeRabbit` check certified a commit range CodeRabbit never read — and the honest reviewer in the same run reported SKIPPED

## Routing note

Filed to `review-apparatus` rather than `truthful-signals` per the three-way rule: this is a review-participation defect, and the PR/review test wins outright. Source plan: PLAN-TRUTH-035, PR #1083, squash `3a20814b1`.

## What was observed

On PR #1083, the final check state read:

| Check | State |
|-------|-------|
| `CodeRabbit` | **SUCCESS** |
| `Sourcery review` | **SKIPPED** |
| `verify / conclusion` | SUCCESS |

`overall_status: success`, 11 checks. The merge gate saw green.

But CodeRabbit's own review body records the range it actually read:

> Reviewing files that changed from the base of the PR and between `e1ae38142e20341d5fc5d2dee59ede31313a4437` and `bfa2a30aaf9ed8feab9bb2858659b06a95867d1e`.

The branch did not stop at `bfa2a30aa`. TASK-14 (the `cmd_enrich` idempotency fix) and TASK-15 (the four-site doc cascade) landed **after** it — those commits exist precisely because they remediate the four actionable comments CodeRabbit raised at `bfa2a30aa`. The branch head by the time of CodeRabbit's last comment was `234d8f97b5cb74669f0509e1c07c0688a60d0f94`.

When re-review was requested at that head, CodeRabbit replied (finding `d741be`, stored against `reviewed_commit_sha: 234d8f97…`):

> ✅ Action performed — Review finished.
> Note: CodeRabbit is an incremental review system and does not re-review already reviewed commits.

It performed no review of the new commits and said so. **The check stayed SUCCESS.** So the green `CodeRabbit` check certified a HEAD whose remediation commits — the highest-risk commits on the branch, since they were written under review pressure and touched the exact lines under discussion — were never read by CodeRabbit.

## The contrast is the finding

Sourcery, in the same run, reported **SKIPPED**. Sourcery did not review, and its check said it did not review. That is a correct signal and it is machine-readable.

CodeRabbit also did not review the final range — and its check said SUCCESS. Same underlying state, opposite reported signal. The apparatus cannot currently distinguish "reviewed and found nothing" from "declined to review" by reading check states, because one vendor encodes the distinction and the other does not.

## The generalisable rule

**A review bot's check state is a statement about the bot's job, not about your diff.** `SUCCESS` on an incremental reviewer means *"I have nothing queued"*, which is satisfied both by having reviewed everything and by having declined to review anything. Those are the two zeros again, sharing one representation.

The existing rule — *only `ci pr comments --pr-number N` is evidence of participation* — is necessary but is **not sufficient in this shape**, because comments WERE present. Four of them, actionable and correct, from CodeRabbit. Participation was real. What was absent was participation **at the reviewed commit**. Evidence of review must be commit-scoped, not PR-scoped.

## Proposed detector

The data needed is already stored. `manage-findings` persists `reviewed_commit_sha` on every `pr-comment` finding. The check:

1. Take `head_sha` at the merge gate.
2. For each expected reviewer, take `max(reviewed_commit_sha)` across its findings — and, for CodeRabbit specifically, parse the explicit range out of the review body, which names it verbatim.
3. If the reviewer's latest reviewed SHA is not an ancestor-or-equal of `head_sha`, the reviewer has **not** seen the merge candidate, regardless of its check state.
4. Surface that as an unreviewed-range warning at the pre-merge barrier.

Additionally: an incremental reviewer's "does not re-review already reviewed commits" reply is a **declined-review** signal and should be classified as such, not left as a `rejected` finding with no `resolution_detail` (which is how it landed here — `d741be`, `resolution: rejected`, `resolution_detail: null`, indistinguishable from a nitpick that was waved off).

## Impact

Every PR that receives review feedback and then remediates it — which is every PR that review is working on. The failure is strictly worse the better the review was: the more actionable comments a bot raises, the more remediation commits follow, and the larger the unreviewed tail that its green check covers. Directly extends the standing rule *never read a green finalize as proof the bots saw the diff* — here the check state was not merely uninformative, it was affirmatively wrong about the range.

## Positive signal worth keeping

pr-agent (`cuioss-review-bot`) independently found the same `cmd_enrich` State Mutation Bug that CodeRabbit found, with the same trace, on the same lines. Two-reviewer convergence on a real defect that the plan's own self-review missed. pr-agent participation is confirmed by stored comment body, not by summary.
