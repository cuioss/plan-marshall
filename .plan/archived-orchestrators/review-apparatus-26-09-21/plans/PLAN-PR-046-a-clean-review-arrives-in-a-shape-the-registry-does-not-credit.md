# PLAN-PR-046: A clean review arrives in a shape the registry does not credit

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from two operator-relayed data-points. ⭐ **The root cause below is CONFIRMED
> first-party on `cuioss/cui-http#194`**, and it explains BOTH observations with ONE mechanism —
> replacing the diagnosis the first run gave, which was refuted at HEAD `30cd8aaf8`.

## Objective

CodeRabbit publishes its **clean-review verdict** as an `issue_comment`. Its registry declares
`participation_evidence: [review_body, inline]` (`coderabbit.md:41-43`) — **`issue_comment` is not a
credited shape for it.** So a CodeRabbit run that reviewed the exact merge tree and found nothing
earns **no participation credit, by construction**, and resolves `absent` — the state reserved for
*"this bot did not review"*.

⭐ **This is the epic's own thesis reproduced by our own registry**: *reviewed-clean* and
*nobody-reviewed* are one signal, and here the collapse is caused by us, not by the reviewer.

Two live consequences, in opposite directions and both wrong:

1. **A false block** — `absent` on a required bot holds the merge barrier against a review that
   exists and passed.
2. **A false WAIT** — with the bot reading `absent` and no script-level refusal to explain it, the
   executing plan inferred a quota window and waited. ⛔ Nothing was going to arrive: the review had
   already happened. CodeRabbit's window is `awaitable_window` (`coderabbit.md:58`), so the wrong
   inference is also the *plausible* one.

## Deliverables

### D0 — Credit the clean review by its STRUCTURAL marker, never by widening the shape

⛔⛔ **DO NOT simply add `issue_comment` to CodeRabbit's `participation_evidence`.** Its walkthrough /
summary comment is *also* an `issue_comment` and is posted **before** any review completes — a bare
shape widening would credit participation on a comment that proves a review started, not one that
proves it finished. That replaces a false negative with a false positive, which is worse here because
it fails toward merging.

⭐ **The anchor already exists in the payload.** CodeRabbit wraps the verdict in its own machine
marker — observed first-party on #194:

```text
<!-- recent_review_start -->  No actionable comments were generated in the recent review. 🎉
```

Credit the clean review on the **marker**, in the same registry-derived spirit PLAN-PR-043 D2
requires: *recognise the wrapper shape or derive the set, never chase the literal.*

*Done when:* a CodeRabbit `issue_comment` carrying the clean-review marker credits participation, and
a **matched negative control** holds — the walkthrough/summary `issue_comment`, alone, still credits
nothing. Both pinned by tests whose pre-fix forms fail.

### D1 — A clean review must be distinguishable from a review that found things, not just from silence

Once credited, the verdict must land in a member that says *reviewed, found nothing* rather than
collapsing into plain `participated`. `participated_but_empty` already exists in the taxonomy —
establish whether it is the right member here or whether it carries a different meaning, and record
the answer either way.

⛔ Do not introduce a new state before checking the eleven that exist. This epic has one state
vocabulary and it is already large.

*Done when:* a clean review renders a member whose text a consumer can distinguish from both
`absent` and a findings-bearing `participated`, with the choice recorded against the existing
taxonomy.

### D2 — Say it where the WAITING decision is made

The false wait is the costlier half and it happens above the classifier. The plan saw an `absent`
required bot with an awaitable rate class and inferred a window.

⛔ **Fix the producer's claim, not the waiter.** The waiter behaved reasonably on the input it had —
the same rule this epic applied to the `auth_failed` misclassification folded onto PLAN-PR-036. With
D0 landed the input is correct and the inference no longer fires.

What remains is disclosure: the recovery's own escalation text should state which observation put the
bot in its current state, so an operator reading *"awaiting CodeRabbit's rate window"* can see whether
any refusal was ever observed. ⛔ A wait armed on **no observed refusal at all** is a distinct
condition from a wait armed on a read one, and only one of them is legitimate.

*Done when:* the rate-window wait names the observation that armed it, and a wait armed with an empty
`refused_bots[]` for that bot is reported as unarmed rather than entered.

Three deliverables, comfortably inside the split guard.

## Claim Labels

- OBSERVED: on `cuioss/cui-http#194` CodeRabbit's ONLY comment is an `issue_comment` (3 comments
  total: `sourcery-ai` `review_body`, `coderabbitai` `issue_comment`, `cuioss-review-bot`
  `issue_comment`). Re-derived first-party via the CI abstraction against that repo.
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: that `issue_comment` carries `<!-- recent_review_start -->  No actionable comments were
  generated in the recent review. 🎉`. Read verbatim from the fetched payload.
- OBSERVED: CodeRabbit declares `participation_evidence: [review_body, inline]` — `issue_comment` is
  absent. Confirm/refute at `coderabbit.md:41-43`.
- OBSERVED: CodeRabbit declares `rate_limit_class: awaitable_window`, which is why an unexplained
  `absent` invites a wait rather than an escalation. Confirm/refute at `coderabbit.md:58`.
