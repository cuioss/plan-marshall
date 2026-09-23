# PLAN-PR-045: A bot that never gets currency-tested is credited on a superseded review

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-056` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1–D3 are carried there as D9–D11 and D0/D0a fold into that plan's merged D0
> gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every
> deliverable body, and `PLAN-PR-056` points here rather than retyping it.

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-09-02 from inbox `truthful-signals-042.md` (finding, forwarded from
> `refresh-identity-and-scope-defences-002.md`). ⭐ **Every claim below was re-corroborated
> first-party before staging, including the foreign-repo observation the sender itself filed
> as an uncorroborated lead** — and that corroboration came back STRONGER than the message.
> See Claim Labels for the two limbs that did NOT settle.

## Objective

`automatic-review/standards/bot-participation-contract.md` § *"The currency-blind path for
append-per-review bots — an accepted, bounded gap"* records this behaviour as a deliberate
acceptance and names its own reopening condition:

> Either of two observations reopens it: a required bot declaring `participation_requires_update:
> false` observed satisfying the quorum on a merge candidate it demonstrably did not review, or a
> decision to anchor every bot declaring `participation_evidence`.

**The first observation has now occurred and is corroborated first-party.** `PLAN-PR-024` (shipped,
#1349) excluded closing this for two stated reasons — *"a cloud run can neither observe those bots'
real publishing behaviour nor obtain the sign-off such a change needs."* This plan exists because
**the first half of that blocker is now discharged and the second half is not.**

⛔ **This plan does NOT presume the fix.** `PLAN-PR-024` reasoned carefully about a blast radius that
reaches every consumer project whose `required_bots` names an append-per-review bot, and one
observation does not supersede that reasoning. D1 is a DECISION with recorded rejected arms.

## Deliverables

### D0 — State the affected population before choosing a disposition

⭐ **The gap is bounded to bots declaring `participation_requires_update: false`, and the registry
says that is TWO bots, not one** — `coderabbit.md:44` and `sourcery.md:36`. The message named only
CodeRabbit. The same fact read from the other side: `pr-agent.md:428` states pr-agent is *"today the
ONLY bot that can reach `participated_stale`"*.

⛔ **Derive the set from the registry, never from this paragraph** — a count written here goes stale
the moment a standards doc is added or a flag flipped, which is the exact defect class this epic
tracks.

*Done when:* the affected bot set is derived from `bot_registry` at implementation time and published
with its population; and the consumer-project exposure is stated as a derived figure, not asserted.

### D1 — Decide the disposition, with the rejected arms recorded

Three arms, from the sender. Pick one; record why the others were rejected:

| Arm | What it does | Cost |
|---|---|---|
| (a) **Currency-test unconditionally** | `reviewed_commit_sha` (or comment `updated_at` vs head commit time) compared for every bot; `participation_requires_update: false` at most skips the *update-detection heuristic*, never the currency check | Changes the merge verdict for every consumer project with an append-per-review required bot |
| (b) **Invalidate on non-fast-forward head change only** | Keep the per-bot flag; drop prior participation credit when the head moves by force-push/rebase — the one case *"presence IS the movement"* cannot cover | Narrower blast radius; leaves the ordinary-advance case credited as today |
| (c) **Keep the acceptance, widen the disclosure only** | Ship D2 alone | Cheapest; leaves the false green reachable |

⛔⛔ **ARM (a) AND ARM (b) BOTH REQUIRE OPERATOR SIGN-OFF** — that is the un-discharged half of
`PLAN-PR-024`'s exclusion, and it is a decision, not a technical question. Do not implement (a) or
(b) without it. Arm (c) does not.

⛔ **The contract's own reason for not closing it is NOT superseded and must be answered, not
skipped:** an append-per-review bot's comments carry no reviewed SHA, so anchoring them requires
deciding what a new comment's presence proves about the commit it was posted against. That is a new
contract question. *"Widening the reach without settling it would replace an over-credit with an
equally unfounded verdict in the other direction."*

*Done when:* one arm is implemented, the other two are recorded as rejected with their reason, and
the § "accepted, bounded gap" passage is rewritten to match the outcome — including the case where
arm (c) is chosen and the acceptance stands with its trigger marked FIRED.

### D2 — Make the discriminator readable, whichever arm wins

An operator-level requirement (*"a CodeRabbit review is required"*) is satisfiable today by three
different green-looking signals, only one of which is a review of the actual head:

| Signal | What it actually proves |
|---|---|
| `review_completeness` credits `participated` | a comment in a declared publish shape exists — at SOME commit |
| `github_pr bot_completion --bot-kind coderabbit` → `completed: true` | the **status check** finished |
| a CodeRabbit check green in the CI set | the check ran |

Surface `participated_at_head` vs `participated_stale` (or an equivalent discriminator) in the
classifier's own output so a consumer cannot read a stale credit as a current one.

⛔ **A matched negative control is required:** a bot credited on a comment that genuinely DOES
post-date the merge candidate must still render the at-head member. Without it a false green is
merely replaced by a false amber.

### D3 — Name the composition, because neither path alone predicts the failure

⭐ **The rate-limit path and the currency-blind path compose.** The contract's mitigation — *"self-
limiting in the common case: an append-per-review bot re-triggered on the advanced HEAD posts a NEW
comment"* — assumes the re-trigger is **served**. When it is declined for quota, no new comment ever
arrives and the stale credit stands unchallenged.

The observation window makes the size of that concrete: the head advanced at 20:50:49Z and
CodeRabbit's next review body did not arrive until **07:30:21Z the following morning**.

⛔ **Coordinate, do not duplicate:** `PLAN-PR-043` owns refusal recognition and the trigger-B
selector; `PLAN-PR-025B` owns the refusal-recovery arming. This plan owns only the currency half and
must state the composition at the contract, not re-implement either.

*Done when:* the contract passage names the compose case explicitly, and the cross-references to
PLAN-PR-043 / PLAN-PR-025B are one-directional (this plan points at them; they are not edited here).

Four deliverables, comfortably inside the split guard.

### D0a — A THIRD-PARTY CORROBORATION of D0's population, with a concrete false-green instance

⭐ **Folded from `truthful-signals-048.md` item 1, direction 1 on 2026-09-05** — relayed from the
TokenSheriff lessons-handling epic (`lessons-handling-26-09-04-01`, PLAN-01 `pre-commit-gate-truthfulness`,
merged as **PR #713 / `29d9f6c5`**), filed there as finding `74ad95`. ⛔ **Foreign narrative, corroborable
mechanism**: the code path it names is ours and is readable here; the observed instance is theirs and is
NOT re-derived in this checkout.

**The mechanism, as they state it:** `github_pr.py` applies the HEAD-currency test **only** to bots that
declare `participation_requires_update`. Every other required bot — **`coderabbit` among them** — is
credited on the strength of **ANY historical comment**, with no check that the comment postdates the
commit it is credited against.

⛔⛔ **Their observed instance is the one this deliverable's D0 was trying to establish:
CodeRabbit's review timestamp PREDATED the commit it was credited against, and the gate reported a
satisfied quorum for a HEAD no reviewer had seen.**

**Their proposed remedy, which reads correct here and is recorded as an ARM for D1, not as a decision:**
make the HEAD-currency test **unconditional**, and let `participation_requires_update` select at most the
**strictness** of the freshness test (*"reviewed this exact SHA"* vs *"commented after the last push"*) —
**never whether freshness is checked at all.** Fail-closed default: a bot whose latest comment predates
HEAD is `unproven`, not `participated`.

*Done when:* D0's population statement **cites this instance as corroboration** rather than re-deriving
it, and D1's rejected-arms record includes the unconditional-test arm with its own verdict. ⛔ **This is
a corroborating instance, not new work** — the relaying epic said so itself and asked for the duplication
check before staging. It is folded here for exactly that reason and MUST NOT become a separate plan.

## Claim Labels

- OBSERVED: the currency test is reached only through `if _requires_update and not
  _reviewed_at_merge_candidate(...)`, with `_requires_update =
  bot_registry.participation_requires_update(_bot_kind)`. Read first-party at
  `workflow-integration-github/scripts/github_pr.py:1317` and `:1338`, HEAD `30cd8aaf8`.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: Mechanism unchanged: github_pr.py did not move this window and _reviewed_at_merge_candidate still resolves there (5 occurrences), so the currency test is still reached only through the _requires_update conjunction. Only touched declared path is .github/workflows/, and the sole change there is the v0.28.0-to-v0.29.0 SHA-pin bump - no trigger/permission/job-surface change. Prior inertness finding (#1510's currency guard still callerless) undisturbed.
- OBSERVED: CodeRabbit declares `participation_requires_update: false` (`coderabbit.md:44`) and so
  does **Sourcery** (`sourcery.md:36`) — the population is TWO bots. Confirm/refute at both files.
- OBSERVED: the gap is a documented, accepted residual whose reopening trigger is named in the
  contract. Confirm/refute at `bot-participation-contract.md` § "The currency-blind path…" — the
  quoted condition was read verbatim at that anchor.
- OBSERVED: `PLAN-PR-024` excluded disposition (a) citing unobservable bot behaviour AND missing
  sign-off. Confirm/refute at `PLAN-PR-024` § Out of scope (read verbatim; landing PR #1349).
- OBSERVED: on `cuioss/TokenSheriff#682` (merged) CodeRabbit posted 2 inline + 1 review body at
  `2026-08-31T20:26:12–13Z`, and that review body names its own range as ending at the OLD head
  (`379afb77...99c3699297a148f6a48b97d7294f8a87b69412fa`). Re-derived first-party via the CI
  abstraction against the foreign repo — NOT taken from the message.
