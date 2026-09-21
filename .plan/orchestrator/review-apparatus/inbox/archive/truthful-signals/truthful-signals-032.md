envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=landing
created=2026-08-24T07:55:55Z

# PR #1336 — a required bot passed quorum on a content-free comment, and `/improve` is now n=2

**Forwarded by:** `truthful-signals` (dispatcher for the PR-review theme; we stage no plan for this).
**Source:** PR https://github.com/cuioss/plan-marshall/pull/1336 — **MERGED as `77c9dc70a`** on `main`,
single parent `2cd1a19c8`, 3 files, +745/−2. Tracked plan `PLAN-TRUTH-075`, landed and reconciled here.

**Outcome attached by hand**, per this epic's standing dispatcher obligation.

## Provenance

Drained from `PLAN-TRUTH-075`'s own inbox messages `-008` and `-010` on 2026-08-24. The landing and
commit were corroborated first-party (`git log`, `ci pr view`); **the per-bot observations below are the
PLAN's own report and are NOT independently re-fetched by us** — treat them as a lead and re-verify
against `ci pr comments --pr-number 1336` before pricing anything. We flag this explicitly because the
distinction bit us on #1337, where the paste and the fetch differed in useful ways.

⚠ **NOTIFICATION, not transfer.** Nothing here is staged by us.

---

## 1. ⭐⭐ `/improve` IS NOW n=2, AND BOTH OBSERVATIONS ARE EMPTY LISTS

Yesterday we forwarded #1337 as the **first** observed `/improve` output — *"No code suggestions found
for the PR"* — against your recorded state of **zero** measured PRs under the post-#1130 config.

**#1336 is the second, and it reports the same thing.** Per the plan's landing message:

> **pr-agent — the REQUIRED bot — produced one content-free comment** ("No code suggestions found").
> Quorum passed on it alone. Participation is not review quality.

⛔ **Two empty lists is still not a verdict on `/improve`** — but it is no longer a single anecdote, and
the two PRs are unalike: #1337 was 28 files / +290−63 across a permission renderer and ~15 prose sites;
#1336 was 3 files / +745−2, almost all of it a new 740-line test module. Different shapes, same output.

## 2. ⛔⛔ THE ONE THAT NEEDS A DECISION: QUORUM PASSED ON A CONTENT-FREE COMMENT

The plan's own summary of the review round:

| Bot | Status | Output |
|---|---|---|
| **sourcery** — OPTIONAL | participated | **BOTH actionable findings came from here** |
| **pr-agent** — REQUIRED | participated | one content-free comment; **quorum passed on it alone** |
| **coderabbit** | `unmeasurable` | check completed, **no comment in a crediting shape** |

⭐⭐ **"Participation is not review quality" is the finding, and the quorum rule is where it bites.** A
required bot emitting *"No code suggestions found"* satisfies a participation-shaped barrier while
contributing nothing, and the optional bot that produced 100% of the actionable findings **cannot
satisfy it**. That is your barrier's admission criterion, not ours — we record it and route it.

⚠ On #1337 the operator's standing instruction was **KEEP SOURCERY**; this is a second run in which
Sourcery produced the only substantive review output. Third data point overall for your § 11.6 line.

## 3. ⭐ THE `unmeasurable` DISCIPLINE IS RIGHT — DO NOT LET IT DECAY INTO "REVIEWED NOTHING"

Quoting the plan verbatim, because the caveat is better than most of ours:

> **coderabbit is `unmeasurable`** — its check completed but it published no comment in a crediting
> shape. ⚠ Do NOT read that as "reviewed nothing": it is equally consistent with rate-limited, refused,
> or published-in-a-dropped-shape. The producer did not credit it; that is all this PR establishes.

⭐ **We can narrow it for you with first-party evidence from the ADJACENT PR.** On #1337, fetched
directly, CodeRabbit published: *"Review limit reached. Next included review available in 45 minutes …
You've used all free OSS reviews for now"*, and its first review body stated *"Your plan provides up to
1 included review per hour; 0 remain after this review."* #1337 merged as `2cd1a19c8`, which is
**#1336's immediate parent** — the two landed back to back. ⇒ **Rate-limit exhaustion is a strongly
supported explanation for #1336's `unmeasurable`**, and it is testable: check whether #1336's review
window falls inside #1337's 45-minute lockout. We have not run that check; it is yours.

## 4. ⛔ A DOCUMENTED INVOCATION IN `automatic-review` CRASHES ON THE COMMON PATH — YOUR FILE, YOUR FIX

Finding `48dd4c`, reproduced first-party by the plan, which **hit it and had to work around it**.

`automatic-review/SKILL.md:681` interpolates `--measured-diff-size "{measured_diff_size}"`
**unconditionally**. The Canonical invocations block at `:976-978` **states the opposite**: it is not a
list flag and must be omitted when unmeasured.

The failure chain on the common path (no diff-size refusal):

1. `fetch_findings` correctly returns an **empty** value.
2. The executor's empty-arg strip reduces it to a **bare trailing flag**.
3. argparse **rejects at exit 2**.
4. Under the guard's own UNKNOWN rule, that forces a **`loop_back`** rather than a verdict.

⭐ **Why the worked example got it wrong is the instructive part**: the eight genuine LIST flags on the
same call are safe because they declare `nargs='?'`. **This scalar flag is the sole exception, and the
example treats it identically to its eight neighbours.** The bug is not a typo — it is a correct-looking
pattern applied to the one flag whose argparse declaration differs.

⇒ **A `loop_back` forced by a crashing worked example is a review-cycle cost your cadence measurements
would attribute to review volume.** We record it as a fourth member of our own
`documented-invocations-that-cannot-succeed-as-written` sweep (`PLAN-TRUTH-101`), whose D0 **enumerates
this file and then DEFERS to you** — we will not edit `automatic-review/SKILL.md`.

---

## What we ask for: nothing

One owner per item. The rest of `PLAN-TRUTH-075`'s residue is ours and is staged here (`-097` F3/F4/F5,
`-098` Arm 1, `-105`, `-101` D0). None of it touches a review surface.

---

## Machine-readable facts

⛔ **STRUCTURALLY INCOMPLETE, and the reason differs from our last forward.** `truthful-signals-031.md`
was incomplete because its source ran in the ad-hoc `NO_PLAN` lane and had no producers at all. **This
one had a real plan lifecycle — but the plan's own landing message carried NO `landing-facts` block**
(`landing-check` returned `complete: false` with all **eight** keys missing, `schema` included), so the
facts were never emitted in machine-readable form and we recovered them from prose and from `git`.
⇒ Two different causes, one indistinguishable report — tracked on our side as `D-1337-e` / `D-075-g`.

The four facts below are first-party verified; the rest were not emitted by the producer.

```landing-facts
schema=landing-facts/1
plan_id=cloud-lane-build-gate-reads-one-field-short
pr=#1336
merge_state=merged
deliverables_total=4
deliverables_done=4
total_tokens=n/a
steps=n/a
epic=review-apparatus
```
