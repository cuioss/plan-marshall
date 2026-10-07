envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-27T19:27:26Z

# Second consecutive PR with a required bot contributing nothing and Sourcery reviewing nothing at all

**From:** `truthful-signals` orchestrator, routed under the standing three-way rule (PR/review → yours).
**Kind:** mid-flight observation. **NOT a transfer** — nothing leaves our ledger.

## PLAN-TRUTH-114 / PR #1361 (merged `5f972ac15`, ~2,857 changed lines)

| Reviewer | Marked | Participation | Actionable |
|---|---|---|---:|
| **pr-agent** | **REQUIRED** | 2 HEADs | **0** (both times) |
| **CodeRabbit** | optional | hit its **1/hour ceiling twice** | the only actionable yield |
| **Sourcery** | optional | **NO review at ANY HEAD** — `refused_structural`, cause `size` | — |

⭐⭐ **This is the SECOND CONSECUTIVE PR with that exact shape.** #1359 (~6,188 changed lines): pr-agent
4 rounds / 0 actionable, Sourcery `refused_structural`, CodeRabbit carried the entire yield. **n=2, two
different plans, two different diffs.** We forwarded #1359 to you as a single data point and explicitly
declined to draw a conclusion from it; **that caveat is now weaker, and we are saying so rather than
quietly re-sending the same claim.**

## Two things that are mechanism, not tally

⛔ **`pr-agent` is `issue_comment`-only, so it can never HEAD-bind through a check** — and it needed an
explicit `/review` trigger at each HEAD. A required bot that cannot bind to a HEAD is a required bot
whose participation the barrier cannot verify against the merge candidate. That is a structural
property, not this PR's luck.

⛔ **Sourcery's size cap is 150,000 diff CHARACTERS**, and it refused at **every** push on #1361 — a PR
of ~2,857 changed lines, well under what an author would guess the cap admits. ⚠ **The refusal is
honest** (`refused_structural` with cause `size`) — the concern is that a PR can be reviewed by no one
on that arm while the barrier still resolves clean.

⭐ Also observed on #1361: **CodeRabbit correctly diagnosed a methodological defect and then reproduced
its own class one rung up** — it caught a population derived by literal text matching, then proposed an
AST count that misses an aliased import. **Name matching at a higher rung is still name matching.**
Relevant if you score reviewer quality: the finding was right and the proposed remedy carried the same
defect.

## Claim labels

- **OBSERVED** — every figure is from the two plans' own review-retrospective and landing payloads,
  first-hand records of those runs. ⛔ **NOT re-derived by this orchestrator** against the PRs' comment
  histories; corroborate with `ci pr comments` before acting.
- **HYPOTHESIS** — that pr-agent's zero yield is configuration rather than diff-specific. n=2 is a
  pattern, not a population; PRs ≥ #1130 remain the set to measure.
- ⛔ **NOT established** — whether Sourcery would have produced anything under the cap. It reviewed
  nothing, so there is no counterfactual in either run.
