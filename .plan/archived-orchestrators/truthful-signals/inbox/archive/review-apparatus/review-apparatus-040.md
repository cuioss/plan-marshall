envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-13T21:27:11Z

# A gate build row is written with `worktree_sha=None`, and the reason it is harmless rests on a convention, not an invariant

Transferred from `review-apparatus` (inbox `plan-pr-046-013.md`) on 2026-09-13. ⭐ **Not PR/review
subject matter** — it is `script-shared`'s build ledger — so the PR test does not claim it. ⚠ The
sending plan filed it because `plan-pr-046` declined the finding and then **carried it nowhere**: it
appears in none of that plan's eleven other inbox messages. It was dropped, not routed.

## The code, as shipped on main at `77cb2e251`

`marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py`,
`_append_gate_build_row` (~line 492) writes `worktree_sha=None` into the record. The `None` is
deliberate and documented in that function's own docstring.

## What is and is not established

CodeRabbit raised it as `c5db78` (Major) on PR #1477, resolved `taken_into_account` — ⛔ **the code
observation was never disputed.** The claimed consequence was: a direct `cmd_run` build appends a
`kind=build` row carrying no currency hash, so a consumer reading that row for freshness sees `stale`
and blocks the pre-commit transition.

⛔ **That consequence was argued unreachable on two grounds, and the sending plan's own assessment is
that BOTH are weaker than a refutation** — they rest on a convention about how callers behave, not on
an invariant the code enforces. So the defect is not *shown harmless*; it is *currently unreached*,
which is a different and far more fragile claim: a new caller that does not follow the convention
reaches it without anything failing loudly.

## Why it is worth carrying rather than closing

This is the epic-agnostic shape worth keeping: **a finding whose observation is accepted and whose
impact is argued away by appeal to caller behaviour.** The disposition record then says
`taken_into_account`, which reads as settled, while what actually holds it closed is an unwritten
convention no test pins.

Suggested settlement — either make the harmlessness an invariant (assert or type-enforce that a
`kind=build` row without a currency hash is never read for freshness), or write the currency hash and
delete the argument. ⚠ **Lead, not instruction**: the two unreachability grounds were not re-derived
in this checkout at HEAD.
