# PLAN-PR-013: Participation is credited per-PR while the merge is per-commit, so a tree the required bot never saw can merge

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — two independent sightings, drained 2026-07-30

Staged from the epic inbox: `code-intelligence-substrate-001.md` (mode 5 of a five-mode review-coverage
watch, from session observation) and `code-intelligence-substrate-002.md` (a plan's own
review-retrospective on plan-marshall **#1063**). Both were forwarded under the operator's three-way
routing rule and **removed from that epic's ledger** — this epic owns it or nobody does.

⭐ **Staged as its own plan rather than folded, because its polarity is the opposite of every
participation plan already queued.** PLAN-PR-001 / -005 / -006 / -007 all concern a **false negative** —
a real review that fails to be credited, whose worst outcome is a needless loop-back. This is the **false
positive**: credit granted for a review of a commit that is no longer the merge candidate, whose outcome
is *an unreviewed tree merging*. ⛔ Do not merge this plan into PLAN-PR-007: that plan's load-bearing
safety property is that **no merge verdict moves**, and this plan's entire purpose is to move one.

## Objective

The participation question is asked **per-PR** ("did bot X participate on this PR?") while the artifact
that merges is **per-commit**. When a loop-back adds a commit after the reviews, the per-PR answer stays
`yes` and the barrier passes — for a tree the required bot never saw.

## ⛔⛔ RE-SCOPED 2026-08-08 — PLAN-PR-007 LANDED (#1118) AND MOVED THIS PLAN'S GROUND. Read before D1.

`#1118` (`fddc4ec8b`, merged) shipped the widened participation taxonomy. **Two of this spec's premises
changed, in opposite directions, and neither is what a casual reading would assume.**

**1. The blocking half of D3 IS shipped — do not re-build it.** OBSERVED, orchestrator-verified
first-party in merged main at `bot-participation-contract.md` § *Severity by classification*: a
**required** bot resolving to `participated_stale` **is a completeness failure**, blocking exactly as
`absent` does. So "a review of a superseded commit does not satisfy a required-bot gate" is now the
contract's stated rule. ⛔ **D3 must NOT be scoped as "make stale reviews block."** That is done.

**2. But the ANCHOR is still wrong, and this is now the plan's real subject.** OBSERVED, verified by
symbol at `workflow-integration-github/scripts/github_pr.py` § `_has_update_movement` (`:645-677`):

```
return bool(updated_at) and updated_at != created_at
```

⛔⛔ **The currency test keys on COMMENT MUTATION, never on HEAD IDENTITY.** A comment counts as current
evidence when it is first seen, or when its `updated_at` has moved off its `created_at` — **at no point
is any commit SHA consulted.** The contract's own wording concedes it: staleness is defined as *"the
comment was already observed and its `updated_at` has not moved"*, which is a statement about the
comment, not about the diff.

⇒ **The false-POSITIVE this plan owns survives `#1118` intact**, and now has a named mechanism:

| Shape | What the shipped test concludes | Truth |
|---|---|---|
| Bot reviews commit N; loop-back produces N+1; bot edits its comment for **any** reason | `updated_at` moved ⇒ **credited as current** | it never reviewed N+1 |
| Bot's review is first observed on the call that follows a head advance | first presence ⇒ **credited as current** | the review may predate the advance |

⭐ **`reviewed_commit_sha` ALREADY EXISTS in the findings store** — PLAN-PR-005 cites it first-party
(finding `7e3f74`, `reviewed_commit_sha: 69f2270…`), and this spec's own `#1063` evidence turns on it.
**The anchor this plan needs is already recorded and simply is not the thing the barrier consults.**
⇒ D3 becomes: **re-key the currency test onto HEAD identity, using the `reviewed_commit_sha` already
stored**, rather than adding a comparison that does not exist.

⚠ **PLAN-PR-007's own spec predicted this and was not heeded by its implementation** — it warned that "a
detector keyed on diff CONTENT rather than on HEAD IDENTITY would miss [the content-identical rebase]".
What shipped is keyed on neither: it is keyed on **comment mutation**, which is weaker than both.
⭐ **Record this as the epic's sharpest instance of its own theme: a plan that named the right trap,
shipped a member that reads as closing it, and left the trap open one layer down.** The taxonomy is
now honest about *what happened*; the evidence it classifies is still derived from the wrong observable.

⛔ **Re-ground every line reference in this spec against merged main.** `#1118` modified `github_pr.py`
(+90), `review_completeness.py` (+131), `branch-cleanup.md` (+64) and `_github_checks.py` (+120) — four
of this plan's surfaces.

## ⛔⛔ RE-GROUND BEFORE D1 — #1130 ALREADY EDITED THIS PLAN'S TEST FILE

Source: inbox `generic-charter-language-specific-defect-005`, first-party.

PLAN-PR-022's request named this plan as the owner of `automatic-review/review_completeness.py` and its
currency test, and declared *"No file overlap; it stays untouched here."* **It then modified
`test/plan-marshall/automatic-review/test_review_completeness.py`, which landed in `f5493b437`.**

The crossing was **correct on its merits** — D4's outline prediction that "every registry-consuming
module passes unedited" was falsified at execution; two cases asserted the pre-widening record
directly, and the leaf migrated them under update-tests-not-implementation with `compatibility=breaking`
plus a negative control. ⛔ **But nothing recorded that a request-declared exclusion was crossed, and
nothing routed that fact here.** This absorption is that routing, performed by hand.

⇒ **Two of this plan's test cases have already been migrated.** Re-read the currency test against
`f5493b437` before scoping D5, and treat any line reference in this spec as stale until re-grounded.

## ⚠ ABSORBED 2026-08-09 — a re-review trigger that is anti-correlated with the risk

Source: `truthful-signals-026` item 2, **second-hand and not re-derived by this orchestrator — a
LEAD.** Verify against the trigger implementation before scoping.

**Trigger-A skips the rebased-HEAD re-review exactly when no bot review exists to be stale.** ⇒ A
rebase with no prior bot review is the state in which a re-review is *most* needed, and it is precisely
the state the trigger declines to fire on. ⭐ Structurally identical to the `participated_but_empty`
question this epic keeps meeting: **an emptiness treated as "nothing to refresh" rather than as
"nothing has happened yet."** It belongs to this plan because the currency of a participation credit is
exactly what the trigger is deciding.

## Deliverables

1. **D1 — GATE (mutates nothing): establish WHICH commit each participation credit is anchored to.**
   For every site that credits participation, determine whether the credit is compared against the
   current merge candidate's SHA or merely against the PR. ⛔ **Report the anchor per site, not one
   answer for the system** — the corroboration below shows two sites giving *opposite* answers, so a
   single global answer is evidence the derivation was not done.
2. **D2 — resolve the contradiction D1 surfaces, and state which behaviour is correct.** The
   `participation_requires_update` / HEAD-currency test demonstrably withholds credit in one place
   (PLAN-PR-007's `#1059` evidence) and demonstrably did not prevent a merge in another (`#1063`
   below). ⛔ **Both cannot be the intended contract.** The output is a single stated rule for what
   commit participation is credited against, applied at every D1 site.
3. **D3 — the barrier compares participation against the MERGE CANDIDATE.** A review of a superseded
   commit does not satisfy a required-bot gate for a later one. ⚠ **This deliberately moves a merge
   verdict** — it is the one plan in this epic that does — so it must land with D5(c)'s regression
   evidence, never on assertion.
4. **D4 — the re-trigger must cover every required bot, not one.** ⚠ **The quoted mechanism ("Trigger B
   re-triggers only the most-recently-reviewed bot") is UNVERIFIED — see Claim Labels; the corroboration
   found a *hand*-typed single-bot re-trigger, which does not test Trigger B at all.** Verify the
   mechanism against the implementing source BEFORE scoping this deliverable; if the code already
   re-triggers all required bots, D4 dissolves and must be dropped rather than built.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A required bot whose only review predates the
   merge candidate does not satisfy the barrier. (b) A required bot that reviewed the merge candidate
   does. (c) ⭐ **A regression pinning the `#1063` shape end-to-end**: reviews on commit N, a loop-back
   producing commit N+1, and the barrier refusing to credit the required bot. (d) The set of sites D1
   enumerates is **derived**, non-empty, and every member is asserted — copy the population-derivation
   pattern from `test/_shared/_dispatch_roster.py`.

## ⭐ THIRD SIGHTING — `#1067`, merged 2026-07-30, and the sharpest form yet

Orchestrator-verified against the API at the operator's mid-flight report. ⛔ **This instance is worse
than `#1063`, because what merged unreviewed was the REMEDIATION CODE for a bot's own findings.**

| Time (UTC) | Event |
|---|---|
| 11:19:24 | PR opened |
| 11:19:29 | Sourcery refuses — diff-size limit (see PLAN-PR-008) |
| 11:20:37 | ⭐ pr-agent (**required**) posts its Guide. `updated_at` == `created_at` — **never touched again** |
| ~13:10 | **Branch REBASED** — every commit's committer date resets to 13:10:10Z |
| 13:35:43 | CodeRabbit reviews `371854d1`, posts **5 actionable findings** |
| 14:03:46–14:04:05 | **Three loop-back commits** fix those findings: `14d4e3dc`, `c4ff2273`, `76c7200b` |
| 14:41:54 | **Merged** at head `76c7200b` |

- ⭐ **OBSERVED: no review of ANY kind exists after 13:48:28Z.** The three fix commits — the merged tree —
  were reviewed by **nobody**, human or bot. The last 37 minutes before merge contained the only code
  that no reviewer ever saw.
- ⭐ **OBSERVED: the required bot's review predates a REBASE, not merely a later commit.** pr-agent
  reviewed at 11:20:37 against a HEAD that no longer exists — every SHA moved at ~13:10. This is the
  PLAN-PR-007 content-identical-rebase mechanism and this plan's superseded-commit mechanism **composing
  on one PR**: the rebase invalidated the required bot's review, and nothing re-credited or re-triggered
  it before merge.
- ⛔ **The remediation-code observation is the one to carry into D3.** Fixes written under loop-back time
  pressure, addressing defects a reviewer just found, are the *highest*-risk diff on the whole PR — and
  they are systematically the least likely to be reviewed, because they arrive after every bot has had
  its turn. A barrier that credits participation per-PR cannot see this at all.
- ⚠ **Do NOT read the CodeRabbit re-replies (13:48:12–13:48:28Z) as a re-review.** They are thread
  replies to the operator's five triage dispositions posted 13:47:58–13:48:07, all anchored to
  `371854d1`. A reply on a stale commit's thread is not a review of a later one.

## ⭐ The `#1067` coverage picture, completed (inbox `code-intelligence-substrate-004` § 1, 2026-07-30)

The forwarding plan's own inbox message `-004` recorded coderabbit as `refused_awaitable` / "saw the diff:
**no**" — and was **retracted by its own sender** in `-011` once CodeRabbit reviewed at 13:35:43Z. ⭐ **The
correction makes this plan's thesis WORSE, not better.** The final merged HEAD `76c7200b` was reviewed by
**zero of three** configured bots:

| Bot | What it actually reviewed | Saw the merged HEAD? |
|---|---|:---:|
| **pr-agent** (required) | `405b05f06` only — an informational Guide with no actionable content | **no** |
| coderabbit | `371854d14` — the HEAD *before* the 5 fixes it requested | **no** |
| sourcery | nothing, any revision | **no** |

⇒ **Coverage existed, arrived late, arrived by accident, and did not extend to what was merged.**
⭐ Note pr-agent's review is anchored to `405b05f06` — an even **earlier** HEAD than this plan first
recorded, i.e. pre-rebase. The gap is wider than one loop-back.

⭐⭐ **Why `-004` was wrong is itself the finding, and it is the same root cause as PLAN-PR-010's:** it was
generated from the same 11:51 snapshot as `review-retrospective.md` and inherited a **point-in-time
reading of live bot state** instead of querying the **append-only `pr-comment` findings ledger**, which
cannot go stale. ⛔ **Two artifacts were wrong for one reason.** Any fix here should prefer the
append-only store as its source over a live read.

**Still-open dispositions carried from `-004`, now better evidenced:**

- ⭐ **`refused_awaitable` should engage `review_rate_window_await` — waiting demonstrably WOULD have
  worked.** A rebase forced the retry and CodeRabbit reviewed. (See PLAN-PR-008: the knob is shipped and
  switched off; the arming decision is operator-deferred to that plan's D3.)
- A partially-reviewed PR must not present the same `display_detail` shape as a fully-reviewed one; the
  distinction the pipeline lacks is **reviewed-and-clean vs not-reviewed** (shared vocabulary — see
  PLAN-PR-006).
- ⛔ **A required bot's review of an earlier HEAD must not satisfy the barrier at the merged HEAD** —
  this plan's D3, now independently proposed by the forwarding epic.

## ⭐ A TEMPORAL analog of this plan's invariant — `#1066`, verified 2026-07-30

This plan's invariant is *an approval is scoped to the HEAD it was established against*. `#1066` shows
the same failure on the **time** axis instead of the HEAD axis, and D1/D3 should derive on both.

- **VERIFIED** (orchestrator-run `ci pr comments --pr-number 1066` — a check the forwarding epics
  recorded as run by nobody): CodeRabbit's 3 inline review comments are timestamped **11:58:43Z**; the PR
  merged at **12:06:46Z**; **all 8 comments are unresolved**, including a **Major**.
- ⇒ **A real review landed 8 minutes before the merge and was never handled.** The HEAD did not move —
  so this plan's HEAD-scoped check would NOT have caught it. What moved was **time**: findings that did
  not exist at the last fetch existed at the merge.
- ⛔ **HYPOTHESIS, and it is the one to settle at D1**: the FIND step ran *before* 11:58:43Z, returned
  nothing (CodeRabbit was still refusing), and the merge proceeded on that **stale read** — so a review
  arriving between the last fetch and the merge is structurally invisible.
  **Confirm/refute artifact**: `#1066`'s own plan directory — the `automatic-review` FIND step's
  timestamp and returned count in its `logs/` and `phase_steps`. ⚠ The orchestrator could **not** read it
  (`.plan/local/plans/` is outside its carve-out), so this is verify-at-outline and genuinely unsettled.
  ⚠ Note `review_bot_buffer_seconds` is **180** — an 8-minute gap is well outside it, so a buffer alone
  does not explain or fix this.
- ⇒ **D3 should require the barrier to compare against BOTH**: the merge candidate's HEAD *and* a
  findings read taken at the barrier, not one inherited from an earlier step. ⭐ Otherwise the same class
  recurs with no HEAD change to detect.
- ⚠ **Do not conflate this with PLAN-PR-014's D4.** There, a check conclusion was substituted for a
  findings-handled record (a *representation* error). Here, the findings read was simply **stale** (a
  *freshness* error). Same outcome, different fix; if D1 shows one predicate covers both, say so.

## ⛔⛔ ABSORBED 2026-08-03 — THREE more mechanisms, from two sibling epics. This plan is now the epic's highest-value staged item.

Drained from `truthful-signals-014` (items 9 and 11, a consuming project's round-7 bundle findings at
bundle **0.1.1276** — ⚠ **re-ground every line reference, that bundle predates our tree**) and
`code-intelligence-substrate-007` § 2 (first-party to PLAN-CIS-028 / PR #1080, merged `e1ae38142`).

⭐⭐ **The convergence is the finding.** Four independent mechanisms now produce ONE outcome — participation
credited against a SHA that is not the merged HEAD:

| # | Mechanism | Source | New? |
|---|---|---|---|
| a | loop-back adds a commit after the reviews | #1063, #1067 | this plan's origin |
| b | **force-push rewrites the reviewed SHAs away** | `truthful-signals-014` item 9 | ⭐ NEW |
| c | **incremental-review model REFUSES to re-review after loop-back** | `code-intelligence-substrate-007` § 2 | ⭐⭐ NEW |
| d | `reviewed_commit_sha` frozen at record creation, no update path | our own source-confirmed defect | already held |

⇒ ⛔ **D3 must not be scoped to any one of these.** They differ in *how* the anchor goes stale and agree
completely in *what the barrier then does wrong*. **One remedy — evaluate the quorum against the HEAD
being merged, treating a review whose reviewed-SHA is an ancestor of HEAD as STALE EVIDENCE — covers all
four.** A fix aimed at loop-backs alone leaves three live.

### ⭐ Mechanism (b) — force-push, and the cost is measured

`participation_requires_update: false` credits participation recorded against SHAs a force-push has
rewritten away. **The bot reviewed a commit that no longer exists on the branch.**

⛔ **Not hypothetical**: on **API-Sheriff PR #140** all four then-known axes were live at once, the operator
overrode the pre-merge barrier, and **two commits of a pipeline-stage security fix merged with no bot
review of record.** Every individual signal was green.

⭐ **This directly engages this plan's load-bearing HYPOTHESIS below** (that the HEAD-currency test is
applied *inconsistently* across sites). `participation_requires_update` is the switch that decides which
arm runs — so "inconsistent application" may resolve to **"consistent application of a per-bot flag whose
value differs"**. ⛔ **Check the flag's value per bot at D1 before concluding a second currency-blind path
exists.** That distinction changes the fix from *find the rogue path* to *the contract is per-bot and
should not be*.

### ⭐⭐ Mechanism (c) — the incremental-review refusal, and why it is the sharpest form yet

On **#1080**, after a loop-back **CodeRabbit declined to re-review**, stating it *"does not re-review
already reviewed commits"*. ⇒ **The PR's final 8 commits carry no bot review at all — and the participation
quorum read GREEN.** Sourcery was hard-quota throughout, so **two of three reviewers effectively declined
and the quorum passed anyway.**

⭐ **Why this is a defect and not a bot quirk** (the filer's reasoning, kept verbatim because it is the
cleanest statement of this plan's thesis anyone has produced):

> The quorum's **proposition** is about *the diff being merged*; its **evidence** is *the existence of a
> review event*. Those come apart exactly when an incremental-review model refuses after a loop-back —
> **which is the normal shape of a plan-marshall run, not an edge case.**

⛔ **`re_review_on_loopback: false` in the org config is directly implicated, and the cost is now measured
rather than hypothesised.** ⚠ But do **not** scope the fix as flipping that knob: this plan's Prohibited
Remedies already forbid re-reviewing more as the remedy, and mechanism (c) is a bot that *declines* —
re-triggering it produces another decline, not a review. **The remedy is that a decline must be recorded
as `declined` and must not count toward quorum.**

### ⭐⭐ Mechanism (e) — the artifact that LOOKS like participation is the proof it did not happen

`code-intelligence-substrate-007` § 3, and it ties (c) to the detector: CodeRabbit's **trigger
acknowledgement** — *"Review finished. Note: CodeRabbit is an incremental review system and does not
re-review already reviewed commits"* — **was the ONLY record CodeRabbit produced at the final HEAD.**

⇒ ⛔ **The participation artifact and the refusal are the same object.** A detector reading "a comment from
CodeRabbit exists at HEAD" credits participation using the bot's own written statement that it did not
review. ⚠ **Shared with PLAN-PR-006** (which owns the disposition side of this — a summary card / trigger
ack consumes a triage decision to conclude there was nothing to decide). ⛔ **Agree the discriminator once
across both plans**; two detectors for one distinction is the duplication this epic exists to fix.

### ⭐ Mechanism (f) — the edit-in-place blind spot is WIDER than we scoped it

`truthful-signals-014` item 11: **CodeRabbit posted a rate-limit refusal by EDITING an older persistent
comment**, so a `created_at`-ordered sampler never saw it — the comment's creation timestamp **predates
the review round entirely**.

⛔⛔ **We already source-confirmed this mechanism on PR-Agent** (`github_pr.py:783-785` `continue`s on the
`(bot_kind, comment_id)` dedup; `reviewed_commit_sha` written once at record creation with no update
path). **We scoped it to PR-Agent. This is CodeRabbit doing it too.**

⭐ **Our own standing rule fires against us**: *a population-derived detector needs its anchor re-checked
when the fix widens the population.* ⇒ **If a fix is being built against a PR-Agent-shaped population it
is now under-scoped.** Sampling by `created_at` cannot see an edited comment — the detector needs
`updated_at`, **or must read the body of every persistent bot comment rather than only recent ones.**

⚠ Rides along, same item: the **ETA regex does not match the shape actually posted**
(`**Next review available in:** **N minutes**`), so the wait silently defaults to **3600 s**. Small, but it
is the difference between a 12-minute wait that works and an hour that reads as a dead end. ⭐ Measured:
declining to merge and waiting that window cost ~12 minutes and returned **two real defects, one of them a
vacuous guard test.** ⇒ **The detection gap is what turned a signal into a judgement call.**

## ⛔⛔ ABSORBED 2026-08-03 (second drain) — a FIFTH mechanism that the adopted remedy DOES NOT CATCH

From `code-intelligence-substrate-008`, first-party to PLAN-CIS-001 / PR **#1084** (merged `714130bdb`).

On #1084's **first** automated-review pass: **2 of 3 bots refused · nothing retried · the step passed
green.** The refusals produced no findings and **no `declined` record**.

⭐⭐ **Then an unrelated fix moved HEAD, triggering a `head_dependent` re-fire of the review step — and
that accidental second pass returned 14 previously-unseen findings, two of them Major.**

⇒ ⛔⛔ **With a clean self-review round — i.e. had nothing moved HEAD — that branch merges with 14
findings including two Majors never surfaced, behind a green participation check.** The counterfactual is
one absent commit away.

### ⛔ Why this changes the deliverable set rather than adding a row

| The four mechanisms above | This one |
|---|---|
| the review happened, against the **wrong SHA** | **the review did not happen at all**, and the gate said it did |

⛔⛔ **D3 as scoped — evaluate the quorum against the merged HEAD — DOES NOT CATCH THIS.** A refusal at
first pass leaves **no reviewed-SHA to compare**; there is nothing stale to detect because there is
nothing at all. **A HEAD-currency remedy is necessary and not sufficient.**

⇒ ⭐ **The covering remedy is the OTHER half already named in mechanism (c): a bot that declines must be
recorded as `declined`, and `declined` must not count toward quorum.** This absorption **promotes that
from a tidy corollary to a load-bearing, independently-required deliverable.** ⛔ **Do not let the outline
treat it as a sub-clause of D3** — the two halves catch disjoint failure sets:

- **HEAD-currency** catches *a review anchored to a dead SHA*.
- **`declined` accounting** catches *no review at all, reported as participation*.

⚠ **And note what recovered #1084: luck.** An unrelated fix. ⛔ **A defence that holds only because
something unrelated moved HEAD is not a defence** — the same form of the argument the filer used on us in
`-006`, now with a countable blast radius.

### ⭐ A sixth instance of the same shape, from a different direction

`token-total-is-a-partition-labelled-a-whole-001` (PLAN-TRUTH-035 / PR **#1083**, squash `3a20814b1`),
routed here under the three-way rule. **A green `CodeRabbit` check certified a commit range CodeRabbit
never read:**

| Check | State |
|---|---|
| `CodeRabbit` | **SUCCESS** |
| `Sourcery review` | **SKIPPED** |

CodeRabbit's own body records the range it read — base → `bfa2a30aa`. **TASK-14 and TASK-15 landed after
it**, and exist *precisely because they remediate the comments CodeRabbit raised at `bfa2a30aa`.* At the
real head `234d8f97b`, the re-review reply was the incremental-refusal acknowledgement again.

⇒ ⭐⭐ **This is the cleanest statement of the whole plan's thesis**: the remediation commits — the
highest-risk diff on the PR — are systematically the least reviewed, **and the check state says SUCCESS
over exactly the range that was never read.** ⚠ Note the honest reviewer in the same run reported
**SKIPPED** — so the surface *can* represent non-review; **the bot that certified a range it had not read
is the one that read green.**

## Claim Labels

- ⚠ **The 2026-08-03 absorbed items are the filers' first-party observations, re-derived by nobody here.**
  Bundle 0.1.1276 predates our tree. *A corrective is a hypothesis until the named site is read* — this
  plan's own standing discipline, applied to its own new inputs.
- ⭐ OBSERVED (orchestrator-verified 2026-07-30 against the live GitHub API, **not** taken from the
  forwarded message): plan-marshall **#1063** merged at **08:40:48Z**, merge commit `d0da6742`, head
  **`2475cd17`**. Its commit sequence: `225f3be9` (07-29 19:39) → `2a471ae2` (05:18) → `de6eb8be`
  (05:19) → **`2475cd17` (07:05:55Z, the loop-back fix and the merged head)**.
- ⭐ OBSERVED: **both bot reviews are anchored to `de6eb8be`, the SUPERSEDED commit** —
  `sourcery-ai[bot]` `COMMENTED` at 06:22:38Z and `coderabbitai[bot]` `COMMENTED` at 06:31:39Z, both
  carrying `commit_id: de6eb8be`. Neither review names `2475cd17`.
- ⭐ OBSERVED: **the required bot never re-reviewed.** `cuioss-review-bot[bot]` posted its Reviewer Guide
  at 06:23:26Z with `updated_at` **equal to** `created_at` — so it never touched the comment again, and
  `2475cd17` (07:05:55Z) postdates it by 42 minutes. **The tree that merged was never seen by the
  required reviewer, and it merged anyway.**
- ⛔ **PARTIALLY CONTRADICTED — the forwarded headline "the final shipped commit was reviewed by nobody"
  is FALSE, and the correction matters.** CodeRabbit **did** see the final commit: `cuioss-oliver` posted
  `@coderabbitai review` at 07:42:52Z (after `2475cd17`), CodeRabbit auto-replied at 07:43:01Z and its
  walkthrough comment's `updated_at` moved to 07:43:06Z. The accurate claim is **"reviewed by CodeRabbit
  only — the REQUIRED bot never saw it"**, which is still a defect but a different one. ⚠ Scoping to
  "nobody reviewed it" would aim the fix at the wrong gap.
- ⛔ **CONTRADICTED — the message's time-sensitivity is spent.** It was written at 08:08:51Z asserting
  #1063 was still open and the review still obtainable; that was **true when written** and the PR merged
  32 minutes later at 08:40:48Z. ⚠ Recorded because the *lesson* survives the expiry: an inbox message
  carrying a closing window needs the window re-derived at drain time, never trusted from the note — the
  same rule this epic already adopted for cross-epic blockers.
- ⛔ HYPOTHESIS, and it is the load-bearing one: **the HEAD-currency test is applied inconsistently
  across sites.** PLAN-PR-007 records OBSERVED evidence that on `#1059` the currency test correctly
  withheld credit (producing a false `absent`); this plan records OBSERVED evidence that on `#1063` a
  superseded review did not stop a merge. ⛔ **Those two facts cannot both follow from one consistent
  contract** — so either a second, currency-blind participation path exists, or the barrier was
  satisfied by something other than the classifier (a force-done, an operator authorization, a
  `barrier_mode` setting, or the barrier not running at all).
  **Confirm/refute artifact**: `#1063`'s own archived plan directory under `.plan/local/plans/` — its
  execution manifest and its `automatic-review` / pre-merge-barrier step records, which state whether
  the barrier ran and what it concluded. ⚠ **The orchestrator could not read this**: `.plan/local/plans/`
  is outside its direct-file-access carve-out, so this is verify-at-outline and is genuinely unsettled,
  not merely unstated.
- HYPOTHESIS: the quoted mechanism *"Trigger B re-triggers only the most-recently-reviewed bot"* — taken
  from a plan retrospective, re-derived by nobody. **Confirm/refute artifact**: the Trigger B
  implementation in `workflow-integration-github/scripts/github_re_review.py` and its callers in
  `phase-6-finalize`. ⚠ The `#1063` evidence does **not** test it: the single-bot re-trigger there was
  typed by hand, so exactly one bot was named by a human, which is not the code choosing one.
- HYPOTHESIS (an asserted absence — verify it): no consumer depends on per-PR participation semantics in
  a way D3 would break. Verify-at-outline by enumerating the barrier's callers.

## ⛔ Prohibited remedies

- **Do NOT fix this by re-reviewing on every commit.** That trades a soundness defect for a cost and
  rate-limit defect, and this epic already carries a *permanently* unrecoverable diff-size refusal
  (PLAN-PR-008) that more review traffic makes worse. The fix is to compare the credit against the right
  commit, not to generate more credits.
- ⚠ **Do NOT widen what counts as participation to make the barrier pass.** That is the failure mode this
  epic is named after, and it is the exact inverse of this plan's purpose.

## Expected Surface

- HYPOTHESIS: `.../workflow-integration-github/scripts/github_pr.py` — the participation derivation and
  whichever comparison anchors it (verify-at-outline; PLAN-PR-005 and PLAN-PR-001 also claim this file,
  see Sequencing).
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` —
  the pre-merge barrier's participation predicate (verify-at-outline).
- HYPOTHESIS: `.../automatic-review/standards/bot-participation-contract.md` — whether the contract
  states a commit anchor at all (verify-at-outline; an asserted absence, so verify rather than assume).
- HYPOTHESIS: `.../workflow-integration-github/scripts/github_re_review.py` — Trigger B, for D4 only.
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py`.

## Dependencies and Sequencing

- **Sequence AFTER PLAN-PR-007.** That plan settles the taxonomy and its D1 derives the state
  population; this plan changes what the barrier *does* with a member. Landing them in the other order
  would have PR-007 re-open a table this plan just moved.
- ⛔ **Overlaps with PLAN-PR-005 and PLAN-PR-001 on `github_pr.py`. Sequence, never pair.** PR-001 claims
  one function (`cmd_pr_wait_for_comments`), PR-005 claims `fetch_findings`; this plan claims the
  participation *comparison*. The boundary is plausible but **unverified** — confirm at D1 before
  assuming three disjoint functions.
- ⛔ **Overlaps with PLAN-PR-008 on `branch-cleanup.md`'s barrier predicates. Sequence, never pair.**
  The two are complementary: PR-008 gives the barrier an *exit* when a bot cannot review; this plan makes
  the barrier *notice* that the required bot has not reviewed the right commit. ⚠ Both touch the same
  predicate — if they converge on one change, say so rather than shipping two.
- Feeds, and is fed by, `code-intelligence-substrate-001.md`'s mode 3 (a check **completing** with no
  comment), folded into PLAN-PR-007's D1 population. If D1 finds mode 3 shares this plan's root cause,
  consolidate rather than shipping a second fix.

## ⛔⛔ ABSORBED 2026-08-08 — the required bot NEVER re-reviews on push, so a loop-back leaves it permanently unproven BY CONSTRUCTION

Sources: `truthful-signals-020` item 42; C05 lessons `2026-08-03-14-002`, `2026-06-21-21-001`,
`2026-07-16-17-004`. ⛔ **LEADS, NOT FACTS.**

**Item 42 — the mechanism, and it is structural rather than intermittent.** PR-Agent triggers on
`opened` / `reopened` / `ready_for_review` / on-demand `/review` — **never on push**. So any loop-back
that pushes fixes leaves the REQUIRED bot unproven not by bad luck but by construction: there is no
event that would have re-invited it. The ask: `re_review_on_loopback` must POST an explicit `/review`
comment for bots that do not self-trigger, rather than pushing and awaiting.

⭐ **OBSERVED, verified first-party by the orchestrator at this drain** — this project has
`re_review_on_loopback: true` and `re_review_on_branch_cleanup: true` configured
(`marshal.json`, `plan.phase-6-finalize.steps.plan-marshall:automatic-review`). ⇒ **the knob that is
supposed to obtain the re-review is ON, and per item 42 it cannot obtain one from the required bot by
pushing.** That combination — an armed re-review setting that is inert against the one bot whose
verdict gates the quorum — is precisely this plan's superseded-commit defect reached from the *trigger*
side rather than the *evaluation* side. A head-currency check that correctly detects a stale review has
nothing to escalate to if no mechanism can obtain a fresh one.

⇒ **Treat "detect the staleness" and "obtain a fresh review" as one deliverable pair.** Shipping only
the detector converts a silent false green into a permanent hard block, which is the wrong direction
and would strand every loop-back.

**C05 lessons folded as corroboration for the two halves this plan already carries:**

- `2026-08-03-14-002` — the re-review that surfaced 14 previously-unseen findings (2 Major) on #1084
  **fired incidentally, not by design**: an unrelated fix moved HEAD and triggered a `head_dependent`
  re-fire. This is the epic's what-recovered-it-was-LUCK datum, and it is the strongest single
  argument for D3's declined-accounting half being independently required.
- `2026-06-21-21-001` — the re-review **freshness matcher** shipped with a naive-datetime comparison,
  caught only by adversarial PR bots. ⚠ Directly on this plan's surface: whatever this plan builds to
  compare a review's anchor against the current head is the same matcher that already shipped one
  timezone defect. Re-read it rather than extending it blind.
- `2026-07-16-17-004` — a review-bot fix recipe can specify a **vacuous test that passes both pre- and
  post-regression**. ⛔ Binding on this plan's test deliverable: **prove discrimination by mutation
  before accepting done.** The epic's standing rule that every set-guarding detector be
  population-derived applies to the freshness check too.

- HYPOTHESIS (verify-at-outline): that `re_review_on_loopback` in OUR tree pushes-and-awaits rather
  than posting `/review`. Confirm/refute artifact: the `re_review_on_loopback` handling site in
  `automatic-review`'s loop-back path — read what it POSTS, not what its doc says it does. ⛔ This is
  the epic's own doc-contract-divergence archetype; the config being `true` proves the knob is set,
  never that the mechanism works.

### ⭐⭐ RECURRENCE, SAME DAY — `matched: true` recorded against an EXPLICIT REFUSAL, on our own PR #1115

Source: `truthful-signals-023` Finding 1 (PLAN-TRUTH-042), corroborated first-party at that plan's
landing analysis from the **stored comment body** via `ci pr comments --pr-number 1115` — not from a
summary. **This is the plan's own defect, observed end-to-end in our tree.**

`finalize-step-sync-baseline` rebased onto 5 upstream commits after CodeRabbit's last real review body
(16:12:44Z). The follow-up `@coderabbitai review` at 17:37:17Z drew, 11 seconds later:

> ⚠️ **Action not completed** — No files to review. Note: CodeRabbit is an incremental review system
> and does not re-review already reviewed commits.

**The registry recorded `matched: true` with `head_sha_verified: false`.** The bot said *not
completed*; the record says *matched*. The merged tree carries no CodeRabbit review of the head that
actually merged, and nothing downstream can tell.

⭐⭐ **THE SHARP EDGE IS NOT THE MISSING REVIEW — incremental review is the bot's documented, correct
behaviour. It is that `head_sha_verified: false` WAS RECORDED AND NOT ACTED ON.** The deciding bit was
computed, written down, and then ignored by the consumer. ⇒ **A match that cannot name the SHA it
matched is not evidence of coverage of THIS head, yet it satisfies the coverage obligation.**

⇒ **Remedy shape, and it is this plan's D3 stated precisely:** a match with `head_sha_verified: false`
MUST NOT satisfy a coverage obligation — it resolves to a distinct third state
(*reviewed-at-an-earlier-head*) rather than collapsing into `matched`. ⛔ **A taxonomy that collapses
"not yet" into "yes" destroys the deciding bit** — the same collapse this epic has now catalogued at
the absence axis (`absent` naming two states), at the participation axis (a refusal credited as a
review), and here at the freshness axis.

⚠ **This also connects the two halves of the plan's own remedy pair.** Item 42 above says no mechanism
can *obtain* a fresh review from a bot that does not self-trigger on push; Finding 1 says the record
*claims* one was obtained anyway. Same run, same PR class: the missing capability and the false record
of it are complementary, and fixing only the record converts a silent false green into a permanent
block. Ship the pair.

- **OBSERVED** (first-party, #1115): registry `matched: true` alongside `head_sha_verified: false`,
  with the bot's refusal body stored on the PR. Read at the `truthful-signals` landing record
  `landings/PLAN-TRUTH-042.md`; re-read the registry write site at outline to locate the consumer that
  ignores the flag.

## ⛔⛔ ABSORBED 2026-08-09 — THE CURRENCY PREDICATE HAS NO SHA TERM. IT HAS AN OBSERVATION-HISTORY TERM STANDING IN FOR ONE. And this spec's own quote of it is incomplete.

Source: `truthful-signals-027` item 1 (finding `a8d263`, first-party to PLAN-TRUTH-070 / PR **#1132**,
merged — PR state orchestrator-verified at this drain). ⭐⭐ **Unlike every other absorbed item in this
spec, the MECHANISM here is OBSERVED, not a lead**: the orchestrator read the implementing source
first-party at this drain and the reported behaviour follows from it deterministically.

**The report.** On #1132 the same bot was classified two ways by two fetches of the same PR at the
**same HEAD `cbb184c9d`**, ~24 minutes apart — `participated` / `participation_complete: true` at 18:41,
then `participated_stale` / `participation_complete: false` at ~19:05. Nothing about the tree changed:
sync at `cbb184c9d`, rebase `action: noop` with `pre_sha == post_sha`, no push.

### ⛔ FIRST — correct this spec's own OBSERVED claim above (§ "the ANCHOR is still wrong")

That section quotes `_has_update_movement` as:

```
return bool(updated_at) and updated_at != created_at
```

**That is only the SECOND of two arms, and the missing first arm is the one that matters.** OBSERVED,
orchestrator-verified first-party in merged main at
`workflow-integration-github/scripts/github_pr.py` § `_has_update_movement` (`:644-677`) — note the
signature is now three-argument, so every line reference in that section is stale:

```python
def _has_update_movement(comment, observed_keys, bot_kind) -> bool:
    comment_id = str(comment.get('id') or 'unknown')
    if (bot_kind, comment_id) not in observed_keys:
        return True                                            # ARM 1 — first presence
    updated_at = str(comment.get('updated_at') or '')
    created_at = str(comment.get('created_at') or '')
    return bool(updated_at) and updated_at != created_at       # ARM 2 — edit movement
```

`observed_keys` is the plan's **accumulated observation ledger** — the stored-findings keys UNIONED with
the sidecar's noise-dropped keys (`github_pr.py:659-665`), persisted per fetch at `:898`.

### ⭐⭐ The mechanism, and it is neither intermittent nor a race

The ledger grows monotonically across fetches, and the code comment at `:892-897` states the
consequence as **intended design**: *"the record only ever closes that arm on a LATER fetch."*

| Fetch | `(bot_kind, comment_id)` in `observed_keys`? | Arm taken | Verdict |
|---|---|---|---|
| 1st (18:41) | no — never seen | ARM 1 → `True` | `participated` |
| 2nd (~19:05) | **yes — the 1st fetch recorded it** | falls to ARM 2, `updated_at == created_at` for an unedited Guide → `False` | `participated_stale` |

⇒ ⛔⛔ **The first fetch CONSUMES the first-presence credit, so a second fetch of the same unchanged
comment at the same HEAD necessarily flips proven → unproven.** The reported direction is not a symptom
of a flaky input — it is the only direction this predicate can produce.

### ⭐⭐ What this settles, and what it refutes

- ⭐ **CORROBORATED, and sharpened**: the filer's core claim that `participation_requires_update` *"is not
  a pure function of `(bot, comment, HEAD)`"*. It is a function of `(bot, comment, observed_keys)` — and
  `observed_keys` is **the observer's own memory**, not a property of the PR.
- ⛔ **CONTRADICTED — all three candidate mechanisms the filer named.** Not a wall-clock freshness window
  (no clock is read), not a comparison against a mutable PR field such as `updatedAt` (no PR-level field
  is read — `updated_at` here is the COMMENT's own, and only on arm 2), not a paging/ordering effect. The
  varying input is a fourth thing none of the three covers.
- ⛔ **CONTRADICTED — the forwarding orchestrator's ⭐⭐ inference** that this is PLAN-PR-007's trap firing
  with the `updatedAt`-vs-SHA candidate as *"the predicted one"*. Their **direction** is right (currency
  keyed on something other than HEAD identity) and their **named mechanism** is wrong. ✅ They labelled it
  an unverified inference offered as a starting point — the label held, and it is why this drain
  re-derived rather than propagating it.
- ⚠ **UNSUPPORTED — the filer's endorsement that "the barrier re-derives rather than trusting the recorded
  verdict, so this run is evidence FOR the barrier."** The barrier's `false` did not come from
  re-deriving against HEAD; it came from **having looked before**. Neither verdict is HEAD-grounded, so
  the run is evidence about the predicate, not about the barrier. ⚠ Nor can the earlier `true` be called
  the dangerous reading on this evidence: whether that comment predates `cbb184c9d` is not established
  either way — **this drain does not settle which verdict was factually right, only that neither was
  derived from the merge candidate.**

### ⭐⭐ THE NEW DELIVERABLE-SHAPING CONSEQUENCE — the verdict depends on HOW MANY TIMES YOU LOOK

⛔ **The same evidence yields opposite verdicts as a function of fetch count.** A run that fetches once
merges on `true`. A run that fetches twice blocks on `false`. Nothing about the code, the diff, the HEAD,
or the bot differs between them.

⇒ This is an **observer effect in a merge gate**, and it is a distinct failure from the four mechanisms
tabulated above: those are all *"the credit is anchored to the wrong SHA"*, this is *"the credit is not
anchored to a SHA at all, and decays on re-observation."* ⛔ **D1 must report, per site, not only WHICH
commit a credit is anchored to but WHETHER the predicate is idempotent under repeated evaluation** — a
predicate that changes its answer when re-run on unchanged inputs cannot be the basis of a merge verdict
regardless of which SHA it names.

⭐ **This strengthens D3 rather than redirecting it.** `reviewed_commit_sha` is fetched and stamped on
findings at `github_pr.py:904` — the anchor exists in the system and the currency predicate simply never
consults it. Re-keying onto HEAD identity replaces a non-idempotent observation-history term with an
idempotent SHA term, fixing both defects with one change. ⛔ But per the fifth-mechanism absorption
above, it remains **necessary and not sufficient** — the `declined` half is still independently required.

- **OBSERVED** (orchestrator-verified first-party at this drain, merged main): `_has_update_movement`
  two-arm body at `github_pr.py:644-677`; `observed_keys` union contract at `:659-665`; the
  first-presence-consumed-on-a-later-fetch comment at `:892-897`; the `stale_participation` branch at
  `:878-889`; `reviewed_commit_sha` fetched at `:904`.
- **SECOND-HAND** (not re-derived here): the #1132 fetch timestamps, the two verdict payloads, and the
  `noop`-rebase / no-push claims. ⭐ They are consistent with the verified mechanism, which is why the
  mechanism is recorded as OBSERVED while the instance stays a report.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-013-participation-credited-from-a-superseded-commit.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
