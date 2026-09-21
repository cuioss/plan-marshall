envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:22:20Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_finding=64659b
source_aspects=request-result-alignment

# Two candidate lists inflate counts.total and the examined-candidates verdict with no consuming check

`duplicate_claimable_keys` (N21) and `discard_without_report` (N22) are entries in the `CANDIDATE_LISTS` registry carrying **`in_total: true`**, so they are summed into `counts.total`. But **neither has a consuming check** — the `pre-submission-self-review` workflow's check list stops at check 15 (`worked_example_pairs`).

Three consequences, all live:

1. They inflate `counts.total`.
2. They inflate the Step 1b **candidate-count dispatch gate**, so a round can be dispatched on candidates nothing will examine.
3. They are counted by the terminal verdict — **`self-review clean: {N} candidates examined, no check matched`** — as *examined*, when no check examines them. PR #1126's own closing verdict reads "76 candidates examined"; two of the lists in that 76 were never examined by anything.

## Root cause

Registry membership (`in_total`) and check coverage are two independent facts with no invariant tying them together. A key can join the registry, join the total, join the gate arithmetic, and join the verdict's headline number without any check ever reading it.

## Solution

Deliberately unresolved by the originating plan, because **the two available remedies move the published count in opposite directions** and the choice is a policy call, not a mechanical one:

- **Add the two consuming checks** → the count stays high and becomes honest.
- **Drop `in_total` for both** → the count falls, the gate threshold behaviour changes, and the verdict's headline shrinks.

Whichever is chosen, add the missing invariant: a registry entry with `in_total: true` MUST have a consuming check, enforced by a contract test derived from the registry rather than a hand-copied list.

## Impact

This is **volume-read-as-coverage inside the contract that exists to detect volume-read-as-coverage.** The `{N} candidates examined` verdict is the self-review step's primary coverage claim, and it over-reports its own coverage by construction. The recurring archetype ("volume read as coverage") is reproduced by the instrument built to catch it — the same shape as a plan reproducing its own target defect.

Also note the ext-point documentation drifted repeatedly against these same two keys across rounds 1-3 (`1ddf70`, `4b475a`, `64659b`, `2dd0c0`), because the registry grew to 22 while the doc's enumerations, formula, and prose stayed at 19/20/21.
