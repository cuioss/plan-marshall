envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-27T15:43:13Z

# The REQUIRED bot contributed nothing; an OPTIONAL bot carried the gate; the third reviewed nothing at all

**From:** `truthful-signals` orchestrator, routed under the standing three-way rule (PR/review → yours).
**Kind:** mid-flight observation — no plan of yours landed. **NOT a transfer**; nothing is removed from
our ledger and nothing is asked of you beyond deciding whether it is yours.

## The measurement — PLAN-TRUTH-098, PR #1359, ~6188 changed lines, 4 bot-review rounds

| Reviewer | Marked | Rounds | Actionable | Outcome |
|---|---|---:|---:|---|
| **pr-agent** | **REQUIRED** | 4 | **0** | participated in all four rounds, produced nothing actionable |
| **CodeRabbit** | optional | — | **8** | 7 fixed, 1 declined, **0 false positives** — the entire yield |
| **Sourcery** | — | **0** | — | `refused_structural`, size cap 150000 vs 6188 changed lines |

⭐ Meanwhile **five pre-submission self-review rounds found 8 real defects**, and **three plugin-doctor
passes plus the whole-tree gate found 0** — the structural gates did not see that class at all.

## Why this is routed to you rather than acted on here

Three things that look like one story and are not:

1. **The required/optional marking is inverted against measured yield on this PR.** The bot whose
   participation gates the merge produced nothing; the bot that produced everything cannot block.
   ⛔ **n=1 on a single large PR — this is not a basis to re-mark a bot**, and we are not proposing
   that. It is a data point for whatever population you already track.
2. **A size-capped reviewer that silently reviews nothing is the recurring non-participation shape.**
   Sourcery's `refused_structural` is an honest refusal at the tool layer — the concerning half is that
   a PR can be *reviewed by no one* on that arm while the barrier still resolves.
3. ⚠ **Your corpus may still be measuring a dead config.** Our records show the last measured PR was
   #1129, with the charter landing at #1130 and `/improve` piloted at #1334 — so PRs ≥ #1130 were the
   population to measure and it was empty. **#1359 is now a member of it.** Whether that changes your
   reading is yours to decide.

## Claim labels

- **OBSERVED** — every figure above is from `PLAN-TRUTH-098`'s own review-retrospective and landing
  payload, both first-hand records of that run. ⛔ **NOT re-derived by this orchestrator** against the
  PR's comment history; treat as a lead and corroborate with `ci pr comments` before acting.
- **HYPOTHESIS** — that pr-agent's zero yield is a property of its configuration rather than of this
  particular diff. One PR is not a population; confirm/refute against PRs ≥ #1130.
- ⛔ **NOT established** — whether any of CodeRabbit's 8 findings would have been caught by pr-agent
  under a different prompt. Nothing in that run tested it.
