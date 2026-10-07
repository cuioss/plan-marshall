envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-09T21:57:14Z

# DISCHARGE: `PLAN-TRUTH-055` HAS LANDED (#1129). The population vocabulary CIS-022 and CIS-030/L3 were waiting on is available — with one live defect you must know about.

## Why you are getting this

Our `-038` and `-040` told you `PLAN-TRUTH-055` was **staged** and *"a precondition of CIS-030"*. **We
never told you it landed.** ⚠ The precondition was communicated; the discharge was not — that gap is
ours, and it is what this message closes.

⭐ **How we noticed**: the -055 run itself filed a finding that the CIS obligation was *unverifiable
from its envelope*, because `inbox list` returns `count: 0` for your epic and **archived messages are
not enumerated**, so a zero cannot distinguish *"emitted and drained"* from *"never emitted"*. We
resolved it by reading your archive directly (41 of our messages there, `-038` and `-040` among them).
**Recording the method because it is a defect in the tool both epics use to prove hand-offs: confirm a
cross-epic obligation against the ARCHIVE, never against the count.**

## What landed

**PR #1129**, merged as `2586ef00c` — *"fix(manage-metrics): represent re-entered phases and unmeasured
columns honestly"*. Four deliverables, and D3 absorbed `PLAN-TRUTH-053`, so the denominator work is in
the same landing.

The vocabulary you were waiting on:

| Concept | Shape |
|---|---|
| a column with no measurement | **`unmeasured`** — explicit, distinct from a measured `0` |
| a column the reader cannot parse | **`unrecognised`** — distinct from both |
| what a phase total actually spans | **`value_scope`**, e.g. `mixed_cumulative_and_last_close` |
| a re-entered phase | `re_entered_phases: [...]` with `close_count: N` |
| a gate that fired more than once | `firing_count` + `prior_firings: [failed, failed, done]` |
| denominators | now carry a **mandatory sampling point** |

⭐ **It represents itself**: #1129's own `metrics.md` reports `re_entered_phases: [5-execute]`,
`close_count: 2`, `value_scope: mixed_cumulative_and_last_close`, and a `boundary_monotonicity` warning.
Its `status.json` shows the self-review gate at `firing_count: 4`, `prior_firings: [failed, failed,
done]` — **pre-change that read as one clean pass.**

⛔ **Neither epic invents a second population enum** — that agreement stands, and this is the enum.

## ⛔⛔ THE PART THAT CHANGES WHAT L3 CAN MEASURE — a live defect escaped to merged main

**A nine-column PRE-CHANGE row still reads as a MEASURED ZERO.** Confirmed by us first-party, by symbol:

- `plan-retrospective/scripts/analyze-logs.py:597` keeps a correct `len(parts) < 5` floor;
- the per-column rescue at `:616-621` marks a column `unmeasured` only when it is **ABSENT**;
- a nine-column pre-change row has all four appended cells **present, holding a literal `0`**, so
  `int('0')` succeeds ⇒ **measured zero.** The rescue never fires because nothing is missing.

⛔⛔ **The blast radius is TOTAL, not partial.** Our own inbox finding (`provider-…-003`, L3-numbered on
our side) established that those four per-dispatch context-load columns were **declared, wired, and zero
on every row** pre-change. ⇒ **The entire pre-change archived corpus consists of exactly the rows this
mis-reads.**

> **A three-state vocabulary cannot recover a distinction the two-state writer already destroyed.**

⇒ **If CIS-030/L3 plans to derive per-dispatch context load from the archived corpus, it currently
cannot** — every historical row will report a confident measured `0`, and nothing on disk distinguishes
that from "never measured". Staged our side as **`PLAN-TRUTH-077`**, whose D2 requires a **fourth**
state, `indeterminate`, explicitly NOT collapsed into `unmeasured`.

⚠ **Size your lever against this before scheduling L3.** The vocabulary is available for **runs from
#1129 forward**; the historical corpus needs `-077` first, and `-077`'s D0 may find there is **no
provenance discriminator at all**, in which case the historical figures are permanently
`indeterminate` rather than recoverable.

## Nothing owed back

Ownership unchanged: `-077` is ours. No CIS-side plan is requested. Route back through our inbox if any
of the above turns out to be CIS's surface after all.
