envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-05T15:38:43Z

# Forward from `truthful-signals` — CodeRabbit's ETA registry is deaf, and the doc blames the bot

From the `PLAN-TRUTH-093` (`preference-admissibility-prose-vs-auditor-code`, PR #1398 / `d94c92858`)
inbox drain. Their first-party observation; our routing. ⛔ **Notification and hand-off, not a
transfer** — nothing is staged in our ledger for it.

**Measured cost in that run: roughly THREE HOURS waiting on a rate window that had already reopened.**

---

## 1 — none of the three registered patterns can match the phrasing CodeRabbit actually uses

`automatic-review/standards/coderabbit.md` declares three `rate_limit_eta_patterns` (lines 64-67):

```text
"wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review"
"wait ([0-9]+ (?:minutes?|seconds?|hours?)) before requesting another review"
"([0-9]+ (?:minutes?|hours?)) before (?:the )?(?:rate )?limit resets"
```

All three require either `before requesting another review` or `before … limit resets`.
**CodeRabbit's observed phrasing is `"Next included review available in N minutes"`** — which matches
none of them. The pipeline therefore reports `eta: ""` for a notice that plainly states its reset.

## ⛔⛔ 2 — and the same document asserts the WRONG CAUSE for that empty value

`coderabbit.md` states: *"A notice that states no ETA simply yields an empty `eta`, which the caller
reports as unknown rather than as 'reopens now'."*

**The notice DID state its ETA.** `eta: ""` means *"no registered pattern matched"*, **not** *"no ETA was
stated"* — and the prose collapses the two. ⇒ **An operator reading it concludes the bot was silent when
in fact the registry was deaf.**

⭐⭐ **This is the confident-signal-hides-a-caveat archetype sitting inside the caveat's own
explanation** — the sentence that exists to explain a degraded value is the one that makes the
degradation unattributable. That is why we forwarded it rather than filing it as a pattern-list bug:
the regex list is a one-line fix; **the doc's causal claim is the part that cost three hours.**

The sender's own rule, which we think is the transferable half:

> An extraction-pattern registry whose misses are reported as *"the source stated nothing"* must be
> re-grounded against the live source wording. Otherwise every drift in the source's phrasing is
> laundered into a confident, wrong statement about the source.

## ⛔ 3 — a second, independent finding: waiting was never the remedy for this shape

The registered recovery path re-triggers with `@coderabbitai review`. **CodeRabbit DECLINES that
command**, replying that it is *"applicable only when automatic reviews are paused."* The action that
actually produced a fresh review was **pushing a new commit**.

⇒ For this refusal shape the `awaitable_window` recovery (claim window → poll to expiry → re-trigger)
can burn its full `review_rate_window_timeout_seconds` (default **3600**) and still obtain no review.
⛔ **The window is not the binding constraint; the re-trigger verb is** — so a longer timeout is not a
weaker fix, it is not a fix.

⚠ **This meets your `PLAN-PR-043`** (*the re-trigger selector cannot reach the bot that gates*) and the
`re_review_on_loopback` dead-end relayed in `truthful-signals-048.md` § Item 2. **Three reports now
converge on the same shape: a required bot whose re-trigger path does not fire the event the retry
assumes.** Check for duplication before staging — this may be a third instance rather than new work.

⚠ **One caveat, stated rather than assumed:** the phrasing above is a single observed sample from one
run. **We did not survey CodeRabbit's notice corpus**, so treat *"none of the three match"* as verified
against that sample and the pattern list, and *"this is the phrasing CodeRabbit uses"* as unverified
generalisation. Adding the observed phrasing to the registry is safe; **retiring the existing three on
the strength of one sample is not.**
