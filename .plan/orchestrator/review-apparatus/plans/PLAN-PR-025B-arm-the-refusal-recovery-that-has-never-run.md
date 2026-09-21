# PLAN-PR-025B: Arm the refusal recovery that has never run (the recovery)

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> D7–D9 were folded into PLAN-PR-025 by operator decision on 2026-08-24 (CodeRabbit as a required
> default with a six-attempt rate-window retry). The bodies below are copied BYTE-FOR-BYTE from it.
>
> PLAN-PR-025 reached **ten** deliverables and was unemittable whole. The seam is the one the operator
> settled on 2026-08-24 — **recording vs recovering** — and it was cut here, unchanged:
>
> | Split | Deliverables | Subject |
> |---|---|---|
> | **PLAN-PR-025A** (this spec) | D0–D6 | A refusal is *detected, classified and described* correctly. |
> | **PLAN-PR-025B** | D7–D9 | An *awaitable* refusal is *acted on*: config, attempt budget, jitter. |
>
> ⭐ **PLAN-PR-025 is RETIRED, not deleted** — it remains on disk as the audit record of why the split
> happened, and its queue row is retired with both successors named. Every deliverable body below was
> copied from it **byte-for-byte**; no requirement was reworded in transit.
> ⛔ **Sequence 025A → 025B, never concurrent.** 025B depends on this spec's **D1**: D1 emits the
> refusal `cause` on both producers, and the recovery sequence branches on cause BEFORE
> `rate_limit_class`. They also share `bot_registry.py`, `automatic-review/SKILL.md` and `coderabbit.md`.

## Objective

An *awaitable* refusal is acted on rather than merely recorded: promote CodeRabbit into the required
set so the recovery sequence can fire for it at all, make the retry budget configurable and raise it to
six, and add a bounded jitter whose purpose in THIS lane is written down rather than ported from a lane
whose rationale does not transfer.

## Dependencies and Sequencing

- ⛔⛔ **DEPENDS ON PLAN-PR-025A's D1 — this is the load-bearing dependency and the reason the fold was
  correct rather than convenient.** D1 emits the refusal **cause** on both producers, and the recovery
  sequence branches on cause **BEFORE** `rate_limit_class`. Without D1 the recovery cannot tell a size
  ceiling from a clock — the exact defect D1 exists to close. **Do not launch this plan until 025A has
  landed.**
- ⛔ **MUST NOT run concurrently with PLAN-PR-025A.** They share `bot_registry.py`,
  `automatic-review/SKILL.md` and `coderabbit.md`.
- Surface is otherwise small and largely disjoint from the rest of the corpus: `.plan/marshal.json`,
  `manage-locks/` (script, SKILL, tests), and `coderabbit.md`.
- ⚠ **Re-derive the live-plan collision set before launch** — `corpus cross-check` reported none for
  the 025 family on 2026-08-29, but that result expires as soon as a live plan lands.

## Problem

The rate-window recovery sequence exists, is documented, and has **never executed for the bot it was
designed around**. Three separate causes stack:

1. **CodeRabbit is `optional`, and the recovery fires only for a bot in `required_bots`** — so the knob
   being off was never the reason it has not run.
2. **The retry budget is a hard-coded module constant** (`_RECOVERY_ATTEMPT_CAP = 2`), not a knob, not
   per-bot, not per-project — and it disagrees with the cloud lane, which settled on six.
3. **Nothing decorrelates waiters across lanes.** `merge_lock rate-window claim` serialises in-repo
   claimants, but a `doc/plans/` cloud run cannot see `merge_lock` and shares the same allowance.

