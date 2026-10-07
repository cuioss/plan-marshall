envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=finding
created=2026-09-05T07:49:17Z

# Correction to landing message 015, Residue item 3

**Corrects:** `apply-the-cloud-plan-lane-contract-amendments-015.md` (`kind: landing`), § Residue item 3
("`status.json` phase drift, corroborating the retrospective").

## What item 3 claims

That `phases[]` records `2-refine` as `in_progress` while the plan sits at `6-finalize`, that `progress`
reports `completed_phases: 4` where five are genuinely complete, and that the condition was left
unrepaired and would therefore ship into the archive.

## What is actually true

The first half was accurate **at the time it was written** — the drift was read directly off the live
`status.json` during `emit-landing`, and independently corroborated by `manage-status progress`
returning `completed_phases: 4` at `6-finalize`.

The **conclusion is wrong**. The drift did NOT survive the archive. The archived record at
`.plan/local/archived-plans/2026-09-05-apply-the-cloud-plan-lane-contract-amendments/status.json`
shows:

```
1-init      done
2-refine    done
3-outline   done
4-plan      done
5-execute   done
6-finalize  in_progress
```

`2-refine` is `done`. `manage-status archive` normalized the phase rows as part of the archive move,
so the "left unrepaired, ships into the archive" framing of item 3 does not hold.

`6-finalize` remaining `in_progress` is NOT a residual instance of the same drift: there is no
transition that closes the terminal phase — the archive IS the terminal act — so that is the normal
shape of a completed plan's record, not an unclosed phase.

## What survives from item 3

The light-lane bookkeeping gap it points at is real and is unaffected by this correction: the light
planning lane collapses refine+outline+derive into one envelope and does not close `2-refine` at the
time it completes, so the phase reads `in_progress` for the whole of `4-plan`, `5-execute` and
`6-finalize`. Anything reading phase state **mid-run** — a resume check, a progress percentage, a
handshake counting completed phases — sees the wrong value for the majority of the plan's life. Only
the archive repairs it, and only after every consumer that could have been misled has already read it.

So the defect is a **window**, not a persisted corruption. Item 3 named the right mechanism and the
wrong blast radius.

## Why this correction is a separate message

The landing spec allows exactly one `kind: landing` per orchestrated finalize run, and the erroneous
text sits in the prose `## Residue` section rather than in the validated `landing-facts` block — so no
machine-readable fact key is affected and the drain's completeness check on 015 is unchanged. This is
filed as a `finding` so the drain sees the correction alongside the message it corrects, rather than
by rewriting an already-written envelope.
