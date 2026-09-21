envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:20Z

component=plan-marshall:tools-script-executor
category=improvement
bundle=plan-marshall

# The empty-flag exit-2 population across marketplace scripts is UNMEASURED — derive it as its own plan

Plan `crashed-participation-gate-records-a-pass` fixed **seven** flags across **two** parsers (`review_completeness.py check` x5, `github_pr.py fetch_findings` x2). It measured nothing beyond those two parsers and claims nothing about the rest of the marketplace.

Because the executor's empty-argument strip is global (`script_args = [a for a in script_args if a]`, `.plan/execute-script.py:989`), **any** marketplace script with an optional flag that lacks `nargs='?'` and is reachable with an empty value is exposed identically. Whether such sites exist elsewhere is an open question, not a settled one.

This is the recurring `volume-read-as-coverage` shape: "7 flags fixed" is a VOLUME, not a coverage number, and the fixed set was chosen by the crash that was reported rather than by a derived population.

## Solution

Stand up a separate plan whose deliverable is the derived population, not a spot-check:

1. Enumerate the argparse surfaces of **all** marketplace scripts (population source, not a sample).
2. Filter to optional arguments declared without `nargs='?'` / `const`.
3. Cross that set with invocation sites — SKILL.md / workflow docs / other scripts — that interpolate a possibly-empty placeholder into the flag's value.
4. The intersection is the exposed population. Fix the parsers; add a population-derived detector with a vacuity guard so the set-guarding test cannot silently pass on an empty population.

## Impact

Field evidence that this bites in production: API-Sheriff PR #138 hit exit-2 on **4** `review_completeness` invocations while `automatic-review` still recorded `outcome=done` — a crashed gate that reported a pass. Any other exposed site fails the same silent way, so the cost of leaving the population underived is a class of false-green gates, not a class of visible errors.
