envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:35:48Z

## Proposed lesson metadata

- `component`: `pm-plugin-development:ext-self-review-plan-marshall`
- `category`: `anti-pattern`
- `title`: Three LLM review passes cannot converge a closed-set claim — only a population-derived sweep can

## Observation

This plan's target defect class was *prose asserting a closed set of subtractions
where the real set is larger*. Its own pre-submission self-review found **8
instances of that exact defect class inside its own diff**.

The convergence behaviour is the finding:

- Three separate LLM review passes each believed they were complete.
- Pass 1 and pass 2 each **missed instances that pass 3 later found**.
- One instance — the phrase "the only compose-time subtraction that drops the
  consumer step" — appeared in **three separate files**. It was found and fixed
  **twice** before all three occurrences were located.
- Only a **population-derived mechanical sweep** converged the set. That sweep
  found **3 further instances** beyond what three LLM passes had produced.
- One of those three was inside the orchestrator's **own remediation prose**:
  "One known exception" was itself false — there were four.

## Rule

A claim of the form "this is the only X" / "the N cases are …" / "one known
exception" is a **closed-set assertion**, and an LLM reading pass is structurally
incapable of certifying one. Repeating the pass does not fix it: each pass
samples, and independent samples do not converge to an enumeration.

When a diff contains closed-set assertions:

1. Enumerate the population mechanically (grep/sweep the *generating structure*,
   not the prose), then check each assertion against that population.
2. Treat "a pass found nothing new" as **no evidence** of completeness — pass 2
   found nothing pass 3 later found.
3. Sweep for the *shape* (`the only`, `one known exception`, `both`, `all N`,
   `exactly`), not for the specific claim already fixed — the same false claim
   recurs verbatim across files.
4. Apply the sweep to remediation prose too. Prose written *while fixing* this
   defect class reproduced it.

This is the strongest available argument for keeping the deterministic
`ext-self-review-*` candidate surfacing ahead of, not instead of, LLM judgment.
