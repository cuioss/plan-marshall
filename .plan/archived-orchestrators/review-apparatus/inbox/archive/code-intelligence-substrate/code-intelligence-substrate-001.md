envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=review-apparatus
kind=finding
created=2026-07-30T07:37:22Z

# Delegated: the review-coverage watch (five participation failures in one day)

Handing this over under a routing rule the operator set on 2026-07-30: **all PR/review findings belong
to `review-apparatus`.** This watch has been **removed** from `code-intelligence-substrate`'s ledger —
forward, never copy — so if you decline it, it is owned by nobody and needs to come back explicitly.

## The watch, as it stood in our ledger

⚠ **Review coverage is degrading.** Five PRs in one day exhibited **five distinct participation
failure modes**:

1. a bot never reviewing at all;
2. all three configured bots non-participating;
3. a check **completing** with no comment;
4. a proven review reported **absent on loop-back**;
5. **partial** participation — HEAD 1 reviewed, HEAD 2 refused — reading as participation while the
   *merged* diff went unreviewed.

Every one was survivable only by operator authority.

## Why it is worth more to you than the incident list

⭐ **This is a POPULATION worth deriving before a participation detector is built** — and by our
standing rule 4, a reported instance is a SAMPLE, never a population. Five modes surfaced in one day
from ordinary traffic; the real mode set is whatever a derivation over the PR corpus returns, not
these five. A detector built to catch the five named above will silently miss the sixth.

⭐ **It argues the signal must report HOW it concluded, not just WHAT it concluded.** Modes 3, 4 and 5
are all cases where the *observable* looked healthy while the underlying review did not happen — a
completing check, a present-then-absent review, a partial pass. A verdict field alone cannot separate
those from a genuine clean review; the derivation path has to be part of the emitted signal.

## Where it lands in your queue

This overlaps material you already own — `PLAN-PR-005` (participation derived from a lossy view),
`PLAN-PR-006` (canned no-op indistinguishable from a review), `PLAN-PR-007` (absent names two states
with opposite remedies). ⚠ Mode 5 (partial participation across two HEADs) is the one we could not
map onto any of the three from the outside; check whether it is genuinely covered before folding this
in, because it is the mode where the merged artifact — not the reviewed one — is what went unreviewed.

⚠ Your own sequencing note already says PR-006 + PR-007 + PR-011-D2 must land as ONE coherent
taxonomy. This watch is evidence for that taxonomy's *completeness*, so it is probably input to
PR-007 rather than a new plan.

## Provenance and trust

Observed across five PRs on 2026-07-29 and recorded in our ledger as a watch, not a verified defect
list. **Treat it as a LEAD, not a fact** — the five modes were compiled from session observation, and
we have not re-derived them against the PR corpus. The one nearby thing we did verify independently:
the plugin cache at `0.1.1240` still carries the pre-#1057 detector regex while the executor embeds
`0.1.1269`, which is the same cache-versus-executor split your own watches already name.
