envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:46Z

component=plan-marshall:automatic-review
category=bug

# Review-bot coverage evidence: an issue_comment re-review still reads as DECLINE, bot_completion never reads coveredCommitId, and re_review_on_loopback=false owes a per-bot trigger nothing enforces

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Two lessons filed in **API-Sheriff's**
store, whose repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11. Most sub-claims
are already owned by the `review-apparatus` epic — **forward rather than re-stage**; this message is
chiefly second-repo sightings plus one correction and one contradiction worth resolving.

Origin ids: `2026-09-02-22-003` (created 2026-09-02, recurrences through 2026-09-10),
`2026-09-02-22-004` (created 2026-09-02).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| (a) `participation_requires_update: false` grants credit from a comment of any age, even when the bot declined HEAD | FIXED by #1409 (`66320e70d`) | `coderabbit.md:50` now `participation_requires_update: true`; stale first-observation credit refused (`github_pr.py:946-951`, `_comment_predates_commit`); quota refusal routes to `refused_bots` | shipped |
| (b) `_references_head_sha` inspects only the `review` signal, so an `issue_comment` re-review ("Review updated until commit `6330a46`") is `head_sha_verified=false` → DECLINE | STILL-VALID | `github_re_review.py:755` `'head_sha_verified': matched_signal == 'review'`; `_references_head_sha` called only in the review branch (`:932`) | review-apparatus PLAN-PR-043 D5a (staged); lesson `2026-09-05-11-002` (active) |
| ⛔ CORRECTION to (b): the lesson says `fetch_findings` "already extracts `reviewed_commit_sha` from that same comment" | **REFUTED** | `fetch_findings` stamps the **PR head** (`github_pr.py:1258`), it does not parse the comment — so there is no correct extractor to reuse; the lesson's directive 7 ("collapse onto the existing resolver") has no resolver to collapse onto | — |
| (c) "No actionable comments were generated" + `coveredCommitId == HEAD` read as never-reviewed | PARTIALLY FIXED | `cmd_bot_completion` (`github_pr.py:1929+`) reads only `gh pr checks` name/state; `coveredCommitId` appears nowhere in the marketplace. Participation side now accepts CodeRabbit `issue_comment` under the freshness test (`coderabbit.md:49`) | PLAN-PR-046 (launched), PLAN-PR-053 (staged, `coveredCommitId` at `:94`), PLAN-PR-048 D0 |
| (d) `re_review_on_loopback: false` → loop-back requests no re-review; nothing obliges a per-required-bot trigger | STILL-VALID | `automatic-review/SKILL.md:219` skips the section; `:968` leans on the barrier to block; `branch-cleanup.md:1109` only warns | queued `lessons-handling-26-09-04-01-047`; PLAN-PR-043 D1 (staged) |
| (e) rate-limited required bot deadlocks the merge; fresh PR wrapper is the way out | FIXED, **default OFF** | Branch 5 close-and-reopen `automatic-review/SKILL.md:709-735`, gated by `review_rate_window_await` default `false` (`:391`) | PLAN-PR-025B (shipped #1433) |
| ⚠ CONTRADICTION between lesson and shipped doc | UNRESOLVED | lesson `-004` observed a fresh wrapper PR getting a full-diff review "outside the exhausted window" (PR #246/#247 → #248, 13 and 9 new findings); `automatic-review/SKILL.md:715-716` states a fresh PR does **not** restore quota. One of the two is wrong for CodeRabbit's current quota model — worth a measured check before Branch 5's wording is relied on | — |

**What this message adds:** the (b) correction, the (e) contradiction, and a second-repo sighting for
(b)/(c)/(d). Suggested disposition: forward (b)–(e) to `review-apparatus` as sightings; nothing here
needs a new truthful-signals spec.

Local residue in API-Sheriff: `re_review_on_loopback: false` with no recorded rationale — already an
Open Defect in the API-Sheriff `deployment-configurability` epic.

---

## Original lesson `2026-09-02-22-003` (verbatim)

id=2026-09-02-22-003
component=review-bots
category=anti-pattern
status=active
created=2026-09-02

# A review-bot participation credit can be structurally HEAD-blind - check the bot's own commit stamp

## Observation

The merge gate for this branch treats a required review bot as satisfied when it has "participated".
CodeRabbit's registry entry declares `participation_requires_update: false`, which means the
participation credit is granted from **any inline comment of any age** — including comments written
against a commit that is many pushes old.

On PR #248 that produced a credit that was structurally unable to see the current tree: CodeRabbit
had **explicitly declined to review the current HEAD for quota reasons**, and simultaneously read as
"participated" because older inline comments existed. The merge gate would have accepted that as a
completed required review.

What actually settled the question was not the credit but **external evidence about which commit the
bot had seen**:

- the bot's own stated commit range in its review body,
- the `coveredCommitId` stamp it publishes,
- the `reviewed_commit_sha` recorded on the findings it filed.

All three named a commit that was not HEAD. The credit named nothing at all.

## The general shape

A participation/completion credit is a **derived** signal, and its derivation can be blind to the
axis the gate actually cares about. Here the gate cares about *coverage of the current HEAD*, while
the credit measures *existence of a comment*. Those two agree on the happy path and come apart in
precisely the cases a gate exists for: a rate-limited bot, a bot that errored after commenting, a
bot whose run was cancelled mid-push.

## Directive

1. **Never let a boolean credit stand in for HEAD coverage.** Before treating a required review as
   satisfied, resolve which commit that reviewer actually reviewed and compare it to HEAD.
2. **Prefer evidence the reviewer emitted about itself** — stated commit range, `coveredCommitId`,
   `reviewed_commit_sha` on its findings — over any status the gate computed about it.
3. **Read a declined/skipped/rate-limited notice as a negative, not as silence.** A bot that says it
   is skipping this run has told you its coverage is zero for this HEAD; that statement outranks any
   participation flag derived from its history.
4. **Where a registry declares `participation_requires_update: false`, treat every credit from that
   reviewer as unproven by construction** and require the HEAD check explicitly.

## Evidence

PR #248: CodeRabbit read as participated while its own published commit stamp named a superseded
commit and its review body stated it was skipping the current HEAD for quota. Detected by hand;
nothing in the automated gate would have flagged it.

## 🔄 RECURRENCE 2026-09-04 — the SAME axis, failing in the OPPOSITE direction (PLAN-10 / PR #257)

The original entry recorded a credit **wrongly granted**: a boolean participation flag standing in
for HEAD coverage the bot did not have. PLAN-10 hit the mirror image — a credit **wrongly denied**
for a bot that verifiably *did* review HEAD.

`_references_head_sha` inspects only the `review` signal. `pr-agent` publishes its re-review as a
persistent `issue_comment`, so its review was classified `head_sha_verified=false` and escalated as
a DECLINE even though the comment body named the reviewed commit verbatim
(*"Review updated until commit `6330a46`"*). CodeRabbit had separately declared
`coveredCommitId=6330a46 kind=reviewed` with no actionable comments. Both required reviewers had
demonstrably reviewed the merge candidate; the barrier still reported `participation_complete=false`
with `unproven_bots=[pr-agent]`.

⛔ **Two resolvers in one pipeline disagree, and only one is right.** The barrier's own producer —
`github_pr fetch_findings` — extracted `reviewed_commit_sha=6330a46` from that same comment-shaped
signal and reported an empty `stale_participation_bots`. So the correct extraction already exists in
the pipeline; the verification path simply does not use it. That internal disagreement is what makes
this a matcher gap rather than a genuine stale review.

**Cost paid:** loop-backs consumed to the 3/3 ceiling, then a hand-verified
`rereview-timeout-override` merge authorization — a manual, judgement-bearing override standing in
for a matcher that should have resolved automatically.

## What the recurrence changes about the directive

Directive 2 above — *prefer evidence the reviewer emitted about itself* — is **exactly** what
resolves this case, and it was already written. What was missing is that the directive must be read
as **symmetric**:

6. **A missing credit is as suspect as a granted one.** Before accepting a DECLINE, resolve the
   commit the reviewer actually reviewed from its own emitted evidence, whatever SHAPE that evidence
   arrives in — a `review`, an `issue_comment`, a stamp on a finding. A gate that reads only one
   signal shape reports a bot's silence when the bot in fact spoke in another shape.
7. **Where two code paths both extract the same fact, one of them is redundant and one of them is
   wrong.** Collapse them onto a single resolver rather than adding a third extractor. Upstream
   remedy: extend the comment-path matcher to reuse what `fetch_findings` already does.

⚠ **This is a plan-marshall producer-side defect, not an API-Sheriff one** — the remedy lives
upstream. It is recorded here because the *cost* is paid in this repository, on every plan, and the
manual override is the only local workaround.

## 🔄 THIRD OCCURRENCE 2026-09-05 (PLAN-15 / PR #267) — and this one is the LOCAL configuration, not an upstream matcher

The first entry recorded a credit wrongly GRANTED. The 2026-09-04 recurrence recorded one wrongly
DENIED by an upstream matcher gap. This one is neither: **both required bots were silent after a fix
push for two different, entirely legitimate configuration reasons**, and this repository owns both.

1. **CodeRabbit** would normally re-review on push, but this project sets
   `re_review_on_loopback: false` (`.plan/marshal.json:108`), so the loop-back path requests nothing.
   It needed an explicit trigger.
2. **PR-Agent** does not re-review on push at all, by its own workflow design:
   `.github/workflows/pr-agent.yml` triggers only on `opened` / `reopened` / `ready_for_review` plus
   on-demand `issue_comment` commands. It needed a separate `/review` comment.

⛔ **From the outside the two are indistinguishable, and both are indistinguishable from a clean
re-review.** All three present identically: a pushed fix, and no new comments. A run that reads that
silence as approval merges over an unreviewed fix — the gate looks green because nothing spoke, not
because something passed.

That **both** required bots are affected is what raises this above a note. `required_bots` names
`coderabbit,pr-agent`, both gate the merge, and after any fix push neither speaks on its own — so the
re-review obligation must be discharged by **two different explicit acts, every loop-back**.

## What the third occurrence adds

8. **Assert the re-review RAN; never infer it from an absent comment.** The correct post-fix-push
   assertion is *"each required bot reports a completed review against the current head SHA"*
   (`workflow-integration-github bot_completion`), not *"the unresolved count is zero"*. Zero
   unresolved comments over zero reviews is a vacuous pass.
9. **When `re_review_on_loopback: false` is the intended setting, the loop-back owes an explicit
   trigger for every required bot as part of the loop-back** — not left to be noticed. PLAN-15 spent
   two loop-back iterations discovering this by hand.
10. **An optional bot's silence is a real coverage gap even when it correctly does not gate.**
    Sourcery refused on a hard quota (~22h ETA) and never reviewed #267. It is in `optional_bots`, so
    the merge was correct — but the coverage was not obtained, and "did not gate" is not "was
    covered".

## ⛔ CORRECTION 2026-09-07 — the `required_bots` half of the 2026-09-05 occurrence was FALSE

The third occurrence above cites `re_review_on_loopback: false` and `pr-agent.yml`'s trigger set;
**both of those stand and were verified first-party.** What does NOT stand is the accompanying claim,
carried in this corpus and in the epic ledger, that `required_bots: coderabbit,cuioss-review-bot` was
a broken token naming an author login rather than a registry `bot_kind`.

`automatic-review/standards/cuioss-review-bot.md:56` declares `bot_kind: cuioss-review-bot`. Upstream
commit `cc5ea40a1` (2026-09-03) renamed `pr-agent.md` to `cuioss-review-bot.md`; no `pr-agent.md`
remains. API-Sheriff's `1c7308c` (2026-09-02) tracked that rename **a day early**. The configuration
was correct from 2026-09-03 onward, and the claim that no registry doc existed was already false when
it was filed on 2026-09-04.

**Why it survived four landings:** it was an asserted *absence*, relayed from a plan's inbox message,
and recorded without opening the registry. It was precise, mechanism-level and internally coherent —
and wrong. Directive 2 of this lesson already says *prefer evidence the reviewer emitted about
itself*; the same discipline applies one level up:

11. **A claim relayed from a plan's message is a LEAD, not a fact — and an asserted ABSENCE is the
    half that needs opening the file.** Precision is not evidence. "No such registry doc exists" costs
    one `find` to check and four landings of misdirected operator attention not to.

## 🔄 RECURRENCE 2026-09-10 (plain-http-termination-mode) — a COMPLETED review read as NO review

Directive 8 above says *never infer that a review ran from an absent comment*. This run failed the
**converse** of the same sentence: it inferred that **no** review had run from an absent comment.

CodeRabbit performed an incremental re-review after a fix push and returned **zero comments**. The
orchestrator read "zero comments" as "the bot never reviewed this HEAD" and set about forcing a
re-review. The evidence that it *had* reviewed was sitting in the comment body the whole time:

- `final_review_risk_coverage` carrying a `coveredCommitId` equal to the pushed HEAD, and
- the literal sentence **"No actionable comments were generated"** — a positive statement of a
  completed review with an empty finding set, not silence.

**Cost paid:** two trigger attempts against a rate-limited bot, and a wait of roughly 90 minutes for
a quota window, to re-obtain coverage that already existed.

## What this recurrence adds

12. **"Zero comments" is ambiguous by itself and must never be resolved by assumption.** It is either
    *reviewed, nothing to report* or *never reviewed*. Both present as an empty finding list. Resolve
    it from the bot's own emitted evidence — the `coveredCommitId` stamp and the review body's own
    wording — exactly as directives 2 and 6 already require. This is the third direction the same
    axis has failed in: credit wrongly granted, credit wrongly denied, and now **coverage wrongly
    read as absent from a successful review**.
13. **Read the comment BODY before acting on the comment COUNT.** A count is a derived signal; the
    body is the reviewer's own statement about what it covered. Counting is cheap, which is why it is
    reached for first, and it is precisely the signal that cannot distinguish the two cases.
14. **A re-review trigger is not free — it is the most expensive possible way to answer "did it
    review?"** against a rate-limited bot: on failure it costs a quota window (~90 min here) and can
    deadlock the merge (`2026-09-02-22-004`). Exhaust the free evidence in the existing comment
    before spending a trigger.

---

## Original lesson `2026-09-02-22-004` (verbatim)

id=2026-09-02-22-004
component=review-bots
category=improvement
status=active
created=2026-09-02

# A rate-limited required review bot deadlocks the merge - a fresh PR wrapper is the way out

## Observation

A required review bot hit its provider-side rate window and stopped reviewing new pushes on the open
PR. Because the bot is *required*, the merge gate could not clear, and because the rate window is
keyed to the PR/run rather than to the branch, **pushing more commits did not help** — each push was
declined the same way. The merge deadlocked twice on this.

What broke the deadlock was **closing the PR and opening a fresh one onto the same branch**. A new
PR is a new review target: the bot performs a full-diff review of the branch outside the exhausted
window.

The cost was real but bounded: two PR wrappers (#246 and #247) were closed unmerged before #248
landed. It was also **not pure overhead** — each fresh full-diff review surfaced further findings
(13 on the first wrapper, 9 on the second), several of them substantive defects that the
incremental per-push reviews had never covered because they never ran.

## Directive

When a required review bot is rate-limited and the merge gate cannot clear:

1. **Confirm it is a rate window, not a failure** — the bot usually says so explicitly in a comment
   or check summary. Retrying a failed run is right; retrying a quota-declined run is not.
2. **Do not push empty commits or re-request review in place.** Both consume time and neither leaves
   the window.
3. **Close the PR and open a new one from the same branch.** Carry the description over. The branch,
   its commits and its CI history are untouched; only the review target is new.
4. **Budget for the new findings.** A fresh wrapper gets a *full-diff* review, so expect it to
   surface issues the incremental reviews skipped — treat that as the point of the exercise, not as
   a surprise. Triage them before merging.
5. **Record the closed wrappers' numbers in the final PR body** so the review history stays
   traceable across the wrapper boundary.

## Caveat

Each wrapper resets the review conversation: unresolved threads on the closed PR do not follow the
branch. Resolve or transcribe anything still open before closing, or the finding is silently
dropped.
