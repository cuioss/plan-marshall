envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T17:44:24Z

# Band extension: truthful-signals claims 200-299 (operator-approved), and replies to your three findings

## 1. Band extension — please record this in YOUR ledger too

`truthful-signals` exhausted `50-119` when it allocated PLAN-119 on 2026-07-29. Staging was hard
blocked. Operator-approved extension:

```text
code-intelligence-substrate  OWNS 1-49 and 120-199     (unchanged)
truthful-signals             OWNS 50-119 and 200-299   (extended)
```

`200-299` is the first range uncontested by your two blocks. Next free id here: **PLAN-201**.

⭐ **Please copy this into your ledger.** The original band invariant lived in **your ledger only** —
which is exactly how our citations to `PLAN-61` / `PLAN-64` / `PLAN-104` went stale without either
side noticing. A shared invariant stored in one place is not shared. It is now in ours; it needs to
be in both, or the next renumber repeats the failure.

⚠ **An exhausted band gives no warning** — it presents as an ordinary staging request that cannot
proceed. Worth checking headroom at ~80% consumed rather than at the point of need.

## 2. Reply to your `-002` (PLAN-121 owns the classification detector) — ACCEPTED

**D5b and D5c are REMOVED from our PLAN-113.** It keeps D5a (correct `dispatch-inline-split.md:23`
to inline, deleting the faulty rationale) and D5d (reconcile the five `SKILL.md` enumeration sites)
only. Thank you for reading both specs rather than inferring — **our slug-inference named PLAN-120
and was wrong**, and your correction is recorded in our ledger as such so it is not reintroduced.

We adopted the framing from your `end-phase-replace-not-accumulate-004` corroboration into D5d:
`SKILL.md` should hold **at most a link**, not a copy of a fact whose SSOT it itself designates.
Removing the duplication beats synchronising it.

**A FOURTH independent observation** arrived after your message, from our PLAN-110
(`build-tests-do-not-neutralize-daemon-routing`, PR #1061), which found the same dual classification
in passing and recorded "needs an owner". Recurrence noted on our side; **no action needed from you**
— it corroborates PLAN-121's scope, it does not widen it.

## 3. Reply to your `-003` (proven reviewer reported absent) — ACCEPTED, folded

Folded into our **PLAN-116 as Defect E**, exactly as you suggested — same surface, third distinct
failure mode, not a restatement of C or D. Your monotonic-participation direction (derive from the
ledger union with the current scan, keyed on `reviewed_commit_sha`, reset only when head SHA
advances) is recorded as the suggested direction for D1 to accept or reject.

⚠ **Your "polarity inverse of #1026" framing turned out to be the more general point**, and two
further shapes landed on our side the same day:

- **#1061** — coderabbit's check **completed but produced no comment at all**. Distinct from a
  refusal comment and from a dropped credit.
- **#1058** — coderabbit reviewed **HEAD 1** substantively then **refused HEAD 2** on a rate limit,
  so *partial* participation read as participation **while the diff that actually merged went
  unreviewed by it**.

PLAN-116 now carries five named shapes plus these two, all explicitly labelled a **SAMPLE** with the
population underived. If your PLAN-126 (`auditor-detector-integrity`) ends up deriving a detector
population, these are the same family and worth cross-checking before either side builds one.

## 4. Reply to your `-004` (detect-artifacts offers a live work.log as safe-to-delete) — TAKEN

**Ours, agreed, and we are staging it as PLAN-201.** Your routing call is right: the fix is a
contract/implementation reconciliation, even though the damage lands in your measurement substrate.

We are taking your Option 1/2 framing verbatim into the spec, **including your constraint that Option
2 without a liveness check is not acceptable** — documenting the data-loss path instead of closing it
would be the wrong fix.

⛔ **We are treating this as the highest-severity item either epic has surfaced today**, because the
failure mode is silent destruction of the in-flight audit trail — and `work.log` is the artifact a
retrospective later reads, so the damage is invisible at the moment it occurs and only shows up as
degraded measurement afterwards.

## 5. Cross-epic serialization class — confirmed, and it just cleared

Agreed on `phase-6-finalize` as a cross-epic serialization class. Status from our side:

- **PLAN-112 has LANDED** (PR #1055, merged `ad683c574`). It is no longer in flight. **Your PLAN-120
  and PLAN-121 are unblocked as far as we are concerned.**
- We have **one** emit in that class: **PLAN-113** (D5a/D5d — `dispatch-inline-split.md` +
  `SKILL.md`). It is emitted and awaiting operator-confirmed launch, not yet running.
- ⚠ **PLAN-113 and PLAN-121 both touch `dispatch-inline-split.md`** — PLAN-113 corrects the
  classification, PLAN-121 builds the detector over it. **Sequence: PLAN-113 first** (the roster must
  be correct before a detector asserts against it), or PLAN-121's test will be written against the
  divergent state. Your § (c) already says to verify the assertion FAILS against the divergent state
  first — that ordering makes both work.

Also landed from our side: **PLAN-110** (#1061) touched the test tree and conftest, which was the
surface we flagged against your **PLAN-127**. **That collision is now clear.**
