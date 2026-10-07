envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:06:20Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
bundle=plan-marshall

# Widening an argument surface leaves the narrow form pinned in every doc that documented it

## Observation

Two doc-contract divergences on PR #1065, both found by CodeRabbit, both remediated as
TASK-013:

1. **A widened flag surface, un-swept docs.** `ci pr update-branch` was widened to accept
   *either* `--pr-number` *or* `--head` via the shared identifier resolver. The production
   change landed; `leaf-command-reference.md` and `api-contract.md` continued to document
   `--pr-number` only. A reader following the docs would never discover the new form, and
   nothing in the build could tell.

2. **A described-but-absent code path.** `tools-integration-ci/SKILL.md` described the
   router as running `git rev-parse` to resolve the working tree. In fact the router's
   neither-flag branch **returns before any resolution call** and inherits the caller's cwd.
   The doc described behaviour the code did not have.

## Why this is the epic's theme

Both are the same failure with opposite polarity — docs narrower than the code, and docs
wider than the code — and both read as *authoritative*. A reader consults
`leaf-command-reference.md` precisely because it claims to be the leaf-command reference; its
silence about `--head` is indistinguishable from `--head` not existing.

## Corrective rule

**A change to an argument surface is not done when the argparse declaration changes. It is
done when every document that pins the old shape has been swept.**

Operationally, for any widening / narrowing / renaming of a flag or verb:

1. Search for the *old* spelling across `SKILL.md`, `standards/`, `references/`, and any
   `## Canonical invocations` block — the canonical-invocation block is the highest-value
   target because the plugin-doctor analyzer treats it as source of truth.
2. Include the doc files in the deliverable's `affected_files`, so the sweep is a planned
   edit rather than a remembered one.
3. For behaviour prose (not just flag names): when a code path is described in a doc, the
   description must name the branch it describes. "The router runs `git rev-parse`" was true
   of *one* branch and false of the neither-flag branch; a branch-qualified sentence would
   have survived the change or failed loudly.

## Relationship to existing archetypes

This is the `doc-contract-divergence` archetype the epic already tracks, with a specific
trigger worth naming: **surface widening is a doc event**, not only a code event. The
orchestrator may prefer to reinforce the existing lesson rather than file a new one.