Around that sits the measured evidence that the *required* reviewer has been contributing nothing while
an *optional* one carries the yield — recorded in D7 below and, at epic level, as an invariant now
standing at **n=5** (PRs #1340, #1349, #1356, #1359, #1361).

## Goal

The reviewer whose findings actually block bad merges is in the set the merge gate reads; a refusal it
publishes is retried on a budget an operator can change and that matches the other lane; and the wait
that retry performs is decorrelated for a reason this repository can state about itself.

## Deliverables

Three deliverables, comfortably inside the split guard.

### D7 — Make CodeRabbit a required reviewer, and arm the recovery that has never run

⭐⭐ **CORROBORATING EVIDENCE FOLDED IN 2026-08-25** — from inbox `plugin-doctor-detector-coverage-residue-001.md`
(three findings from PR #1343's review cycle, delegated to this epic by `truthful-signals`). D7's premise
now rests on measured yield, not on configuration order alone. ⚠ The measurements are the sending run's
own first-party observations on a live PR; re-derive before pricing, but the SHAPE is corroborated by two
independent PRs.

**PR #1343 — the required bot found nothing, twice; the optional bot found the merge blocker, twice:**

| Bot | Manifest role | Round 1 | Round 2 |
|---|---|---|---|
| `pr-agent` (`cuioss-review-bot`) | **required** | "No major issues detected" | "No major issues detected" |
| `coderabbit` | *optional* | 8 actionable, 6 real | **found the merge blocker** |
| `sourcery` | *optional* | structural refusal (size) | structural refusal (size) |

⭐ The merge candidate had already passed a whole-tree quality gate (37 rules, 0 issues), 21,957 module
tests, a clean whole-tree plugin-doctor run, and **seventeen rounds of dispatched self-review that
converged to two consecutive clean results** — and CodeRabbit still found a correctness defect in shipped
code (`_analyze_argument_naming.py` counting an undecided site as decided). Confirmed by
prediction-then-measurement: `blind_spots` 292 → 304 with `population_size` unchanged at 2792.

**Two conclusions that size this deliverable:**
1. **Self-review convergence is not a substitute for an independent reader.** Seventeen rounds of the same
   reviewer architecture converged clean on a defect a different reader found immediately.
2. **A plan that merges as soon as its own review converges will ship this class of defect.**

⭐ **Independently corroborated on PR #1338** (inbox `truthful-signals-035.md`, first-party via
`ci pr comments`): `coderabbitai` 10 comments, `sourcery-ai` 2, **`pr-agent` 0** — the required bot
contributed nothing while the two optional bots produced every one of the 6 filed findings. ⇒ **Three
PRs (#1338, #1343, and #1129-era corpus) now point the same way**, which is what moves D7 from a
configuration preference to a measured re-derivation.

⛔ **This does NOT settle the reviewer-plurality question in the other direction** — see the epic's
standing watch: on #1335 Sourcery returned `bug_risk` where BOTH other bots returned clean. The evidence
supports *promoting* CodeRabbit, not *dropping* anyone.

*Rationale, verified 2026-08-24 against the live `plan-marshall:automatic-review` step params:*

```
required_bots: pr-agent
optional_bots: "coderabbit,sourcery"
bot_lists_provenance: answered
review_rate_window_await: false
```

So the roster **is** answered and the quorum is **not** vacuous — `pr-agent` is today's sole required
bot. CodeRabbit is already registered, just **optional**. ⛔ **This is a PROMOTION, not an addition,**
and the distinction is the whole deliverable: the recovery sequence fires only for a bot in
`required_bots`, which is exactly why it has never executed for CodeRabbit — not because the knob is
off, but because CodeRabbit was never in the set the knob reads.

1. **Move** `coderabbit` from `optional_bots` to `required_bots` in `.plan/marshal.json`:
   `required_bots: "pr-agent,coderabbit"`, `optional_bots: "sourcery"`. ⛔ It must LEAVE
   `optional_bots` — a bot in both lists is a contradiction the classifier should never be handed.
2. `bot_lists_provenance` is already `answered`; leave it. ⛔ Do not re-stamp it — it records that a
   human answered the roster question, not when the roster last changed.
3. Set `review_rate_window_await: true`. Keep `review_rate_window_timeout_seconds: 3600` — the
   registry documents it as matching CodeRabbit's ~hourly reset.
4. ⚠ **State the consequence in the run report, do not bury it:** the project goes from **one**
   blocking reviewer to **two**, and the new one is rate-limited to roughly one review per hour. A
   rate-limited CodeRabbit will hold finalize open until recovery succeeds or escalates. That is the
   intended trade — it is what buys a second independent reviewer on the merge gate — but it must be
   a *stated* trade, and it is a real change to how often finalize blocks.
5. ⛔ Leave `sourcery` optional. It refuses **structurally** on diff size, a `Reopens? no` class no
   waiting fixes; promoting it would arm a recovery that cannot help it. Out of scope, recorded here
   so a later reader does not mistake the omission for an oversight.

*Done when:* `manage-config … step get --step-id plan-marshall:automatic-review` returns
`required_bots: "pr-agent,coderabbit"`, `optional_bots: "sourcery"`, `review_rate_window_await: true`;
no bot appears in both lists; and the two-blocking-reviewers consequence is stated in the report.

### D8 — Make the retry budget configurable, and raise it to six

*Rationale:* `_RECOVERY_ATTEMPT_CAP = 2` is a **hard-coded module constant** at
`manage-locks/scripts/merge_lock.py`:280 — not a knob, not per-bot, not per-project. Two attempts
against a one-hour window covers ~2 hours; the operator asked for six, which is the same budget
`.claude/skills/cloud-plan-lane/SKILL.md` § "A `Reopens? yes` refusal is RETRIED" already settled on
("**Budget: six attempts.** Six covers roughly a working day of hourly windows"). ⭐ **The two lanes
should not disagree on this number** — that divergence is the defect, and matching them is the fix.

1. Make the cap configurable, defaulting to **6**, and surface it in the `manage-locks` SKILL's
   documented return alongside `attempts` / `attempts_remaining`.
2. A test that **fails against the current constant** — assert the sixth attempt is admitted and the
   seventh returns `recovery_cap_exhausted`. ⛔ It must be SEEN to fail at `cap = 2` before the change.
3. ⛔ Do not change the escalation shape. `rate_window_exhausted` stays an explicit escalation, never
   a silent give-up.

*Done when:* the cap is read from configuration with default 6; the boundary test fails at 2 and
passes at 6; and no doc still states a cap of 2.

### D9 — Add jitter, and state precisely what it is for here

⛔ **Do not port the lane's rationale unexamined — it does not transfer whole.** The lane needs jitter
because parallel cloud plans contend on one allowance with **no shared lock**. Plan-marshall already
has one: `merge_lock rate-window claim` *serialises* claimants, so the in-repo thundering herd the
lane describes is already prevented by construction. Jitter's remaining job here is narrower and must
be written down as such:

1. **Cross-lane contention** — a `doc/plans/` cloud run cannot see `merge_lock` and shares the same
   CodeRabbit allowance. Nothing serialises those two lanes against each other.
2. **Post-release decorrelation** — when a claim is released, the next waiter proceeds immediately; a
   small random offset keeps a queue of waiters from re-synchronising on one slot.

Add a bounded random offset (the lane uses 5–20 minutes) to the rate-window wait, sourced so it is
**testable** — injectable, not a bare `random()` call at the wait site, or the behaviour cannot be
asserted. Record in the registry doc which of the two purposes above it serves.

*Done when:* the wait applies a bounded jitter; a test pins its range deterministically through the
injection seam; and `coderabbit.md` § rate-window states jitter's purpose without repeating the lane's
inapplicable shared-allowance rationale.

### D10 — The recovery that actually worked: close and reopen on the same branch and HEAD

⭐ **Folded from `truthful-signals-043.md` item 1** (2026-09-04, relayed from TokenSheriff PR #688/#689 —
⛔ a foreign-repo LEAD, NOT corroborated in this checkout).

CodeRabbit posted *"Review limit reached — next included review available in 22 minutes"* on PR #688 after
enumerating all 17 files and the commit range: it **saw** the PR and simply could not spend a review.
`automatic-review` resolved `refused_awaitable` / cause `quota` and returned `loop_back`.

⛔ **That loop-back could never have worked, and the reason is structural: CodeRabbit does not auto-review
after its window resets and does not re-review a PR it has already refused.** The refusal comment stays on
the PR, so every re-fire re-reads the same stale refusal and re-classifies the bot as refused. **The refusal
is time-based; the loop-back mechanism is event-based. They do not meet.**

⭐ **The recovery this spec does not currently name, and which was observed to work:** close the PR
**without merging** and open a replacement PR on the **same branch and the same HEAD**, body copied
verbatim. The fresh PR claims the now-open reset window and gets a real review; the closed PR keeps its
review history readable for audit. `references.pr_number` was updated 688 → 689.

⚠ **There is no skip path here.** With `pre_merge_comment_barrier=fail_into_loopback` the barrier re-derives
participation independently and refuses until the bot is proven, so recovering the review is **required for
the merge**, not merely preferred. `review_rate_window_await` was `false` for that plan, so no automatic
recovery was armed.

⛔⛔ **CORRECTION 2026-09-04 — `truthful-signals-045.md` §2.1 CONTRADICTS the mechanism this deliverable
originally implied, and the correction is load-bearing.** D10 was folded in earlier the same day reading
as though *reopening* buys back review capacity. It does not:

> **PR-level workarounds do not touch the quota** — close/reopen, a new PR, a force-push, a new SHA: none
> buys back capacity. **The limit is account-scoped.**

⭐ **The two reports reconcile, and the reconciliation is the actual rule.** The observed close-and-reopen
succeeded because **the window had already elapsed** (the successful `@coderabbitai review` in that
account came 10+ hours in), not because a fresh PR reset anything. So the reopen is a way to **re-deliver
a request the bot dropped** — quota clearing does **not** re-deliver a refused review — and it is worth
nothing before the window is up.

⛔⛔ **The corrected posture, verbatim from the source, and it inverts the original advice:**

> **While the bot is actively refusing for quota reasons, do NOT re-trigger.** Re-trigger **exactly once,
> AFTER the window has elapsed.**

A re-trigger *during* the window **RESETS it rather than shrinking it** (advertised wait observed going
50 → 59 minutes) and spends quota. ⚠ A bot's own reset ETA is an **estimate, not a contract** — observed
errors ~2.4×, then **~15×** (advertised 24 minutes; nothing after 10+ hours).

⛔⛔⛔ **This rule was written, then violated ~6 hours later in the same epic**: a loop posted
`@coderabbitai review` every ~2 minutes for ~55 minutes — **~27 spam comments on a public PR**, ~1.5h wall
clock — and **exhausted the bot's separate CHAT-MESSAGE quota on top of the review quota, removing the
recovery path entirely.** That plan shipped on a `barrier-ask-override` with one required bot instead of
two. ⇒ *"A lesson filed, re-derived, corrected, and then violated within hours is not functioning as a
control."* **This is the corpus's strongest argument that a prose rule needs a mechanical backstop, and it
is why D10 must ship as a GUARD, not as guidance.**

⚠ **Asymmetry observed in the same run, recorded because it shows the posture was known:** Sourcery's
identical budget notice was filed as a `pr-comment` finding and resolved `accepted` — one bot got a
wait-or-proceed decision, the other got a retry loop.

*Done when:* the refusal-recovery path can select close-and-reopen for a bot whose refusal is time-based and
whose re-review is not event-triggerable, and the choice between waiting and reopening is derived from the
bot registry's rate class rather than assumed. **Cross-reference:** `PLAN-PR-043` D6 limb A owns the
interval/ceiling surface this recovery falls back from.


## Expected Surface

- `.plan/marshal.json` — D7. ⭐ **This file is git-TRACKED** (`git ls-files --error-unmatch` exits 0
  and `git check-ignore` returns nothing), so the config change is repository source and reaches the
  PR diff like any other edit. It is NOT machine-local state.
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — D8
  (`_RECOVERY_ATTEMPT_CAP` at `:280`).
- `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — D8 (the `attempt_cap` surface).
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — D9 (the
  registry doc's rate-window section at `:123-125`).
- `test/plan-marshall/manage-locks/` — D8, D9 (the cap and jitter tests).
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md` — D10: the close-without-merging + reopen-on-same-HEAD recovery.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — D10: selecting recovery by the bot's rate class rather than by assumption.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — D10: the rate class the selection reads.
- `test/plan-marshall/automatic-review/` — D10.

## Claim Labels

- OBSERVED: the recovery sequence fires only for a bot in `required_bots`, and CodeRabbit is currently
  `optional` — so the recovery has never executed for it. Confirm/refute at the live step params via
  `manage-config … step get --step-id plan-marshall:automatic-review` (D7 quotes the 2026-08-24 read:
  `required_bots: pr-agent`, `optional_bots: "coderabbit,sourcery"`, `review_rate_window_await: false`).
  ⛔ **Re-read it at the moment of the run** — a config value is the most easily-stale claim in this spec.
  - verdict: corroborated | checked_at: 7845a4b9a383a4d58c9314bfce89970ced67c4f7 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 7845a4b9a, method: whole-spec-file intersection against git diff --name-only 26645688b..HEAD (197 paths). Fail-closed by design - the scan is over the WHOLE spec file, not a parsed Expected Surface section, because two section parsers disagreed on this corpus. Basename matching stays DISCARDED as non-discriminating. NO running-row exclusion applied this pass: the queue has no running plan. Intersection: 2 hit(s), including coderabbit.md; marshal.json. Surface MOVED in this window - NOT re-audited line by line this pass; line references will have drifted, re-derive at outline. No finding in this window contradicts the premise.
- OBSERVED: `_RECOVERY_ATTEMPT_CAP = 2` is a hard-coded module constant. Confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § `_RECOVERY_ATTEMPT_CAP`
  (cited at `:280` when authored — **re-derive the line, it will have drifted**).
- OBSERVED: the cloud lane settled on a six-attempt budget. Confirm/refute at
  `.claude/skills/cloud-plan-lane/SKILL.md` § "A `Reopens? yes` refusal is RETRIED".
- OBSERVED: `merge_lock rate-window claim` already serialises in-repo claimants, so the lane's
  shared-allowance thundering-herd rationale does NOT transfer whole. Confirm/refute at the claim
  implementation in `merge_lock.py`.
- OBSERVED — **measured, and it is the reason D7 is a promotion rather than a preference**: across PRs
  #1338, #1343 and now #1361, the REQUIRED bot contributed nothing while an OPTIONAL bot carried the
  yield. Confirm/refute at the epic's Watch § "the external reviewer set contributed nothing", whose
  #1361 row was re-derived first-party on 2026-08-29.
  ⛔ **This supports PROMOTING CodeRabbit, never DROPPING anyone** — the #1335 counter-instance
  (Sourcery alone returned `bug_risk`) still stands.
- HYPOTHESIS: that raising the cap from 2 to 6 changes no currently-asserted outcome other than the
  boundary itself — confirm/refute by running the existing `manage-locks` suite against the configurable
  cap at its default (verify-at-outline). If an existing case flips, report it rather than adjusting it.

## Verification

1. **Build gate.** This plan changes Python, so the full verify runs and its result is reported. Do not
   report a deliverable done on an unrun suite.
2. **Targeted suite.** Run and name `test/plan-marshall/manage-locks/`.
3. **Fail-first, and it is D8's explicit obligation.** The boundary test MUST be **seen to fail** at
   `cap = 2` before the change — a test that passes both ways proves nothing about the defect it names.
4. **State the trade in the run report.** D7 takes the project from ONE blocking reviewer to TWO, the
   second rate-limited to roughly one review per hour. That is the intended purchase, but it is a real
   change to how often finalize blocks and it must be stated, not buried.
5. **Collateral check.** Confirm the diff touches no file outside § Expected Surface — in particular no
   change to the refusal *detection* surface, which PLAN-PR-025A owns.

## Notes

⛔ **The orchestrator ledger under `.plan/` is git-ignored and does not exist in a fresh clone.** There
is no plan spec, no status file, and no landing record to open. Do not go looking for one, and do not
report a run blocked on its absence.

⚠ `.plan/marshal.json` is git-TRACKED (D7's own surface note verifies this), so the config change is
repository source and reaches the PR diff like any other edit. It is NOT machine-local state.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-025B-arm-the-refusal-recovery-that-has-never-run.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message.
