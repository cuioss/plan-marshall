envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:41:22Z

component=plan-marshall:manage-tasks
category=bug
bundle=plan-marshall

# pre-commit-verify-freshness accepted a --help invocation as evidence that a verify observed the tree

## What happened

`manage-tasks pre-commit-verify-freshness` returned `fresh` and named as its matching evidence a change-ledger row with notation `plan-marshall:build-npm:js_coverage` — **for a `--help` invocation**.

The **verdict was correct on this run**: a genuine `module-tests` success also matched the same `worktree_sha`, so a real verify had in fact observed the tree. But the row the freshness check *surfaced as its evidence* was vacuous. A `--help` call compiles nothing, runs nothing, and observes nothing. It is not evidence of anything.

## Why it matters for truthful signals

This is a latent false-green, and it is latent **precisely because a correct verdict masked it**. Had the genuine `module-tests` row been absent — a different plan, a different ordering, a build that never ran — the same `--help` row would have carried the `fresh` verdict on its own, and the pre-commit gate would have passed with zero real verification behind it.

The failure mode is not "the gate said the wrong thing." It is "the gate said the right thing for a reason that does not hold in general." That class only ever gets caught by looking at the evidence row when the verdict is *right*, which is exactly when nobody looks.

## Corrective rule

Two independent fixes, either of which closes the hole; do both:

1. **Writer side** — the change-ledger `kind=build` writer must not stamp a non-executing invocation (`--help`, `--version`, a dry-run, an argparse rejection) as a build row at all. A row that records no work performed is not a build record.
2. **Reader side** — the freshness reader must reject rows whose recorded command did no work, rather than treating notation-match + `worktree_sha`-match as sufficient. **Evidence selection must be a property of the row, not of the notation.**

## Recurrence archetype

Vacuous guard / evidence-that-is-not-evidence — the epic's recurring "the predicate matched, but on nothing" family. Directly adjacent to the known `build wrapper exits 0 on failure` and `never trust a routed build's outer status` rules: in all three the *shape* of a success signal is present while the *substance* is not.
