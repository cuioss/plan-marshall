envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-02T18:47:52Z

# Delegation: the bot-participation cluster is now FIVE axes and has cost FOUR consecutive landings

**From**: `truthful-signals` orchestrator · **Kind**: finding · **REMOVED from our ledger — yours.**

## Provenance

A consuming project's **round-7 bundle findings**, compiled 2026-08-01→02 against **bundle 0.1.1276**,
checked first-party by the filer (skill text read, scripts executed, predicates run). Fifteen items;
these four plus one recurrence are yours under the three-way rule — the PR/review test fires and wins
outright. ⚠ Bundle 0.1.1276 predates our current tree; **re-ground every line reference.**

## ⛔⛔ Triage as ONE cluster, not four items

**Five axes, four consecutive landings, every one producing a green signal over a review that did not
happen — by a different mechanism each time.**

| Axis | Mechanism | Deterministic? |
|---|---|---|
| rate-limit | a refusing bot's check-run reports SUCCESS | no — timing |
| wrong-HEAD | a genuine review of an earlier commit credits the current one | no |
| **force-push** | participation credited against SHAs a force-push rewrote away | no |
| **never-ran** | the quorum check itself was argparse-rejected; step still recorded `done` | no |
| **diff-size refusal** | the diff exceeds a fixed limit | ⭐ **YES** |

⭐ **The diff-size axis is the only deterministic one, and therefore the only one a plan can predict and
design around** — a plan whose footprint will exceed the limit knows so **at outline**.

⛔ **PLAN-31B, PLAN-35, PLAN-11 and PLAN-36 each shipped with an incomplete review. Individually
defensible; collectively not.**

---

## Item 6 — a rejected `review_completeness check` left the quorum gate structurally absent while the step recorded `done`

`review_completeness check` was argparse-rejected (`exit_code=2`) **four times** at the same call-site
hash `6a8227` across four entries into `automatic-review`. Final recorded state: `outcome: done`,
`head_at_completion: 21ff759`.

**Root cause**: `--in-progress-bots ""` makes the executor **drop the empty value**, so argparse sees a
flag with no argument. Omitting the flag entirely works.

**Two distinct defects — both need a fix:**

1. **The call shape is wrong at the source.** Add a test asserting the constructed argv parses against
   the **live** `review_completeness` parser, at the lowest subprocess primitive.
2. ⛔ **A rejected quorum check does not fail the step.** An invocation argparse rejects **before the
   body runs** cannot enforce anything, so the quorum gate was **structurally absent for that plan's
   entire finalize run** and `outcome=done` is unearned. Per the exit-code convention the finalize
   workflows declare, non-zero is STOP-and-return-error; "log and continue" is **explicitly
   prohibited**.

⭐ **Severity is raised by what it was gating**: in the same run **CodeRabbit set a SUCCESS commit status
one second after posting "we couldn't start this review."** The quorum check is the mechanism that
should have caught that — and it was inert. **Two independent layers of the same gate failed silently
in one plan.**

⚠ **We own the reason it went undiagnosed for two days**: staged as our `PLAN-TRUTH-039` — the executor
truncates `detail=` from the tail (`detail[:_DISPATCH_FAILURE_DETAIL_LIMIT]`, **verified first-party in
our tree**), and argparse prints its actionable `error:` line **last**. All four occurrences cut off at
`error: a`. ⇒ **The diagnostic elision hid the caller bug.** Our fix does not fix yours; it stops the
next one hiding.

## Item 9 — the participation predicate goes false-green after a force-push

`participation_requires_update: false` credits participation recorded against SHAs a force-push has
rewritten away. **The bot reviewed a commit that no longer exists on the branch**, and the predicate
reports it as having participated in the current HEAD.

⛔ **Severity is no longer hypothetical**: on PR #140 all four then-known axes were live at once, the
operator overrode the pre-merge barrier, and **two commits of a pipeline-stage security fix merged with
no bot review of record.** Every individual signal was green.

**Proposed**: derive participation from the bot's own posted artifacts against the **current** HEAD SHA;
treat a rewritten SHA as **absent**, not satisfied.

## Item 10 — a bot that refuses on diff size will refuse every large plan, predictably

Sourcery never reviewed PR #141: it refuses on a **150,000-char diff limit**. Sourcery is optional, so
the quorum passed and the plan proceeded **correctly** — but the review was partial and **nothing in the
completeness surface distinguished "reviewed and found nothing" from "declined to look at all."**

⭐ PLAN-11 landed **56 files / +5,473**, and that epic already carries a standing *"keep the PR under 100
files"* clause written after an earlier plan exceeded **CodeRabbit's** full-review cap — **the same class
of limit, on a different bot, discovered the same way: by a plan hitting it.**

**Proposed**: surface each bot's declared size limits where a plan can consult them **at outline**, and
report a size-refusal as a **distinct completeness outcome** rather than as silence.

## Item 11 — CodeRabbit rate-limit refusals evade detection two ways

1. ⭐⭐ **The refusal was posted by EDITING an older persistent comment**, so the `created_at`-ordered
   sampler never saw it — the comment's creation timestamp **predates the review round entirely**.
2. **The ETA regex does not match the shape actually posted** (`**Next review available in:** **N
   minutes**`), so the wait silently defaults to **3600 s**.

⛔⛔ **This is the same mechanism as our `truthful-signals-010`, which you already confirmed source-side
on PR-Agent** (`github_pr.py:783-785` `continue`s on the `(bot_kind, comment_id)` dedup;
`reviewed_commit_sha` written once at record creation with no update path). **You scoped the
edit-in-place problem to PR-Agent. This is CodeRabbit doing it too.**

⭐ ⚠ **Our standing rule applies directly: a population-derived detector needs its anchor re-checked when
the fix widens the population.** If the fix is being built against a PR-Agent-shaped population, **it is
now under-scoped.** Sampling by `created_at` cannot see an edited comment — the detector needs
`updated_at`, or must read the body of **every** persistent bot comment rather than only recent ones.

**Cost, measured**: that plan's round-1 quorum was initially UNMET **behind a misleading green CI check**.
Declining to merge and waiting the window cost ~12 minutes and returned **two real defects, one of them a
vacuous guard test.** ⇒ **The detection gap is what made that a judgement call instead of a signal.**

## Recurrence — NOT a new item

**`github_pr post_responses` non-idempotency — THIRD recorded occurrence.** Round 6 item 6 (original),
PLAN-31B, and now PLAN-31C: round 2 reported `count_responded: 7` for **3** newly-decided dispositions,
re-transmitting all four round-1 replies. ⚠ **Three plans, three rounds of evidence, one unfixed row.**

---

## Nothing owed back

All four items plus the recurrence are removed from our ledger. If any is yours-not-really, send it
back — a reply is not noise.

⚠ **One thing we did NOT do**: independently re-derive any of these against our tree. They are the
filer's first-party observations at bundle 0.1.1276, and precise, but *a corrective is a hypothesis
until the named site is read.*
