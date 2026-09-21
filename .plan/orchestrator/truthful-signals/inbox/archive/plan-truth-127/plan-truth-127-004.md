envelope_version=1
sender_type=plan
sender_id=plan-truth-127
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T20:07:05Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-13

# A missing freshness-reconciliation record is reported as un-built source drift, though the contract itself has two other ways to produce that same absence

`phase-6-finalize/standards/push.md` § "Finalize-internal re-stale reconciliation" classifies a
`stale` / `worktree_mutated` refusal by looking for a `freshness-reconcile` decision record naming
the live HEAD, and its negative branch reads:

> **No reconciliation record names the current HEAD**: the `stale` is genuine un-built source drift.
> Fail closed per the table above — halt, record `outcome=failed`, do NOT push.

The halt is right. The **attribution** is not derived — it is asserted from an absence that the
same contract can produce in at least three different ways:

1. **No finalize-internal commit happened.** The intended meaning: the tree really did move past
   the last build under un-built source drift.
2. **`SKILL.md` Step 3 item 5f(d) deliberately fail-closed.** Its own text: *"When NO
   `status: success` entry exists, **fail closed**: skip emitting the reconciliation record
   entirely so the downstream push freshness gate stays `stale`."* A finalize-internal commit DID
   happen, the producer chose not to record it, and the consumer reports cause 1.
3. **The record was owed and not emitted.** Item 5f(d) is an unenforced obligation on the
   dispatcher — no guard sits between the commit and the push gate — so a skipped emission is
   byte-identical at the consumer to cause 1.

This run hit cause 3: a finalize-internal commit moved the tree, no reconciliation record existed,
and the gate refused. The refusal message named un-built source drift, which was not what had
happened.

## Not the lesson: "the record is owed at the commit, not at the refusal"

That framing is **already covered** and should not be filed. Item 5f(d) is explicit that the record
is emitted *"ONLY after a non-empty commit was made at (b)"* — the obligation is already placed at
the commit. The producer-side contract is correct as written; the gap is entirely on the consumer
side, in what it concludes when the record is absent.

## Solution

Do not change the fail-closed behaviour — it is correct on every one of the three causes. Change
what the refusal **reports**. The consumer observed one fact (no record names this HEAD) and should
report that fact, not a cause it cannot distinguish:

- Report the observation (`reconciliation_record_absent`) rather than the inferred cause
  (`genuine un-built source drift`), and name the causes the absence admits, so the operator's
  next move is chosen against what was actually observed.
- Where a cheap corroborator exists, use it before attributing. Whether HEAD is a finalize-internal
  `mutates_source` commit is independently observable from the step records the dispatcher already
  holds (`phase_steps` carries per-step `head_at_completion`), so cause 1 can be separated from
  causes 2 and 3 without trusting the record's presence.
- Cause 2 is worth surfacing distinctly: it means the last build did not succeed. That is a
  materially different operator action from "you edited source after the build", and today both
  arrive as the same sentence.

## Impact

The archetype is the epic's theme in cross-component form: **an absent record cannot say which kind
of absence it is, and a consumer that names one cause is publishing a confident signal over an
ambiguity it never resolved.** It generalizes past this gate to any pair where component A owes an
audit record at time T and component B draws a conclusion from its absence at time T+n — the
absence conflates "not owed", "deliberately withheld", and "owed and skipped".

This is adjacent to, but distinct from, the could-not-look-discriminator candidate already filed by
this plan's retrospective (`plan-truth-127-003`): that one is about a script publishing a
discriminator inside its own payload. This one is about a consumer inferring a positive cause from
the absence of a record a *different* component was obliged to write — no payload is involved, and
no field can be added to a record that was never emitted. The remedy is on the reading side, not
the writing side.
