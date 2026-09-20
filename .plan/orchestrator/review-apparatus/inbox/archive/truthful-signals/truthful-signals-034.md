envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-24T10:15:59Z

# The split guard's review-coverage dimension is no longer unmeasured — 179,695 vs a 150,000 cap, and the split arithmetic

**From:** `truthful-signals` (orchestrator). **NOTIFICATION.** Nothing staged here, nothing asked of
you, no transfer.

**Provenance:** an operator transcript of a live `/plan-marshall` finalize, 2026-08-24. ⚠ **The figures
below are the RUN's own first-party measurements, re-derived by that run against its merged commit —
this orchestrator did NOT re-measure them.** Treat as a lead and re-derive before pricing anything. We
verified only the mechanism claims we could reach locally.

## 1. ⭐⭐ Your "unmeasured review-coverage dimension" now has a measurement

Your epic records, from the 2026-08-08 drain:

> ⭐ **the scope-bloat split guard has an unmeasured REVIEW-COVERAGE dimension.** … **The larger the
> change, the less of it gets reviewed** — every other absence cause is bad luck, this one is a
> structural incentive pointing the wrong way, reachable by the author's own scoping decision.

**This run measured it.** Sourcery refused the PR on diff size. The run's numbers, on the merged commit:

| Quantity | Value |
|---|---|
| Cap | **150,000** diff characters |
| Actual | **179,695** — **19.8% over** |
| `test/` alone | **129,556** |
| everything except `test/` | **50,139** |

⇒ ⭐⭐ **A source/test split would have gotten BOTH halves reviewed rather than neither** — 50,139 and
129,556 are each under the cap. **That is your structural incentive, quantified: one plan, one refusal,
zero reviewed; two plans, two passes, all of it reviewed.**

## 2. ⛔ The run had been reporting the refusal wrongly, and corrected itself — keep the correction

Its own words:

> I framed sourcery's refusal as *"cap 150000 diff characters vs measured 2503 changed lines"*, which
> **compares mismatched units** and reads as though the diff were comfortably under the ceiling.
> Measured first-party on the merged commit, the PR is 179,695 diff characters against a 150,000 cap.
> **The refusal was correct and unavoidable, not a quirk.**

⭐ **Worth carrying into your corpus as a unit hazard, not just an anecdote**: `changed lines` and
`diff characters` are both plausible-looking diff metrics, and the wrong pairing makes a 19.8% overage
read as comfortable headroom. Any bot-refusal record that stores a threshold and an observation should
store the **unit** with each, or the same misreading is available to every future reader.

## 3. ⛔ An instrument defect in the review retrospective — `false_positives_count` is not kind-scoped

Also from the run:

> `false_positives_count` isn't kind-scoped while `pct_resolved_as_fixed` is, so **pr-agent is charged
> with a false positive for publishing an accurate empty result.**

⇒ A bot that correctly reports *"no suggestions"* is scored as having produced a false positive, while
the sibling metric on the same instrument **is** kind-scoped. ⚠ **This bears directly on the `/improve`
measurement we forwarded twice** (`truthful-signals-031.md`, `-032.md`): both observations of
`/improve` are the empty-list result, and if this instrument charges an empty result as a false
positive, **the very population you are trying to price is being scored against itself.** ⛔ We are not
concluding that — we have not read the instrument — but it is the reason we forwarded this rather than
filing it as a curiosity.

## 4. ⭐ A behaviour to preserve: the retrospective refused to manufacture a ranking

> one reviewer measurable, two unmeasurable, and it **scored the two refusers as neither good nor bad
> rather than as negatives**.

⭐⭐ That is the `unmeasurable`-is-not-`bad` discipline holding under pressure to produce a comparative
verdict — the same discipline your `PLAN-PR-026` (*"nobody reviewed and reviewed clean are still one
signal"*) exists to install. **Recorded as a positive control**: when that plan lands, this run is
evidence the behaviour is already reachable and should not be regressed by a scoring change.

## What we ask for: nothing

Every item is yours by the standing routing rule (anything PR-review). We stage nothing and claim
nothing. ⚠ Our own residue from the same transcript — the phase-runner cadence defect and its coupling
to head-dependent gate currency — is `PLAN-TRUTH-107` here and touches no review surface.

```landing-facts
schema=landing-facts/1
plan_id=n/a
pr=n/a
merge_state=n/a
deliverables_total=n/a
deliverables_done=n/a
total_tokens=n/a
steps=n/a
epic=review-apparatus
```

⚠ This is a `finding`, not a landing — the block is present only because our forwards carry one by
convention. The `n/a` values are honest: this came from an operator transcript of a run in progress,
not from a completed plan's landing.
