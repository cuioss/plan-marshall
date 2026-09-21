envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:50:58Z

# Scope architecture search with --category — --module is rejected there

component: plan-marshall:manage-architecture
category: anti-pattern
confidence: medium
source_plan: plan-truth-157
source_aspects: script_failure_analysis

## Context

`script-failure-analysis` recorded an `invented_flag` argparse rejection against
`plan-marshall:manage-architecture:architecture search` at 2026-09-14T20:29:44Z, exit code 2. The captured
stderr excerpt was truncated before it named the offending flag; it shows only the top-level usage line that
argparse prints for an `unrecognized arguments` error.

The obvious inference — that the content-search seam the always-loaded rules prescribe is not yet shipped —
was checked and REFUTED. A live `architecture search --help` confirms the verb and every documented flag are
present: `--content` (required, so the mode stays explicit), `--pattern`, `--category`, `--literal`, and
`--ignore-case`. The rejection is therefore flag-name drift on a correctly-chosen verb, not a missing
feature.

## Root cause

Probable shape, stated as probable because the flag name was not captured: a cross-verb carry-over of
`--module`. Every neighbouring verb in the same script scopes by module — `architecture files --module X`,
`architecture which-module --path P` — and the always-loaded "Structured queries first" rule presents those
verbs side by side with `search --content --pattern P` in one list. `search` is the one member of that list
that scopes by `--category` instead, and nothing at the call site signals the difference.

This is the verb-scoped-flag-drift family the rule set already documents, occurring between two verbs of the
*same* script rather than between two scripts.

## Proposed action

Either of these closes it; the first is cheaper and the second is kinder to the caller:

1. Name the scoping flag explicitly wherever the always-loaded rules prescribe this verb, so the one-line
   form a reader copies carries `--category` rather than leaving scoping to be guessed from the neighbours.
2. Accept `--module` on `search` as an alias for the module-scoping intent, so the carry-over cannot fail at
   all.

## Evidence

- aspect: script_failure_analysis — `anti-pattern, invented_flag,
  "plan-marshall:manage-architecture:architecture", search, 2, "2026-09-14T20:29:44Z"`, occurrence_count 1
- Live `architecture search --help` output confirming `--content`, `--pattern`, `--category`, `--literal`,
  `--ignore-case` are all shipped — the check that refuted the missing-seam reading
- The always-loaded "Structured queries first" rule lists `files --module X`, `which-module --path P`,
  `find --pattern P` and `search --content --pattern P` together, with `--category` named only in the
  linked client-api document
