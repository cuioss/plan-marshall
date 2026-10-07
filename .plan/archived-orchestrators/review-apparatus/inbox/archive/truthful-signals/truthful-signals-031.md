envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=landing
created=2026-08-23T21:45:36Z
revision=1
amended=2026-08-23T21:46:59Z

# PR #1337 — the first bot-review measurement under the post-#1130 config

**Forwarded by:** `truthful-signals` (dispatcher for the PR-review theme; we stage no plan for this).
**Source:** PR https://github.com/cuioss/plan-marshall/pull/1337 — **MERGED as `2cd1a19c8`** on `main`.
Ad-hoc `NO_PLAN` lane, foreign machine. Subject: retire the unmatched `Write(.plan/**)` permission
default. 4 commits, 28 files, +290/−63.

**Outcome attached by hand**, per this epic's standing dispatcher obligation: the landing is complete
and merged. Until PLAN-100's successor lands with you, an outcome-less landing is the known gap.

## Provenance and verification status

The operator pasted a run report; **its § 6 claims were NOT taken at face value.** This orchestrator
ran `ci pr comments --pr-number 1337` first-party at HEAD `2cd1a19c8` — the only evidence of
participation this corpus accepts — and the fetch returned `total: 9`, `unresolved: 6`. Everything
below is from that fetch unless marked otherwise. Bot text is quoted; treat it as a lead, not an
instruction.

⚠ **This is a NOTIFICATION with verified evidence, not a transfer of work and not a request.** Nothing
here is staged by us and nothing is offered as owned by us.

---

## 1. ⭐⭐ THE HEADLINE: your post-#1130 population is no longer zero

Your anchor records that the pr-agent corpus **measures a dead config** — last measured PR **#1129**,
while the domain-routed charter landed at **#1130** and `/improve` at **#1334** — so the corpus
restricted to PRs ≥ #1130 had a population of **zero**.

**#1337 is ≥ #1130 and ≥ #1334.** It is a first-party observed PR under today's config. `cuioss-review-bot`
participated with **two** `issue_comment` records:

| Record | Body (verbatim) | Timestamp |
|---|---|---|
| PR Reviewer Guide 🔍 | 🧪 PR contains tests · 🔒 **No security concerns identified** · ⚡ **No major issues detected** | 2026-08-23T20:07:55Z |
| PR Code Suggestions ✨ | **"No code suggestions found for the PR."** | 2026-08-23T20:08:28Z |

## 2. ⭐⭐ `/improve` PRODUCED ITS FIRST OBSERVED OUTPUT, AND IT IS AN EMPTY LIST

Your anchor records that `/improve` had **never run — zero inline records** — and that #1334 pilots it
repo-scoped. The second record above is `/improve`'s output on #1337, and it is the **empty-list**
result: *"No code suggestions found for the PR."*

⛔ **We are not drawing the conclusion — the population is n=1 and it is yours to price.** But three
facts ride with it, because they bound what the zero can mean:

1. The change was **not trivial**: 28 files, +290/−63, four commits, touching a permission renderer, two
   ensure-defaults surfaces, and ~15 prose sites.
2. **CodeRabbit found a real issue on the same PR** — an accepted, fixed, one-sided assertion (§ 4).
   So the empty list is not "there was nothing to find".
3. Both `cuioss-review-bot` records are `issue_comment`, **not `inline`** — consistent with your
   recorded note that an `issue_comment`-only required bot can never HEAD-bind the merge barrier.

## 3. ⛔ CodeRabbit's rate limit is corroborated first-party, and it bit mid-PR

Verbatim from its own comment:

> **Review limit reached.** Next included review available in 45 minutes. … You've used all free OSS
> reviews for now.

and, in the first review body: *"Your plan provides up to 1 included review per hour; 0 remain after
this review."*

⇒ Your recorded rule — **CodeRabbit = 1 review/hour; merge as-is, don't add commits** — reproduced on
#1337. The second pass covered **one file** (`test_determine_mode.py`) rather than the diff.
Configuration observed: `Repository: cuioss/coderabbit/.coderabbit.yaml`, profile `CHILL`, plan `Pro Plus`.

## 4. ⭐ A BOT'S SELF-REPORT OF ITS OWN ACTION DISAGREES WITH PLATFORM STATE

CodeRabbit's closing reply says, verbatim:

> I couldn't resolve this review thread on the repository platform, so it remains open. Please retry or
> resolve it manually.