- OBSERVED: CodeRabbit's `refusal_patterns` are exactly `"Review limit reached"` and `"Review rate
  limited"` — **neither matches the clean-review text**, so no script-level arm classified it as a
  refusal. ⇒ The false wait was an AGENT-level inference, not a producer misclassification.
  Confirm/refute at `coderabbit.md` § `refusal_patterns`.
- ⛔ REFUTED — **the earlier run's diagnosis, recorded so it is not re-adopted**: that the noise
  pre-filter's consumption of the clean text (`count_skipped_noise`) is what denies the credit. The
  noise drop sits at `github_pr.py:1551` inside the FINDING-PERSISTENCE loop (`:1446`), while
  participation is credited in a separate loop (`:1313`) that consults no noise predicate. The
  string IS in `ignore_patterns` (`coderabbit.md:47`) — that limb held; the causal limb did not.
- HYPOTHESIS: the same mechanism explains the earlier foreign-system observation (a coverage-stamped
  clean review scoring `absent`). The two are consistent and the marker is the same, but that PR's
  comment `kind` was never read. Confirm/refute by reading it (verify-at-outline).
- OBSERVED — **n = 2, and the consequence is named**: independently reported reproduced on BOTH
  `cui-http#193` and `#194`, where the resulting `absent` **caused a loop-back and required the
  force-done escape hatch**. ⚠ #194 was re-derived first-party here; **#193 was NOT read** — it rides
  the reporter's observation. So the count is one checked instance plus one reported, not two checked.
- ⚠ NOT ESTABLISHED: whether other registered bots publish a clean verdict in an uncredited shape.
  ⛔ Sourcery declares the same `participation_requires_update: false` posture and was NOT checked
  here — an unchecked limb, not a clean one. D0 must derive the answer per bot, not assume CodeRabbit
  is the only case. ⭐ Sourcery has since been found to carry a SEPARATE defect on the refusal side
  (folded onto PLAN-PR-043 D2) — that is a different failure and does NOT discharge this limb.

### D3 — The same mechanism reached from the other side: an in-place republish reads as `declined`

⭐ **Folded from `truthful-signals-043.md` item 2** (2026-09-04, relayed from TokenSheriff — ⛔ a foreign-repo
LEAD, not corroborated here) and **independently corroborated first-party** by this epic's own finding
`e8bde7` on PR #1388.

⛔ **The false negative is high-severity because of its remedy: the documented handling for `declined` is to
ask the operator to merge UNREVIEWED.**

pr-agent (`cuioss-review-bot`) does not post a new comment per review. The PR timeline carried exactly ONE
entry. On re-trigger it **edits that same comment in place**: `/review` → workflow run
(`event=issue_comment`) → the comment's `updated_at` moves → its body now carries
`(Review updated until commit faf76712c81ec…)` plus *"PR contains tests"*, *"No security concerns
identified"*, *"No major issues detected"*. **The required bot had reviewed the current HEAD and cleared it.**

**Why the classifier got it wrong:** it SHA-verifies only via the **`review` signal path**. The
`issue_comment` path does not inspect body content, so it never sees the embedded SHA. An in-place update
produces no new comment to match, so it resolved `head_sha_verified: false`,
`matched_signal: issue_comment` → **`declined`**.

⭐ **This is D0's structural-marker rule reached from the opposite direction**, and it names the marker
precisely: **the reviewed-commit SHA embedded in the comment body**. ⭐ A cheap corroborating tell:
**`updated_at` later than `created_at`, landing shortly after a review trigger, is an in-place republish.**

*Done when:* an in-place republish is credited from the SHA in its body rather than denied for lacking a
`review` object, and `declined` is reserved for a bot that genuinely answered without naming a commit.
**Matched negative control required:** a comment edited for an unrelated reason, naming no commit, still
resolves `declined`.


## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — D2, the rate-window recovery
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` — only if D0's per-bot derivation implicates it
- OBSERVED: `test/plan-marshall/automatic-review/`, `test/plan-marshall/workflow-integration-github/`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — D3: where `head_sha_verified` is computed from the signal type rather than from the body.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — D3: the in-place-republish evidence declaration.

## Dependencies and Sequencing

- ⛔ **Overlaps `coderabbit.md` and the `github_pr` family** — never concurrent with PLAN-PR-043,
  PLAN-PR-045, PLAN-PR-042, PLAN-PR-025B, PLAN-PR-029, PLAN-PR-035, PLAN-PR-040, PLAN-PR-044.
- ⭐ **Composes with PLAN-PR-043 D2** (derive the refusal set, never widen the literal) — D0 applies
  the same rule to the CLEAN-review side. If 043 lands first, reuse its derived-recognition seam
  rather than adding a second one.
- ⭐ **Composes with PLAN-PR-045** (the currency-blind gap): 045 asks *which commit did this comment
  read*, 046 asks *does this comment count as a review at all*. Both key on the same evidence
  declaration; whichever lands second must re-read the other's changes to `participation_evidence`.
- ⛔ **NOT a fold onto PLAN-PR-026** despite sharing its title's subject: PR-026 already carries
  SEVEN deliverables (D0–D6), over the split guard. Recorded so the omission reads as a decision.
- ⚠ Re-derive the live-plan collision set before launch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-046-a-clean-review-arrives-in-a-shape-the-registry-does-not-credit.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
