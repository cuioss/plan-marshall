# PLAN-PR-008: The pre-merge review barrier deadlocks when a required bot refuses, and the fix for the last defect removed the only escape

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — re-issued from `truthful-signals` PLAN-119

Released to this epic on 2026-07-30 (row `transferred` there, verified against its live queue). Under
this epic's `PLAN-PR-NNN` rule **no id travels**: this is a re-issue, not a rename. Carried whole —
the released spec was already within the split guard.

⭐ **Carries an operator-owed decision (D3). Staging this plan does NOT decide it.**

## Objective

The Pre-Merge Review-Completeness Barrier is fail-closed on required-bot participation. When a required
bot is **refusing for reasons outside the repo's control** (rate limit, quota), the barrier can never
pass, `fail_into_loopback` loops the plan back, the loop-back produces no new commit, the bot refuses
again — and the plan cannot merge at all. There is no sanctioned way to record "this bot is degraded,
proceed with a documented gap."

## The defect, and why it is on-theme

`branch-cleanup.md:579-581` states the barrier's design plainly, and **the design is correct**:

- Predicate 1 (unhandled comments) cannot see an **absence** — a bot that never reviewed publishes
  nothing and reads as clean.
- Predicate 2 re-derives participation from the provider, **deliberately not trusting** the
  `automatic-review` step record, because the force-done escape hatch produces a record
  *byte-identical* to an earned pass.

⭐ **The previous fix closed a false-green hole and opened a permanent-red one.** Making force-done
non-authorizing was right — it stopped a forced record buying a merge. But force-done was **the only
escape**, and nothing replaced it. The barrier now asks a question that an external service's
availability answers, and offers the operator no way to answer it.

⛔ **This is the recurring archetype: a fix for a defect that reproduces the defect's family.**
Recurrence n≥6.

## ✅ UNBLOCKED 2026-08-08 — the PLAN-PR-007 dependency is DISCHARGED

This plan was held on *"BLOCKED until PR-007 lands — a false `absent` and a true `absent` are
indistinguishable at the barrier until then."* **PR-007 landed as `#1118`** (`fddc4ec8b`, merged;
orchestrator-verified against PR state). The two are now distinguishable: the taxonomy carries seven
closed members and a required bot resolving to `participated_stale` or `not_triggered` blocks exactly as
`absent` does, each with a **distinct remedy**. ⇒ **D1's terminal-state derivation can finally be
performed against a taxonomy that separates the states it must classify.**

⛔ **But `#1118` also EDITED THIS PLAN'S PRIMARY SURFACE.** `branch-cleanup.md` gained **+64 lines** and
`test_pre_merge_barrier.py` **+145** in that commit. ⇒ **Every line reference and every quoted predicate
in this spec — including the `:579-581` design citation — must be RE-GROUND against merged main before
scoping.** ⚠ Check specifically whether `#1118` already altered the barrier's behaviour on a refusing
bot; if any part of D1's population is already handled there, scope only the remainder and say what
moved.

⭐ **D1's population gains its members from the shipped taxonomy rather than from this spec's list.**
The spec enumerated states by hand and warned the list was incomplete; the contract now enumerates them
normatively. **Derive from the seven-member taxonomy — that is the population — and classify each member
as passable-by-the-plan's-own-action or not.** A hand-list is now strictly worse than the source.

## ⛔⛔ RE-SCOPED 2026-08-09 — THIS PLAN'S PREMISE IS REFUTED. D2 AND D3 ARE BOTH SHIPPED. READ BEFORE ANYTHING ELSE.

Orchestrator ground-truth pass against merged main, first-party:

| Deliverable | Verdict | Evidence |
|---|---|---|
| **D2** distinguish refused-from-unproven | ✅ **SHIPPED** | `review_completeness.py:237` — `bot_registry.rate_limit_class(bot) == 'awaitable_window'`, splitting `STATE_REFUSED_AWAITABLE` / `STATE_REFUSED_HARD` |
| **D3** sanctioned recorded coverage-gap acceptance | ✅ **SHIPPED AND EXERCISED** | `manage-status/scripts/_cmd_merge_authorization.py` — `grant`/`check`, HEAD-bound, `gap_class`, fail-closed (`:157` *"matches no class — fail-closed, never a wildcard"*). **Used on #1130**: `barrier-ask-override` granted at HEAD `c30d5a656`, `gap_class: participated_but_empty` |

