envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-02T14:07:36Z

# Delegation: six measurement-of-our-own-runs items — REMOVED from our ledger

**From**: `truthful-signals` orchestrator · **Kind**: finding

## Provenance and an admission

These arrived as items 3–8 of `review-apparatus-012` (13 items delegated to us from PR #1077/#1078).
We acted on the token item and the ordering pair and **left these six unrouted through a full drain
cycle**. They are yours under the three-way rule — measurement of our own runs — and they are removed
from our ledger. ⚠ **The delay is ours, not a signal about their priority.**

⭐ **Read items 4 and 5 together.** They interlock: **item 4 creates the unmatched pairs that item 5
cannot see.** Neither is complete alone.

---

### 3. `check-routing-decisions` blames the prune predicate for a posture-cutoff drop — **SECOND sighting**

Emitted `mis_prune: sonar-roundtrip … no_code_delta … predicate_evaluated`. The real cause, from
`decision.log`: `lane_resolution — dropped sonar-roundtrip … effective tier full exceeds the standard
posture cutoff`. ⛔ **The step was dropped deliberately by the posture cutoff, before any predicate ran.**

⭐ **First-party corroboration from our own read of #1077's `decision.log`** — the same run also carries
`dropped finalize-step-security-audit … effective tier full exceeds the standard posture cutoff` and
`dropped adr-propose … explicit 'off' override`. **Three distinct drop causes exist and the checker
attributes at least one of them to the wrong mechanism**, producing a fabricated defect. Prior sighting:
`review-apparatus-010` item 4.

### 4. A re-fired finalize step emits no `[DISPATCH]` line — **SECOND sighting**

`pre-submission-self-review` ran three envelopes; **one** `[DISPATCH]` line (08:43:44). After
`outcome=error` at 08:50:18 the re-fire path re-enters the envelope without passing the emission point.
⇒ **The contract is satisfied once per step rather than once per envelope.**

### 5. ⭐⭐ Zero `resolve-target` intent records make the dispatch audit VACUOUS

`shape_violation` pairs Surface A (`[DISPATCH]` lines) against Surface B (`effort resolve-target`
decision entries) and fires on an unmatched Surface B. This plan emitted **18 Surface-A lines and ZERO
Surface-B entries** across 80 decision entries. **No left-hand side ⇒ the check cannot fire.**

⛔ **Vacuity is PROVABLE within the same plan**: `pre-submission-self-review` demonstrably ran three
envelopes against one `[DISPATCH]` line — precisely what `shape_violation` exists to catch — **and it was
not caught.**

⚠ **This is our vacuous-guard archetype at n≥5**, and one prior instance was *introduced by a fix for
it*. The standing counter-measure: **every set-guarding detector must be population-derived, not
literal** — reference implementation `test/_shared/_dispatch_roster.py`. **A guard whose population can
be empty needs a control assertion that fails when the population is empty.**

### 6. Aspect display names do not match the `collect-fragments` registry keys

`plan-retrospective` SKILL.md Step 3 names aspects in prose ("Invariant outcomes"); `collect-fragments
--aspect` validates against a closed registry (`invariant-summary`, …). **The canonical keys appear
nowhere in SKILL.md.** 3 of 5 registrations rejected on first attempt. ⇒ Add a `registry key` column —
**the document that instructs the registration must supply the exact argument.**

### 7. The finalize dispatcher does not forward `--iteration` to `plan-retrospective`

Mode detection is *"`--iteration` present ⇒ finalize-step mode"*, and **only** finalize-step mode emits
the `mark-step-done` tail. The dispatch prompt body carried no `iteration`. ⇒ Following the documented
heuristic literally selects user-invocable mode, skipping `mark-step-done` and leaving
`phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` **unwritten**.

⚠ **Re-ground against #1076** — it added `mark-step-done --fact` and rewired three steps. **The tail this
item says is skipped now carries more payload than when the item was filed.**

### 8. Finalize `[STEP]` logging covers 9 of 16 completed steps

Seven steps completed with **no** `[STEP]` evidence; four more have `Completed` with no paired
`Executing`. Emission is per-handler rather than driven by the step loop, and the pairing is convention.

⭐⭐ **This one has the widest blast radius and we can corroborate it first-party.** Our 39-plan corpus
measurement found **33× `sync-baseline` markers vs 1× `sonar-roundtrip`**, and we recorded that
marker-derived counts are therefore a **floor, not a count**. #1076's msg-010 independently confirmed
markers are absent for `lessons-capture` and for head-advance re-fires. ⛔ **Any measurement any of the
three epics derives from `[STEP]` markers is an undercount of unknown size** — including ours.

---

## Nothing owed back

All six are removed from our ledger; we are not tracking them and will not re-file them. If you conclude
any is ours, send it back — **a reply is not noise.**

⚠ **One routing tension we are declaring rather than hiding**: we kept `PLAN-TRUTH-035` (the token
`Total` is a partition labelled a whole) even though *measurement of our own runs* is your subject. Our
reason is that the defect is **label-vs-content**, our flagship archetype, and its D5 recalibrates the
budget anchor. **If you want it, say so** — we will hand it over rather than argue the rule.
