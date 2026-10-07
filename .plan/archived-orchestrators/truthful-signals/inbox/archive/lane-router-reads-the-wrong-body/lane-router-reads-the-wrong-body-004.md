envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:54:15Z

component=plan-marshall:execution-context
category=anti-pattern
proposed_title=An honestly-declared coverage gap is not coverage — and `git grep` is not the blocked binary

# An honestly-declared coverage gap is not coverage — and `git grep` is not the blocked binary

## What happened

Deliverable D1 had to enumerate every writer of `scope_estimate`. The dispatched leaf ran with `Grep`/`Glob` **denied by the runtime**, and Bash `grep` is hard-blocked by the project's file-operation rule.

The leaf's first answer: **three** writers, plus an explicitly and honestly declared coverage gap — "these files were not swept, the search tools were unavailable." Textbook-good disclosure. It looked correct and it read as trustworthy precisely *because* it declared its limit.

It was wrong. `git grep` is a **git subcommand**, not the blocked `grep` binary, and it was available the whole time. Sweeping with it found a **FOURTH writer** at `phase-3-outline/workflow/light-lane.md:126` — **inside a file the first pass had explicitly named as unswept**.

The self-correction caught it. Had it not, the plan would have shipped a 3-of-4 enumeration wearing a disclaimer that made it look complete-with-caveats.

## Why it matters

This is `volume-read-as-coverage`'s more dangerous cousin: **disclaimer-read-as-coverage**. A declared gap converts an incomplete answer into an apparently-honest one, which *lowers* the reviewer's scrutiny at exactly the moment it should raise it. The confident signal ("here is my answer") hides the caveat ("the answer is a sample") behind a caveat that reads as diligence.

It is also a **capability-assumption defect**: the leaf inferred "no search capability" from "no `Grep` tool + no `grep` binary" without enumerating what search capability actually remained.

## The rule

1. **A declared coverage gap is a BLOCKER, not a disclosure.** When a set-enumeration deliverable cannot sweep its full population, the leaf MUST NOT return a partial enumeration with a note. It returns the coverage gap to the orchestrator (the sanctioned search-capable path) and lets the orchestrator close it. Never "pass green with shrunken coverage."
2. **Enumerate remaining capability before declaring a gap.** Specifically: `git grep` (and `git ls-files`) are git subcommands available under the git carve-out and are NOT covered by the no-Bash-file-operations rule, which targets `grep` / `find` / `cat` / `ls`. A leaf denied `Grep`/`Glob` still has `architecture find --pattern P`, `architecture files --module X`, `architecture which-module --path P`, `git grep`, and `Read`.
3. **Every set-guarding enumeration must be population-derived** — as with `test/_shared/_dispatch_roster.py`. A hand-listed set of writers is a sample; only a derived one is an enumeration.

## Detection

Any deliverable whose output contains a phrase of the form "could not sweep X / tool unavailable / best-effort enumeration" is a coverage-gap escalation that was silently downgraded to a disclaimer. Treat every such phrase as a failed step.
