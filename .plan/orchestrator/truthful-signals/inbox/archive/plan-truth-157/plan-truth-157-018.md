envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:48Z

component=plan-marshall:plan-orchestrator
category=anti-pattern
bundle=plan-marshall

# When the substantive point stands on its own, DELETE the restated mechanism rather than rewording it

The fix for the ambiguous "per-plan carries" sentence added a clause asserting that
the re-grounding machinery addresses a spec's claims BY LABEL, citing
`corpus set-verdict --claim-index` as the mechanism. Both governing contract sources
refute that:

- `orchestration-model.md`'s Re-Grounding Verdict Field section states association
  is by NESTING, never by ordinal position.
- `plan-orchestrator/SKILL.md`'s `corpus set-verdict` section states `--claim-index`
  stays a pure zero-based ORDINAL that never doubles as a sentinel.

So addressing is by zero-based ordinal, and verdict-to-claim association is by
nesting — neither is by label. A fix for an ambiguity introduced a fresh, confidently
wrong mechanism claim.

Source record: Q-Gate finding `ee0de5`, phase `6-finalize`, defect_class
`contract_drift`, resolution `fixed` in commit `85d8e628c`.

## Solution

The substantive point — a body drafted without claim bullets cannot be re-grounded
— is correct and independently supported. The convergent fix is therefore to DELETE
the inaccurate mechanism parenthetical, not to reword it: the obligation stands
stated without any restated mechanism.

General rule: when justifying an obligation, do not restate the mechanism that
enforces it at a second site. Either point at the owning document or state the
obligation bare. A restated mechanism is a second copy that drifts, and a wrong
mechanism is worse than no mechanism because it reads as the authority a reader
then propagates.

## Impact

Same shape as the sibling candidate on `_AFFIRMATIVE_RE`: the FIX authored the next
defect. The recurring generator here is the urge to add supporting detail while
correcting a nearby sentence — the correction is in scope, the new mechanism claim
is not, and it arrives unreviewed because attention is on the thing being fixed.
