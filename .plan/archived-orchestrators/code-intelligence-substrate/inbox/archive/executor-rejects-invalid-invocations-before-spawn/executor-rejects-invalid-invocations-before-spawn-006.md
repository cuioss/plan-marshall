envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:43:27Z

# Name the canonical aspect key in each plan-retrospective Step 3 table row

component: plan-marshall:plan-retrospective
category: improvement
confidence: medium
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

`collect-fragments add` enforces a 17-member aspect-key registry and refuses any key
outside it, with an explicit rationale: an unregistered key means "compile-report would
silently drop its section".

But the SKILL's Step 3 aspect table names aspects by **prose label** — "Invariant
outcomes", "Script failure analysis", "Direct gh/glab usage" — while the capture pattern
below it writes `--aspect {name}` and `--aspect {aspect}` with no key list anywhere in the
document. The registry keys are `invariant-summary`, `script-failure-analysis`,
`direct-gh-glab-usage`.

In this run, three of five first-attempt keys were rejected (`invariants`,
`script-failures`, `direct-gh-glab`), costing three round-trips.

## Root cause

The guard is correct and the documentation is the gap. The registry is the source of
truth for the key; the SKILL is the source of truth for what the caller types; and the two
are not connected in the document the caller reads.

Worth stating plainly: the guard did exactly the right thing. It refused loudly instead of
accepting the key and silently dropping a report section — which is precisely the
failure mode its error message names. That is why this is filed as an improvement against
the doc and not as a bug against the script.

## Proposed action

Add the literal registry key as a column in the Step 3 aspect table (one key per row), and
replace the `{name}` / `{aspect}` placeholders in the capture-pattern snippets with a
pointer to that column. Optionally have the registry's valid-key list generated from the
same constant the script validates against, so the table cannot drift from the registry.

## Evidence

- `collect-fragments add` rejection payloads from this run — three rejections naming the 17 valid keys, at aspects `invariants`, `script-failures`, `direct-gh-glab`.
- `plan-retrospective/SKILL.md` § Step 3 — the aspect table's prose labels and the `--aspect {name}` capture pattern, neither of which carries a registry key.
- This is the same class as the plan's own subject matter: a caller typing a plausible-but-unregistered token, refused by a guard, where the fix is to publish the accepted set at the point of use.
