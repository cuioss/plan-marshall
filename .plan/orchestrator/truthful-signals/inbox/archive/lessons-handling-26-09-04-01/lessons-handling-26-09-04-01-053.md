envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:33Z

component=plan-marshall:persona-code-reviewer
category=anti-pattern

Relayed from Token-Sheriff PLAN-09 (PR #731 / `b6b1a94d`). ⛔ **This is the durable one.** Fixing the CITED sites of a defect class is not establishing the class is closed — and this run demonstrated it from both sides: the plan fixed DPoP/client-auth conflation at 8 cited sites, and two more (`token-handling.adoc:196`, `test-strategy.adoc:232`) survived outside the footprint, correctly identified but deliberately left. A reviewer citing N sites has not enumerated the class.

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
bundle=plan-marshall

# Fixing the cited sites of a defect class is not establishing that the class is closed

A reviewer cites N instances of a defect class. Fixing those N and declaring the
class closed feels like completion, and it is not: the citation list is a
**sample the reviewer happened to surface**, never the population. Closure is a
claim about the population, so it requires a pass over the population.

This run made the mistake twice on the same defect class — the DPoP /
client-auth conflation. Round 3 fixed the cited sites and declared closure.
Round 4 fixed the newly-cited sites and declared closure again. Neither round
had looked at anything except the citations. What actually established closure
was an exhaustive `architecture search --content` sweep over the class's
signature, read under the complete-coverage conjunction so the zero was
trustworthy rather than merely reported.

The repeat is the tell. A defect class that keeps producing "one more site" after
each declared closure is a class nobody has enumerated.

## Solution

When a review cites instances of a *class* (as opposed to a single located
defect), do not close on the citations. Instead:

1. Derive a searchable signature for the class.
2. Sweep the population with `architecture search --content --pattern P`
   (`--literal` / `--ignore-case` as the signature needs).
3. Read the coverage fields before believing the result — a zero is only
   trustworthy under the complete-coverage conjunction. An unreadable file or an
   elided inventory bucket is a file that might hold the defect and was never
   scanned, and that is a coverage gap to report, not an absence to record.
4. Report the swept population alongside the fix count, so the closure claim
   carries its own denominator.

This is the defect-class analogue of the existing "never assert closure over an
enumeration without re-checking it against its declaring source" rule in
`agent-behavior-rules.md`. That rule governs a written enumeration; this one
governs an implicit one — the set of sites exhibiting a defect. The orchestrator
may prefer to extend the existing rule rather than file a sibling.

## Impact

Every review round that produces class-shaped findings. The cost is
repeat-review cycles that each look like progress, plus the reviewer credibility
spent on a closure claim that does not hold.
