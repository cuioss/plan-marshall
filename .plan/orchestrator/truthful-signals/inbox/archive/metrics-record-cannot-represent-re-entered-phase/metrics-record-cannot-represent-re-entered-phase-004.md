envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:02:23Z

# Candidate lesson: a plan can leave its own documentation stale — the doc written one commit earlier is not corrected by the later commit

**Source**: Q-Gate finding `b2c144` (6-finalize), `fixed`
**Defect class**: contract_drift (self-inflicted, intra-plan)

## The finding

`data-format.md:483` — the "Known gap, owned elsewhere" paragraph under
`Per-Field Write Semantics → mark-step-done` — asserted in the present tense that the entry
"retains only its LAST firing", that superseded firings are "echoed to the caller in the
`previous_*` return fields and then discarded", that this is "a genuine loss of history", and that
the answer is "it forgets".

**All four claims were false in the live tree at the moment they were read** — and they were
falsified by *this same plan*. Commit `ea4e077de` added `firing_count` / `prior_firings`, so the
entry now retains every superseded firing.

The mechanism is mundane and therefore easy to repeat: `ea4e077de` did not touch `data-format.md`,
so the paragraph written **one commit earlier in the same plan** was never corrected.

## Why this class is dangerous specifically

A stale doc written by a *third party* is expected and is read with suspicion. A stale doc written
by *the same plan, one commit ago* reads as freshly authored and authoritative — it carries the
plan's own currency. The paragraph even linked to the "firing-history contract" in
`manage-status/SKILL.md:349-363`, which is exactly the section that documents the behaviour
contradicting it. A reader following the link would have found the contradiction; a reader
trusting the prose would not.

Compounding it: the per-field table at `:475-481` omitted `firing_count` and `prior_firings`
entirely, even though the section's declared job is to "state that semantics per field". So the
inventory that exists to be exhaustive silently was not.

## Candidate rule

> When a plan writes a document that describes current behaviour, and a LATER commit in the same
> plan changes that behaviour, the document is stale from the moment of the later commit. A
> "known gap / owned elsewhere / it currently does X" paragraph is a dated assertion; adding one
> creates an obligation to re-read it at the end of the plan.

Practical detector shape: at finalize, for every doc paragraph the plan authored in the present
tense about code the plan also touched, re-verify against HEAD rather than against the state at
authoring time. The existing `ext-self-review-plan-marshall` contract-drift check caught this one
— the lesson is that it is worth keeping pointed at the plan's OWN output, not only at
pre-existing docs.

## Cross-reference

Same family as the standing "doc-contract-divergence" archetype, but with the distinguishing
feature that the producer and the invalidator are the same plan. Worth recording as a named
sub-case: **self-invalidating documentation**.
