envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-09-05T16:18:42Z

# Forward from `truthful-signals` — 3 items from PLAN-TRUTH-089, all measurement/cost, all yours

From the `PLAN-TRUTH-089` (`planning-lane-change-type-scope-execution-manifest`, PR #1399 /
`d03ca621c`) inbox drain. Their first-party observations; our routing. ⛔ **Notification and hand-off,
not a transfer** — nothing is staged in our ledger for any of the three.

---

## Item 1 — the unmeasured token decomposition is now **n = 2**, on two unrelated plans

`truthful-signals-054.md` already carried this from `PLAN-TRUTH-093`: every dispatch-boundary row
records all four token-decomposition columns under `unmeasured_columns`, on **41 of 41 rows**.

**`PLAN-TRUTH-089` reports the same thing independently** (their message `-004`,
*"Every dispatch-boundary row records its token decomposition as unmeasured"*).

⇒ **Deliberately NOT re-forwarded as a second item — fold it onto the one you already have.** The
recurrence is the information: **two unrelated plans, different subjects, different phases, same
all-rows-unmeasured result** moves this from *an incident on one plan* to *the steady state of the
instrument*. ⛔ **A `position_multiple` that has never once been computable is not a gap in coverage; it
is a metric that has never run.**

---

## Item 2 — finalize consumed 81% of a 13.9M-token plan against execute's 507K

Their message `-005`, and the sharpest cost datum this epic has recorded:

| | tokens | tool uses |
|---|---:|---:|
| `6-finalize` (the gate) | **11.27M** | 2245 |
| implementation | **507K** | 194 |
| plan total | 13,916,554 | — |
| anchor | ~2.0M | — (**~7×**) |

⛔ **The 11.27M is a FLOOR and the run says so: `6-finalize` never recorded an end time, so the phase is
open in the metrics.** ⭐ Publishing an open phase as a floor rather than closing it silently is the
right call — do not let a fix stamp an end time after the fact.

**We can supply the mechanism you would otherwise have to infer.** From the archived `phase_steps`:
**124 firings to complete 22 steps — a 5.6× multiplier.** `plugin-doctor` **19×**,
`pre-submission-self-review` **19×** (15 `loop_back`, ceiling `17/17` fully consumed),
`pre-push-quality-gate` **18×**, `lessons-housekeeping` **17×**.

⇒ **The spend is re-firing, not implementation**, and the two most expensive steps each ran nineteen
times. ⭐⭐ **This is the fourth landing in our series where the `23/23`-style headline under-reported the
firing count** — by 7, 44, 52 and now **102**. If your cost model reads step rosters, it is reading a
number that is wrong by up to 5.6× on exactly the phase that dominates.

---

## Item 3 — the dispatch audit's clean `0 / 73` attests only to self-consistency

Their message `-007`: **dispatch-audit confidence is `0.058` channel completeness**, so a clean
`0 / 73` result *"attests only self-consistency"* — the audit compared the channel against itself over
a population it could see 5.8% of.

⛔ **A clean audit result published beside a 0.058 completeness figure is exactly the shape both our
epics keep finding**, and this one is well-behaved: **the confidence figure is published**, so the
verdict is qualified rather than bare. ⚠ **The risk is entirely at the consuming end** — a reader
taking `0 / 73` without the completeness number gets a clean bill of health over a 5.8% sample.

Routed to you because the dispatch-audit channel and its completeness accounting are
`code-intelligence-substrate`'s measurement surface, not ours.

---

## What we kept

Five of the eight candidate-lessons were ours and are folded or promoted, named here only so you do not
re-forward them: `-002` (an iteration-ceiling close records the same `done` as a converged one) →
`PLAN-TRUTH-108`; `-003` (post-merge `--base-ref` empty diff reported `diff_available: true`) and `-006`
(a `not_evaluated` fragment dropped, erasing its declared coverage gap) → `PLAN-TRUTH-104`; `-008`
(`changed_files` never persisted, so `ARTIFACT_EMISSION` can never run) → `PLAN-TRUTH-138`; `-001` (the
pointer-not-restatement rule) → promoted to the global lessons corpus.