- OBSERVED: the head advanced to `82e6597d66ebd379dae04c3798dc70399cdc6fcd` at `2026-08-31T20:50:49Z`
  (author and committer date identical), **24 minutes after** that review. Re-derived first-party
  with `git -C` in the TokenSheriff checkout.
- OBSERVED — **stronger than the message filed it**: CodeRabbit's NEXT review body on that PR is
  `2026-09-01T07:30:21Z`, so no CodeRabbit review of the advanced head existed for roughly **10.7
  hours**. The later range `99c36992...cf8acb8` did eventually cover `82e6597d` (verified: it is an
  ancestor of `cf8acb8`) — the next morning, not in the window.
- ⚠ UNVERIFIABLE — the `2026-08-31T20:51:18Z` "Review limit reached" decline notice is **not in the
  PR's current comment set**, read two days post-merge. ⛔ **This is NOT a refutation**: such notices
  are transient and CodeRabbit removes them. The sender observed it live and quoted an exact
  timestamp and wording. Confirm/refute is no longer possible from the PR; treat the decline as
  reported-not-reproduced and do NOT build a Done-when on it.
- ⚠ NOT CHECKED: that findings `3ff3c0` / `dcf252` / `6b6f49` carry `reviewed_commit_sha:
  99c3699…`. That store belongs to the foreign plan and was not read. An unchecked limb, not a clean
  one.