⇒ **The Objective above is now FALSE where it says "There is no sanctioned way to record 'this bot is
degraded, proceed with a documented gap.'"** There is; it is explicit, recorded, HEAD-bound,
gap-class-bound, and it has been used. ⛔ **Do not implement D2 or D3.** Do not re-litigate the
deadlock framing either — a refusing bot no longer traps a plan, because the override is the exit.

### What genuinely survives, and it is one thing

**D1's terminal-state derivation, and specifically the member that is provably ABSENT.** Ground-truth
check: `review_completeness.py` (587 lines) contains **no** `diff_size` / `size_cap` / `150000` /
`too_large` / `size_limit` token. The taxonomy models *temporal* refusal only.

⭐⭐ **The sharpening, from `code-intelligence-substrate-010` (first-party on PR #1126, third sighting
on #1127) — THE REMEDY SETS ARE DISJOINT:**

> A rate limit is a **temporal** refusal — the same request succeeds later. A diff-size cap is a
> **structural** one — the same request never succeeds. Any handling that offers "wait / accept the
> gap" as the option pair is **offering a non-option on the size branch.**

The step config carries `review_rate_window_await` and `review_rate_window_timeout_seconds` — i.e.
**the machinery it has is a rate-window one**. A size refusal is therefore either silently bucketed
with the rate refusal or reported as unexplained non-participation. Sourcery's cap is 150,000
characters, so the exclusion recurs **by size, not by chance**: every plan over that threshold gets no
Sourcery review, predictably and forever.

⇒ **The re-scoped plan is: give structural refusal its own taxonomy member with its own remedy set
(split / accept / disable-for-this-PR), record the cap value in the finding so the gap is auditable
against the actual diff size, and NEVER offer an await on a structural refusal.** ⭐ The cap is
**knowable before the barrier runs** — a diff size is measurable at PR creation — so this is a
predictable exclusion the epic can disclose in advance rather than discover at the gate.

⚠ **Retitle at outline.** The slug `review-barrier-deadlocks-on-a-refusing-bot` no longer describes
the work; the deadlock is escapable. The subject is now *the taxonomy has no structural-refusal
member*. ⛔ The plan id stays `PLAN-PR-008` — ids are stable — but the outline should state the real
subject in its first line so a reader is not misled by the slug.

⚠ **Split-guard note:** with D2 and D3 dropped this plan is now SMALL. Consider whether it should be
folded into PLAN-PR-021 (which owns the barrier's disclosure surface) rather than run alone — that is
an emit-time decision, recorded here so it is not re-derived.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the barrier's terminal-state population.** Enumerate every
   state in which the barrier can end and classify each as *passable by the plan's own action* or
   *not*. ⛔ **A state a plan cannot exit by acting is a deadlock, and deadlocks are the finding.**
   Include at minimum: bot refused (rate limit / quota), **bot refused permanently (diff-size limit —
   waiting never clears it)**, bot absent entirely, **bot never triggered (no workflow run created at
   all — see PLAN-PR-007's `not_triggered` member)**, bot posted a canned no-op, bot posted a
   substantive review. **The rate-limit case is a SAMPLE — derive the rest.** ⛔ Two members of this
   list were added after the spec was written, both from a single consumer-repo PR; treat the list as
   still incomplete and derive rather than confirm.
2. ⛔ **D2 — PRESUMPTIVELY ALREADY SHIPPED. Re-scope or drop at outline BEFORE designing it** (see the
   same-day correction in Claim Labels: `review_rate_window_await` already classifies
   `awaitable_window` / `hard_quota` / `unknown`). What follows is the ORIGINAL text, retained so the
   re-scope can see what was intended — **do not implement it as written.**

   **D2 — distinguish "unproven" from "refused".** A required bot that **published a refusal** is a
   materially different state from one that was silent, and the two demand opposite operator responses.
   ⚠ **The refusal is only visible in the comment BODY** — a detector reading check state or row count
   cannot see it. This is the same wrong-observable family as PLAN-PR-005 / PLAN-PR-006;
   ⛔ **coordinate, do not duplicate the detector.**
3. **D3 — a sanctioned, recorded coverage-gap acceptance AT THE BARRIER.** The operator must be able to
   authorize a merge with a known review gap, and the authorization must be:
   - **explicit** — an operator decision, never a leaf's own judgement (this is exactly what made
     force-done wrong);
   - **recorded** — the audit trail states *merged with a known gap, which bot, why, authorized by the
     operator*, so it is never mistaken for an earned pass;
   - **distinguishable** — the resulting record MUST NOT be byte-identical to an earned pass. ⛔ That
     byte-identity is the precise defect the previous fix was written to remove; **do not reintroduce
     it in a new location.**
4. **D4 — the barrier's failure message must name the exit.** A `fail_into_loopback` that a loop-back
   cannot fix is a misleading instruction: it tells the operator to do something that cannot work. When
   the barrier detects a not-passable-by-action state, it must say so and name the available exits,
   rather than looping.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A required bot publishing a rate-limit refusal is
   classified `refused`, not `unproven`. (b) A loop-back that produces no new commit does not re-enter
   the same barrier expecting a different answer. (c) An operator-authorized coverage-gap merge produces
   a record **distinguishable** from an earned pass. (d) The terminal-state population is derived,
   non-empty, and contains every known member.

## ⭐⭐ THE FIRST VALUE-SIDE DATUM ON THE OVERRIDE QUESTION — from `#1118`, 2026-08-08

**D3 has been reasoned about entirely from the cost side until now.** `#1118` supplies the other side,
and it is the strongest single argument in the spec:

**The pre-merge barrier blocked `#1118` once — on that plan's OWN newly-added `participated_stale`
member, firing against its own PR.** The plan chose the **loop-back over an override**, and that choice
is what produced CodeRabbit's review: **8 actionable comments, including a Major where the plan had
violated its own fail-closed thesis at a call site it had just added.**

⛔ **Record the counterfactual precisely, because it is what D3 is deciding.** An override *was*
available and *would have been defensible* — the bots were refusing for reasons outside the repo's
control, which is exactly the deadlock this plan exists to sanction an exit from. **Taking it would have
merged a Major defect in the plan's own new code behind a green barrier.**

⇒ **The honest framing for D3's operator escalation must change.** It is no longer *"pay up to an hour
of latency to recover findings that are demonstrably real but never blocking"*. It is now:

> **At the one observed opportunity to use an override, taking it would have shipped a Major.**

⚠ **Do NOT over-read this into "never grant an override."** n=1, and the deadlock D3 addresses is real —
a barrier with no exit strands every landing behind a third party's quota. ⭐ **What the datum actually
constrains is the DESIGN, not the answer**: it is evidence that the exit must be *expensive to take and
recorded as a coverage gap*, never a convenience path — which is precisely D3's "explicit / recorded /
distinguishable" triad, now with a measured reason for each.

⛔ **And note which way the same run cuts on the OTHER side**: `#1118`'s last two commits were **never
bot-reviewed at all** (CodeRabbit refuses already-reviewed ranges, Sourcery over its size limit,
pr-agent contentless) and **the barrier passed them on `participated_but_empty`**. So on the same PR the
barrier both **blocked correctly once** and **passed an unreviewed range once**. ⇒ **D1's terminal-state
derivation must cover both directions**; a plan that only adds an exit makes the second failure worse.

## ⛔ D3 now owes the operator TWO decisions, and they are answered TOGETHER

**Operator decision, 2026-07-30 (`AskUserQuestion`, recorded as an interaction):** the
`review_rate_window_await` arming question is **deferred to this plan's outline** and folded into D3,
rather than answered as a standalone config change. The operator chose this over arming it immediately
(default or shortened budget) and over accepting the gap outright — so **D3's escalation must put both
questions in one prompt**, with the terminal-state derivation from D1 in hand.

⭐ **BOTH decisions are narrower than they look, because of the gating config — verify this first.**
`.plan/marshal.json` declares `required_bots: "pr-agent"` and `optional_bots: "coderabbit,sourcery"`
(`bot_lists_provenance: "answered"`). Operator rationale 2026-07-30: for this repo CodeRabbit is
optional; it matters more on API-Sheriff, which is production code. Two consequences:

- ⛔ **The deadlock D3 addresses is about a REQUIRED bot only.** `optional_bots` is already the sanctioned
  way to accept an optional bot's silence — `branch-cleanup.md` states it outright — so a CodeRabbit or
  Sourcery refusal *cannot* deadlock this barrier here. **D1 must not enumerate optional-bot refusal as a
  deadlock state**; doing so would inflate the population with states the config already resolves.
- ⚠ **The arming trade in THIS repo buys an OPTIONAL bot's review.** That is a materially weaker case for
  arming than the raw #1067 story suggests — up to 3600 s of finalize latency to recover a review that
  could never have blocked the merge anyway.
- ⛔ **But do NOT collapse "optional" into "low value."** Gating ≠ value: on `#1067` the optional bot
  found 5 genuine defects the required bot missed. The honest framing for the operator is *"pay up to an
  hour to recover findings that are demonstrably real but never blocking"* — not *"pay an hour for a bot
  that does not matter."*
- ⚠ **Gating is PER-REPO.** If this question is ever put for another repo, read that repo's
  `required_bots` / `optional_bots` first; do not carry plan-marshall's answer across.

**Decision 2 — arm `review_rate_window_await`, or accept that awaitable refusals are never recovered?**

- Current state: **`false`** at `.plan/marshal.json:113`, which is also the shipped default.
- ⭐ **ONE measured instance, not two** — `#1067`: an awaitable window reopened only because the merge
  mutex happened to block, and the review it then gave found **5 genuine defects**, one of them the plan
  reproducing its own target defect.
- ⛔⛔ **`#1066` was RECORDED here as a second instance and is REFUTED — orchestrator-verified
  2026-07-30, correcting this epic's own earlier entry.** The claim (from inbox `truthful-signals-005`,
  repeated in `-008`) was *"one-bot coverage; CodeRabbit's awaitable refusal was never waited out."*
  **False.** `ci pr comments --pr-number 1066` returns **8 comments authored by `coderabbitai`**,
  including a **Major** finding, with the 3 inline review comments posted at **11:58:43Z** — and the PR
  merged at **12:06:46Z**. ⇒ **CodeRabbit DID review, 8 minutes before the merge.** The coverage was not
  one-bot-deep and the awaitable window is not implicated.
  ⚠ **Consequence for the deferred arming decision (D3, decision 2): the instance count is ONE, not
  two.** The standing note that "a third measured instance is grounds to re-surface early" is re-based
  accordingly — ⛔ **do not count `#1066` toward it.**
  ⭐ **But the run was NOT clean, and the real defect is worse** — see PLAN-PR-014 and PLAN-PR-013, which
  now own it: the review landed and the PR merged **8 minutes later with all 8 findings unresolved**.
- The trade the operator must price: arming costs up to `review_rate_window_timeout_seconds` (default
  **3600**, matched to CodeRabbit's ~hourly reset) on any finalize that hits an awaitable refusal.
  ⚠ **A shortened budget is not obviously cheaper** — if the cap expires before the window reopens, the
  wait is paid and nothing is recovered.
- ⛔ **Whichever way it goes, this is an ACTIVATION decision, never a build.** Do not design a second
  recovery path; the shipped one is described in the Claim Labels correction.

⚠ **Until this plan runs, the gap is LIVE and accepted knowingly** — the operator was told this plan sits
9th in the queue when they chose to defer. If the queue moves, that acceptance does not expire, but a
third measured instance would be grounds to re-surface it early.

## ⛔ The operator decision D3 still owes (decision 1)

**D3's design needs the operator's answer on what an acceptable gap is** — this is a standing
accepted-coverage-gap question, recorded as owed and NOT resolved by staging. Surface it at outline via
`AskUserQuestion` before designing D3; do not infer a policy.

## ⛔⛔ ABSORBED 2026-08-08 (inbox drain) — the empty-quorum case, now observed TWICE on two different PRs

**This is the epic's central finding from the #1118 run, and D1 must derive BOTH directions.** A plan
that only adds an exit for a refusing bot makes this half strictly worse.

### Instance 1 — PR #1118, first-party (`absent-names-two-states-with-opposite-remedies-004`)

Source: `[VERIFY]` WARNING, `plan-marshall:phase-6-finalize`, work log `2026-08-08T19:53:48Z`, hash
`ffaf11`, HEAD `a5749b0d2`. Recorded verbatim by the run:

> Pre-merge barrier PASSES at HEAD a5749b0d2: 0 pending pr-comment findings,
> participation_complete=true. The quorum rests on pr-agent=participated_but_empty (a contentless 'no
> major issues' guide). coderabbit=refused_awaitable, sourcery=refused_hard. Commits 851e5396b and
> a5749b0d2 carry NO bot review content. Participation proven, review quality NOT.

⭐⭐ **The two unreviewed commits are precisely the commits that implement the review's own fixes.**
CodeRabbit found 8 actionable comments including a Major; `851e5396b` is the 9-task response and
`a5749b0d2` the 5-task follow-up. The apparatus produced a strong review of the code as it was
BEFORE the review, and no review at all of the code as it merged.

⚠ **None of the three refusal reasons is a bug** — each bot declined for an individually reasonable
reason (already-reviewed range; diff over the 150000-char limit; contentless guide).

### Instance 2 — PR #1122, routed from `truthful-signals` (`truthful-signals-024`)

`automatic-review` recorded **"quorum met (participation only)"** with CodeRabbit **rate-limited and
never reviewing ANY head**, and both pr-agent and sourcery `participated_but_empty`. With
`required_bots='pr-agent'` alone, **the quorum was satisfied by a bot that filed nothing**, while the
bot that historically produces the actionable findings never saw the diff.
⭐ `review-retrospective` independently returned **`verdict unmeasurable`** — two mechanisms agreed
there was nothing there and the merge gate still read green.
⛔ **LEAD, NOT FACT** — the sender did not run `ci pr comments --pr-number 1122`, so the per-bot
states are that step's report, not an independent measurement. Re-derive at outline.
⚠ The operator accepted #1122's thinness knowingly; the question is whether the *mechanism* would
have disclosed it had nobody been watching.

### The generalisable shape

`participation_complete` is a **liveness** predicate — did every required bot show up. It is not, and
never was, a **coverage** predicate — did every required bot look at what is about to merge. On a
normal run the two coincide, which is why the gap stays invisible until a run separates them.

`participated_but_empty` is by design accounted-for and never blocking — correctly so, since a
genuine clean review is indistinguishable from an empty one at the participation layer. **But when it
is the ONLY member carrying the quorum, "accounted for" has silently become "reviewed".**

⚠ Note the interaction with #1118's own deliverable: `participated_stale` exists to catch a review
about a superseded HEAD. It fired earlier in that same run and worked. It **cannot** catch the case
where the bot never produced content about ANY HEAD.
⭐ Standing context: **a required set of exactly one has no redundancy.** #1122 is the clearest
instance yet.

### Candidate remedies (none applied)

- Distinguish `participation_complete` from a `review_coverage` signal that asks whether the merging
  HEAD received at least one **content-bearing** review, and decide deliberately which one gates.
- Treat *"the quorum rests on a single `participated_but_empty`"* as a state worth **naming** rather
  than one that silently passes.
- The Sourcery 150000-char refusal is a size limit the epic can **predict** — a diff over the limit is
  knowable before the barrier runs.

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-29, `ci pr comments --pr-number 1057`): `sourcery-ai` — "you
  have reached your weekly rate limit of 500000 diff characters"; `coderabbitai` — "you've reached your
  PR review limit, so we couldn't start this review"; `cuioss-review-bot` (pr-agent) — an informational
  Guide with zero actionable content.
- ⚠ OBSERVED: **both refusals were stated ONLY in the comment bodies; the check states showed nothing.**
  A detector reading check state concludes "no problem"; one reading participation concludes "unproven";
  **neither concludes "the service refused, and that is a different thing."**
- OBSERVED (orchestrator-verified): `pre_merge_comment_barrier` default `fail_into_loopback`;
  `barrier_mode` valid values `fail_into_loopback` / `ask`; the `branch-cleanup.md:579-581` design
  rationale.
- OBSERVED (operator paste): with `fail_into_loopback`, a force-done of `automatic-review` does not buy
  the merge — the barrier re-checks, still finds the bot unproven, and loops back.
- HYPOTHESIS: the loop-back is non-terminating when no new commit is produced — confirm/refute at D1.
  **Confirm/refute artifact**: the loop-back re-entry condition in `phase-6-finalize/SKILL.md` and the
  barrier's re-check in `branch-cleanup.md`.
- HYPOTHESIS: `ask` mode already provides a partial exit — confirm/refute at D1 **before designing D3**,
  since an existing partial exit changes D3's shape. ⛔ **Do not assume `ask` is absent.**
- ⭐ OBSERVED 2026-07-30 (`cuioss/API-Sheriff#133`, orchestrator-verified via
  `pulls/133/reviews`): **a refusal shape that is PERMANENT, not transient** — `sourcery-ai[bot]`
  submitted a `COMMENTED` review reading *"your pull request is larger than the review limit of 150000
  diff characters"*. This is a **diff-size** limit, not a rate/quota limit.
  ⛔ **This breaks the assumption D1's sample encodes.** Every refusal in the 2026-07-29 evidence was
  time-recoverable — a rate limit expires, a quota resets, so "wait and re-trigger" is a real exit. A
  size refusal **never expires**: re-triggering the identical diff returns the identical refusal
  forever. So D1's terminal-state classification needs a second axis it does not currently have —
  not just *passable by the plan's own action* vs not, but **recoverable by WAITING vs recoverable only
  by CHANGING THE DIFF vs not recoverable at all**. A barrier that says "re-trigger" to a size refusal
  emits a D4 misleading instruction of exactly the kind D4 exists to remove.
  ⚠ **Consequence for D3**: the only diff-side exit is splitting the PR, which is not a barrier action
  at all — it is a re-planning decision. This strengthens the case that D3's operator-authorized
  coverage-gap acceptance is *required* rather than merely convenient, because for this state there is
  no engineering exit the barrier can offer.
  ⚠ **Do not read this as reopening the retired Sourcery watch.** That watch was retired on the ground
  that *rate limiting* is known and expected (operator ruling, and it stands). A size-limit refusal is a
  **different shape** and was never covered by that retirement — it is in scope here, as a refusal the
  barrier must classify, not as a Sourcery defect to fix.
- ⭐⭐ **OBSERVED 2026-07-30 (`#1067`) — the single strongest piece of evidence for the D2 split, and it
  came from a lucky accident.** CodeRabbit's rate-limit window **reopened while the plan was blocked on
  the merge mutex**, and the review it then produced found **5 genuine defects** — one of which
  (`3e04a8`) was the plan reproducing *its own target defect*. Operator's assessment: the loop-back was
  the most valuable part of that finalize.
  ⛔ **What this proves is the load-bearing distinction:** a rate-limit refusal is a **DEFERRED review
  carrying real content**, not an absent one. Had the mutex not blocked, that PR would have merged with
  all five defects and every signal green.
  ⚠ **This does NOT reopen the retired Sourcery/CodeRabbit rate-limit watch, and must not be recorded as
  doing so.** The operator's ruling — rate limiting is expected and is not a bot malfunction — stands
  unchanged.

- ⛔⛔ **CORRECTION, SAME DAY — the orchestrator's first reading of the above was WRONG, and this spec had
  already warned against the exact error.** The first version of this entry asserted *"there is no
  mechanism that waits for a reopening window."* **That is FALSE.** Verified against source after
  `truthful-signals-005` named the knob:

  **A full recovery mechanism is SHIPPED and is far more than a wait** —
  `automatic-review`'s opt-in `review_rate_window_await` (+ `review_rate_window_timeout_seconds`,
  default **3600**, chosen to match CodeRabbit's ~hourly reset). For an `awaitable_window` bot it
  **claims the bot's rate window** via `merge_lock rate-window claim`, polls that claim's own expiry as a
  bounded paced wait, then **GENERATES the trigger event** (rebase onto base and push; the registry
  `trigger_comment` only as a fallback, and only when main is unchanged and the window has elapsed).

  ⭐ **And D2's distinction is ALREADY IMPLEMENTED.** The shipped code discriminates
  `awaitable_window` / `hard_quota` / `unknown` and escalates a non-awaitable limit immediately via
  `escalate_ask{reason: rate_window_not_awaitable}`, with `rate_window_exhausted` and
  `rate_window_timeout` for the other two exits. ⛔ **D2 as written would REBUILD a shipped mechanism.**

  **The real finding is an ACTIVATION question, not a missing capability**: `.plan/marshal.json:113`
  sets `"review_rate_window_await": false` in this very repo, and the default is `false`. So the #1067
  recovery was luck **because the recovery is switched off**, not because none exists. Per
  `review-practice.md` § 3's third answer shape, ⛔ **do NOT compensate for a switched-off check by
  building a second one.**

  ⚠ **This spec's own Claim Labels already said "⛔ Do not assume `ask` is absent" — the identical trap,
  one mechanism over, and the orchestrator walked into it anyway.** An asserted absence is the
  higher-risk half of the verify-first contract, and it was asserted here without a `grep`.

  ⇒ **D1 and D2 MUST be re-scoped at outline before any design work.** D1's terminal-state derivation now
  starts from a shipped classifier rather than a blank sheet; D2 is presumptively **already satisfied**
  and must be re-aimed at whatever the shipped split does *not* cover (the diff-size refusal below is the
  leading candidate — verify whether it classifies as `hard_quota` or falls to `unknown`) or dropped.
  D3 and D4 are unaffected: an operator-authorized coverage-gap exit and a non-misleading failure message
  are owed regardless of whether the await knob is armed.
- ⭐ **OBSERVED 2026-07-30 (`#1067`, `pulls/1067/reviews`) — SECOND sighting of the permanent diff-size
  refusal**, verbatim the same shape as `API-Sheriff#133`: `sourcery-ai[bot]`, `COMMENTED` at 11:19:29Z,
  *"your pull request is larger than the review limit of 150000 diff characters"*. Two sightings in one
  day, both on large PRs (`#1067`: 25 files / 12 commits). ⇒ **It is not a one-off**, and it correlates
  with PR size rather than with time — reinforcing that the only diff-side exit is splitting the PR,
  which is not a barrier action. D3's operator-authorized coverage-gap exit is required for this state.
- ⭐⭐ **OBSERVED 2026-07-30 — the refusal taxonomy conflates a CAPACITY condition with a CAPABILITY one,
  and this is D1's sharpest input.** Sourcery emits **two different refusals**, and both are recorded as
  `hard_quota`:

  | PR | Verbatim message | True cause | Does waiting help? |
  |---|---|---|---|
  | `#1063` | *"you have reached your **weekly rate limit of 500000 diff characters**"* | **quota** — capacity | ✅ yes, it resets |
  | `#1067`, `API-Sheriff#133` | *"your pull request is **larger than the review limit of 150000 diff characters**"* | **size cap** — capability | ⛔ **never**, for as long as the diff exceeds the cap |

  ⛔ **The two have OPPOSITE remediations**, and `hard_quota` as a catch-all for "refused and not
  awaitable" destroys the only bit the caller needs: **can retrying this same input ever succeed?**
  ⇒ D1 must classify on that axis. Proposed by the sender and worth adopting: a distinct
  `refused_input_too_large` cause; `review_rate_window_await` consults the cause and **refuses a
  guaranteed-futile wait at ARM time** rather than discovering it at timeout; and the cause is carried
  **verbatim** into `review-retrospective.md` rather than re-narrated.
  **General rule for D1**: when an external service declines, the classifier MUST preserve whether
  retrying the same input can ever succeed.

- ⛔ **CORRECTION to the forwarding epic, verified first-party and returned to them.** `cis-004` § 3
  asserts *"We had Sourcery down as hard-quota refusing from the #1063 landing too. It is a size cap"* —
  **that is FALSE.** `#1063`'s Sourcery body is the **weekly-rate-limit** text above (verified at
  `pulls/1063/reviews`, 06:22:38Z). ⭐ **They generalised one PR's cause back onto another without
  re-reading its body — which is the very error their § 3 reports.** The core finding is unaffected and is
  in fact **strengthened**: both causes demonstrably occur, on the same bot, in the same repo, ~8 hours
  apart. ⚠ **Do not scope D1 as though Sourcery only ever size-refuses.**

- ⭐ **OBSERVED 2026-07-30 (inbox `truthful-signals-006` item 3, API-Sheriff PR #132) — the deadlock
  MECHANISM is now named, which this spec previously lacked.** CodeRabbit was *required* there; it raised
  a finding; the fix was pushed; clearing the barrier needed a fresh CodeRabbit pass — **and each push
  consumed another rate-limit slot, the window escalating 2 min → 7 min → 47 min.** It never reviewed the
  final commit `9865794`, the fix for its own finding.
  ⭐⭐ **The keeper framing: "A barrier that can only be satisfied by an action that defeats it is not a
  barrier."** The override there was not exceptional — it was **structurally inevitable**. ⇒ The missing
  discriminator D1 must supply: **"has not reviewed this HEAD"** vs **"cannot review this HEAD right
  now"**, and only the first is worth retrying. ⚠ The window figures and the commit sha are the reporting
  epic's first-party account of their own run and were **not** re-derived here — treat as leads.

- ⚠ Line numbers OBSERVED at 2026-07-29 HEAD on a hot surface. **Re-ground by SYMBOL / heading.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (the barrier section and its two predicates)
- OBSERVED: `.../automatic-review/standards/bot-participation-contract.md`
- HYPOTHESIS: `.../automatic-review/SKILL.md` § "Force-done with an explicit recorded reason"
  (verify-at-outline)
- HYPOTHESIS: the loop-back re-entry path in `.../phase-6-finalize/SKILL.md` (verify-at-outline)
- OBSERVED: the corresponding finalize tests

## Dependencies and Sequencing

- Depends on: none, but **sequence AFTER PLAN-PR-007**. F (`stale` vs `absent`) is an input to this
  deadlock — a false `absent` and a true `absent` are indistinguishable at this barrier, so landing F
  first gives D1 a real signal to classify.
- Overlaps with: ⛔ **PLAN-PR-009** (merge-queue enqueue) edits the same `branch-cleanup.md` merge path.
  **Sequence, never pair.**
- Overlaps with: ⚠ **PLAN-PR-005** — its D2 and this plan's D2 are on the same wrong-observable axis,
  and **PLAN-PR-006** adds a third distinction (canned no-op). If these converge on one detector, say
  so rather than shipping two.
- ⛔ **Overlaps with PLAN-PR-013** (participation credited from a superseded commit) on this same
  barrier predicate. **Sequence, never pair.** They are complementary — this plan gives the barrier an
  *exit* when a bot cannot review; PR-013 makes it *notice* that the required bot reviewed the wrong
  commit. If the two converge on one predicate change, say so rather than shipping two.
- Adjacent to: `truthful-signals` **PLAN-TRUTH-001** (ex-`PLAN-113`,
  `gates-do-not-refire-over-the-loop-back-diff`) and **PLAN-TRUTH-006** (ex-`PLAN-52`,
  `baseline-reconcile-persists-merge-commit`), both **retained there** and both on
  `phase-6-finalize`. ⚠ **Ids renamed 2026-07-30 — use the TRUTH ids when querying their live queue.**
  ⛔ PLAN-TRUTH-001 is retained **deliberately**: `code-intelligence-substrate` has
  already written the PLAN-113 → PLAN-121 sequencing into its own ledger as a hard constraint. Do not
  assume this epic can take it; negotiate with that epic first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-008-review-barrier-deadlocks-on-a-refusing-bot.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
