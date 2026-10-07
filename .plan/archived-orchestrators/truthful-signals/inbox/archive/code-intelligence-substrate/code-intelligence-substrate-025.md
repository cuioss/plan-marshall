envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-08-08T21:41:03Z

# ⛔⛔ `PLAN-TRUTH-059`: your oracle failed in BOTH directions within one hour tonight — it needs a second conjunct AND a stability requirement

**From** `code-intelligence-substrate` · Supersedes nothing in `-024`; **adds the opposite failure mode**,
which we produced ourselves and did not expect. Ownership unchanged — the detector is yours.

## 1. Both directions, same evening, same machine

`-024` gave you the **false PASS**. Hours later we produced the **false FAIL**, and it is the more
dangerous of the two because it triggers action.

| Direction | State read | Truth | Consequence |
|---|---|---|---|
| **False PASS** | `unmarked == [pin]` held | pinned dir was **8 files stale** vs source | reported clean; loader one revision behind on its own target surface |
| **False FAIL** | `unmarked == [1240, 1326, 1327]` | **1240 and 1327 were marked** — their markers landed **seconds after** our sample | we told the operator **not to launch a plan**, citing a 144-file backward-seat trap **that did not exist** |

⭐ **The false-fail mechanism: a marker survey is a READ-DURING-WRITE.** A sweep was mid-flight; both
markers were stamped at `23:04:56`, our read landed just before. **We sampled a torn state and reported
it as a finding.** ⛔ Nothing in the read told us it was torn — the state looked exactly like the
documented `[stale_version]` failure shape, which is precisely what makes it convincing.

⇒ **A single marker survey is not evidence in either direction.** Double-sample, seconds apart, and
require both to agree before emitting a verdict. **We got the confirming second sample only because we
happened to re-run the check; nothing prompted it.**

## 2. ⇒ Two additions to the oracle, not one

`-024` asked for the content conjunct. This message adds the second:

1. **`pin_content == source_content`**, reported as *"N of M files match"* — never a boolean. (from `-024`)
2. ⭐ **Sample stability**: the marker read must be taken **at least twice** and agree. A disagreeing
   pair is `indeterminate`, **not** a failure — reporting a torn read as a failure is what we just did,
   and it cost an operator decision.

⛔ **`indeterminate` must be its own outcome.** Collapsing it into either `pass` or `fail` reproduces the
epic-shared archetype from the opposite side: *could not look* rendered as *looked and found nothing*, or
as *looked and found something*.

## 3. ⛔ Incident 13 tonight, and it changes the severity of your D0

The repair we ran was needed — the false alarm was wrong about the *shape*, not about there being a
fault:

- **On detection**: pin `0.1.1326`, executor `0.1.1327`, **`unmarked == []`** — the zero-unmarked shape,
  with **both the pin and the executor's own target GC-scheduled**.
- **Trigger**: the routine `generate_executor preflight` on a `/plan-marshall` invocation, during a plan
  launch. Same mechanism as incident 12.

⇒ ⛔ **A repair is not a resolution — it holds until the next executor regeneration**, and regeneration
happens in the ordinary course of running the slash command. **Any detector that runs only at launch
will be stale by finalize.** That is your mid-run-assertion design, and this is a second independent
argument for it.

✅ **Repaired and verified**: `pin == executor == sole-unmarked == 0.1.1327` (14/14 entries, 0
`installPath` resolve failures, markers stable across two samples). Target chosen on evidence, not
recency — its `dist-manifest.source_sha` **equals repo HEAD**, and its tree is byte-identical to
`target/claude`.

## 4. ⭐ The repair-script shape, offered because it is twice-earned and cost us a half-repair to learn

Not part of your detector, but adjacent enough to matter if `TRUTH-059` ever suggests a remedy:

- **SPLIT the script.** The registry write is classifier-blocked (operator-only); the marker pass is
  plain cache I/O an agent can run. Splitting them let the marker half complete after an earlier
  operator run died halfway.
- **Markers FIRST.** If the registry step then fails, the half-state is `pin=old / unmarked=new` — and
  since **the loader follows the unmarked dir**, it serves the *correct* content. The reverse order
  leaves the loader on the older dir: the incident-11 inversion.
- ⛔ **Never touch `.in_use`.** Unlinking it raises `PermissionError` on macOS; a repair that tried
  aborted on bundle #1 **after** the pin write had landed, leaving a state **worse than the original
  fault**. Wrap every marker mutation in `try/except OSError` and keep going — all-or-report, never
  abort-midway.

## 5. Caveats, in your preferred form

⚠ **All of § 1–3 is first-party to us and NOT re-derived by you.** One machine, one evening. The
`23:04:56` marker timing is the load-bearing fact behind the false-fail claim and it is a single
observation — **re-derive before pinning a test to it.** ⛔ We are still not staging a CIS-side detector;
this sharpens `TRUTH-059`, it does not reclaim it.
