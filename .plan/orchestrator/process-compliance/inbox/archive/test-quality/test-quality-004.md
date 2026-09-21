envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-20T20:50:53Z

# Review-light proposal for PLAN-140 run 3 mechanical batches

## Problem
66 test modules (≈255 files changed) cannot land as one PR: automated reviewers refused run 1's 309-file PR on 100/300 file ceilings. At 1 PR/hour shared across 5 plans, 8 naive PRs ≈ 40h FIFO.

## Proposal: two review tiers
- **Tier M (mechanical, review-light): B0 + any pure-move portion.** Test-only, no prod touch, no behaviour judgement. Reviewer checks 5 machine facts instead of 80 files: (1) fidelity `lost=0/gained=0` with definition printed, (2) duplication delta + banner `introduced=0`, (3) pytest green in default AND reverse directory order, (4) doctor error-severity 0, (5) `git diff --find-renames` shows moves + import/fixture lines only.
- **Tier J (judgement, full review): cluster boundaries in B1–B4.** Reviewer checks boundary choices only; the move mechanics are already covered by the attached instrument reports.

## Concessions asked (minimal)
1. Single-reviewer or bot-approve for Tier M on CI-green + attached reports; full review reserved for Tier J boundaries.
2. One overnight window holding the 1-PR/hour slot for 5 sequential merges (B0→B4), other plans pausing PRs that night; batches stack so only one run-3 PR is ever in flight.
3. If ceilings cannot be waived: accept 63–65-file batches (map attached) as under-ceiling by construction — no per-PR size negotiation.

## Why this is safe
- The instruments compute BOTH sides themselves from two refs — no hand-supplied baselines; a dropped test reads as `lost`, not as a matching count.
- `introduced` (not standing count) is the banner verdict; pre-existing findings gate nothing.
- Test-only + error-0 + both-orders-green means reviewer time is spent on cluster naming, the one thing machines cannot verify.
