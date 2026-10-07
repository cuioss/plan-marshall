envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:30:09Z

component=plan-marshall:audit-archived-plan-retrospectives
category=improvement
title=D5's acceptance is not-yet-measurable and its re-check obligation lives only in a pending finding inside a plan about to be archived

# The plan shipped a check whose acceptance is unverified, and the obligation to verify it is about to become invisible

# Observation

Deliverable D5 of plan `exploration-share-is-unmeasured` shipped the `exploration-share` audit check. Its own acceptance outcome is **NOT-YET-MEASURABLE** — the third outcome D1 authorized, reported as neither a pass nor a regression.

The evidence recorded in insight finding `c0d568`:

- Run A (from the plan worktree, the literal TASK-8 command): `plans_scanned=0`, `plans_in_corpus=0` — the worktree-resident `.plan` carries no archived-plan corpus, so the run measured nothing.
- Run B (against the main-checkout corpus): `plans_scanned=17`, `plans_excluded_no_counters=17`, `plans_in_corpus=0`, zero rows, **every share statistic 0.000 by construction**.
- Cause: all 17 archived plans predate D2's counters. No post-D2 plan has been archived yet.

The finding is explicit and honest about all of this, and states the re-check condition: *"Re-run this check once at least two post-D2 plans are archived."*

## The gap

That obligation exists in exactly one place: a finding with `resolution: pending` inside a plan directory that `archive-plan` is about to move into `.plan/local/archived-plans/`. Nothing schedules the re-run, nothing owns it, and no epic-level or corpus-level record carries it. Once the plan archives, the obligation is discoverable only by someone already reading this plan's findings store — i.e. by accident.

Meanwhile the shipped check continues to emit `plans_in_corpus=0` alongside share statistics of `0.000`. The exclusion count is present and auditable, but the share fields are **not guarded against being read standalone**. A downstream consumer that reads `exploration_share` without also reading `plans_excluded_no_counters` gets a confident `0.000` — a false green of exactly the kind this epic exists to eliminate, emitted by the epic's own instrument.

## Rule

- **A deliverable that ships with an unverifiable acceptance must leave a scheduled obligation outside the plan, not a pending finding inside it.** A plan directory is a terminal store; an obligation placed there expires with the plan.
- **A statistic computed over an empty corpus must not be emitted as a number.** When `plans_in_corpus == 0`, the share fields should be `null`/absent with a reason token, not `0.000`. An empty-population mean is undefined, and rendering it as zero is the same substitution — absence read as a value — that D3 was written to forbid.
- Re-check conditions must be expressed as a machine-evaluable predicate (`archived plans carrying D2 counters >= 2`), not as prose in a finding body, so a periodic audit can fire it without a human remembering.

## What was done right

This is the strongest work in the plan and should be the template. The team ran the check two ways, documented that run A measured nothing rather than reporting its zeros, explicitly refused to reuse the D1 transcript-derived baseline (a different unit) to manufacture a verdict, and recorded that **the acceptance criterion was NOT reshaped to fit the result** — noting that TASK-8's literal "carries at least one row" criterion is unsatisfiable in the not-yet-measurable case and is superseded by D1's three-outcome clause. That is the epic thesis executed correctly under pressure to declare success.

The defect is only that the honesty stops at the plan boundary.

## Residue

Owed: (a) carry the re-check obligation onto the epic, (b) make the empty-corpus share fields null-with-reason rather than 0.000, (c) express the re-check trigger as a predicate.