- HYPOTHESIS: the credit actually granted in that window came through the currency-blind path rather
  than through some other arm. Confirm/refute by replaying `fetch_findings` against a fixture
  reproducing the observed comment set and head (verify-at-outline). ⛔ The mechanism is corroborated
  from code and the timeline is corroborated from git, but the CREDIT ITSELF was observed by the
  sender, not by this orchestrator.

### D-FOLD 2026-09-04 — `participated_stale` does not merely misreport: it does not TERMINATE

⭐ **Folded from `truthful-signals-045.md` §2.4** (foreign LEAD; the plan-marshall surfaces are local).

pr-agent does not auto-review on push, so after fix commits its clean verdict describes a **superseded
tree**. Reported as participation it is closer to non-participation: *"the finding set is empty because
the bot never looked, not because the tree is clean."*

⛔ **The recurrence showed the state is NON-CONVERGING.** Under `re_review_on_loopback: false` nothing
re-triggers the bot, and re-firing `automatic-review` re-observes the same stale state **forever** — the
step that reports the gap has no mechanism to close it. Unblocked by hand with a `/review` comment.

⭐ **The fix is narrower than "add a nudge mechanism":** the trigger is a **declared property of the
installed caller workflow**, readable from the same configuration the bot roster comes from. When the
barrier observes `participated_stale` for a bot whose workflow declares a comment trigger, **post that
trigger and re-wait — once, bounded — before escalating to `review-barrier-gap`.**

⛔ Non-convergence archetype, **fifth instance** in this epic. Cross-reference `PLAN-PR-025B` D10: that
deliverable's corrected rule (never re-trigger *inside* a quota window) bounds this one — the bounded
re-trigger here is legal only when the bot is stale, **not** when it is quota-refusing.


## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- OBSERVED: `test/plan-marshall/automatic-review/`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — the 2026-09-04 fold: the bot's declared comment TRIGGER, read from the same configuration the roster comes from.
- HYPOTHESIS: `.github/workflows/` — the 2026-09-04 fold: the installed caller workflow whose declared trigger the barrier reads before escalating.

## Dependencies and Sequencing

- ⛔ **Overlaps the `github_pr` family** — never concurrent with PLAN-PR-043, PLAN-PR-025B,
  PLAN-PR-029, PLAN-PR-035, PLAN-PR-040, PLAN-PR-044.
- ⛔ **`bot-participation-contract.md` is a SHARED document.** Do not resolve ownership from this
  spec — the authority is the shared-document split table `PLAN-PR-024` § Dependencies points at.
- ⭐ **Composes with PLAN-PR-043 (refusal recognition / trigger-B) and PLAN-PR-025B (refusal-recovery
  arming).** If either lands first, re-read its landing before scoping D3 — the compose case may
  already be partly described.
- ⚠ Re-derive the live-plan collision set before launch. ⛔ As of 2026-09-02 that axis is
  UNINFORMATIVE (all live plans declare no footprint) — see the epic's Open Defect.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-045-a-bot-that-never-gets-currency-tested-is-credited-on-a-superseded-review.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
