envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:35:07Z

component=plan-marshall:marshall-orchestrator
category=anti-pattern
title=A could-not-look discriminator observed AFTER the scan it describes reproduces the very defect it fixes

# A could-not-look discriminator observed AFTER the scan it describes reproduces the very defect it fixes

⭐ **The epic's own theme reproduced itself inside the fix for that theme.** Caught by CodeRabbit on
PR #1064, remediated in-run.

## What happened

PLAN-203's D2 added an `inbox_state` discriminator to `inbox list` so a zero meaning *"could not
look"* stops sharing a representation with a zero meaning *"looked, found nothing"*. The
implementation evaluated `inbox_dir.is_dir()` **at return time**, while the `count` came from the
**earlier** `list_messages()` scan.

Two observations of the same predicate at two different instants. Under the concurrent writer/drain
this very module explicitly designs for (it has an `unreadable` code precisely for a file vanishing
mid-drain), a directory removed after enumeration yields:

```
count: 3
inbox_state: missing
```

— **"could not look" asserted about a scan that did look.** A self-contradicting payload, shipped
inside the discriminator whose entire purpose is to stop exactly that confusion.

## Fix

Capture presence from the **same observation the enumeration used** (`inbox_present = inbox_dir.is_dir()`
taken before the scan, reported after), so the discriminator is consistent **by construction** rather
than by luck of timing.

## Rule

When you add a field that describes *how* an observation was made, it must be captured **from that
same observation**, not re-derived at emit time. Re-deriving a describes-the-scan field after the scan
is a TOCTOU that manufactures the exact false signal the field exists to prevent.

Corollary for reviewers: check a guard's predicate against the concurrency scenario the surrounding
module already declares it handles. This module's own `unreadable` code was the proof that the racing
scenario is real, sitting a few hundred lines from the defect.

Claim label: OBSERVED (review bot coderabbit, verified first-party and remediated on branch before
merge).