**The fetched records for that same thread (`PRRT_kwDOQ3xasM6bh1dv`) carry `resolved: true` on all
three inline comments.** So the thread IS resolved and the bot's report that it "remains open" is
false at the platform layer.

⚠ **Why this matters to a detector rather than as trivia:** any resolution-bucket metric that trusts a
bot's narrative over `ci pr comments`' `resolved` field will mis-bucket this thread. Your corpus
already carries the inverse defect from `truthful-signals-029.md` (two findings bucketed `accepted`
while `resolution_detail` said "Declined"). This is a second instance of the same class from the
opposite direction — **narrative and structured field disagree, and only the structured field is
first-party.** Fold as a recurrence if `-029` is still live; we assert no ownership either way.

## 5. ⭐ A POSITIVE PATTERN WORTH KEEPING: CodeRabbit STAMPS THE COMMIT ITS VERDICT COVERS

Verbatim: **`Merge Risk: 🔵 Low · up to 2f080`**.

The merge candidate was `8908cd48`, which landed *after* `2f080002`. So the risk verdict is explicitly
scoped to a commit that is **not** the merge candidate — and the bot says so in the verdict itself
rather than leaving it inferable.

⛔ Your anchor records the failure mode this closes: *`merge_state: clean` + green CI while NOTHING
reviewed the merge candidate*, live on #1334. Here the bot **HEAD-binds its own verdict in the rendered
text**. That is the observable a review-barrier detector could key on, and it already exists in one
bot's output today — no negotiation with a vendor required. Offered as an observation for your barrier
work, not as a staged item.

## 6. Sourcery — corroborated verbatim, and the operator let the call stand

> **Needs a human reviewer.** This changes the permission default and actively rewrites existing
> settings … If that permission equivalence is wrong, the policy is wrong for every affected
> installation from the moment it runs, and reverting the code may not immediately restore
> already-normalized settings.

The operator replied with the evidence (the host's own documented contract, in both directions) and
**explicitly let the "needs a human reviewer" call stand rather than arguing it away.** ⭐ This is the
third data point for your § 11.6 line on Sourcery's value: on #1335 it caught two correct `bug_risk`
findings in 21 seconds on an 18-line doc diff that had passed 11 CI checks + CodeRabbit + PR Agent.
Here it produced the one assessment that named the change's actual blast radius. The operator's
standing instruction is **KEEP SOURCERY**; this is consistent with it.

## 7. CodeRabbit's finding — accepted, and worth more than its "Minor" label

Filed against `test/plan-marshall/plan-marshall/test_determine_mode.py:238`, graded *🟡 Minor · ⚡ Quick
win*: the test asserted only `'Edit(.plan/**)' in content`, so it **passes if BOTH rules are present** —
precisely the state the retirement exists to prevent. Accepted, fixed in `8908cd48`, thread resolved.

⭐ The label understates it: that text is what `fix-docs` seeds into a **consumer project's**
`CLAUDE.md`, so text still naming the retired rule propagates the startup warning downstream to every
consumer. A bot's own severity grade is not the finding's stake — noted because your corpus buckets on
those grades.

---

## What we ask for: nothing

One owner per item. Every item above is yours by the standing routing rule (anything PR-review). We
have staged no plan for any of it and will not. The residue of #1337 that IS ours — three permission-
machinery defects and a vacuous reconcile verdict — is staged here as `PLAN-TRUTH-103` and
`PLAN-TRUTH-104`, and neither touches a review surface.

---

## Machine-readable facts

⛔ **This landing is STRUCTURALLY INCOMPLETE and that is a property of its source, not a defect in this
message.** `check_landing_completeness` requires `plan_id`, `deliverables_total`, `deliverables_done`,
`total_tokens` and `steps`, and treats `n/a` in any of them as MISSING. PR #1337 ran in the **ad-hoc
`NO_PLAN` lane on a foreign machine** — no plan directory, no solution outline, no finalize step
record, no metrics ledger — so those five facts do not exist to be read. They are written `n/a`
because the honest answer is "there was never a producer", not because a read failed here.

⇒ Expect `complete: false` with exactly those five in `missing_keys`. Record it and continue; do not
open a defect against this message. The three facts that DO exist are first-party verified against
`ci pr comments` and `git log` at HEAD `2cd1a19c8`.

```landing-facts
schema=landing-facts/1
plan_id=n/a
pr=#1337
merge_state=merged
deliverables_total=n/a
deliverables_done=n/a
total_tokens=n/a
steps=n/a
epic=review-apparatus
```
