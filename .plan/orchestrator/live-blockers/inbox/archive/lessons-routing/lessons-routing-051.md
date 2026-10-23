envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:24:17Z

# Leaves denied Grep/Glob have no sanctioned search over resource trees or declared sibling checkouts

Severity: high. Bundle: **plan-marshall** (`manage-architecture` inventory, `execution-context`, `persona-*` rule surfaces). Filed under RULING 2026-10-09 (a).

Two consequences recur: the hard rule against shell search is broken, or coverage silently shrinks and a step still records `done`.

## Sources

- corpus `2026-10-10-20-008`
- inbox `pm-mcp-core-m2-m4-292`, `-311`, `-337`, `-367`, `-385`

## Consolidated statement

The execution-context contract names `architecture search --content` as the search fallback for a leaf without Grep, but the inventory covers only module-attributed source kinds. It does not index:

- test and main **resource** files: `.json`, `.txt`, `.mmd`, `.pmwf`, `.adoc` fixtures (`architecture find "*.pmwf"` returns 0 for a plan that migrated 124 of them);
- `.claude/**` / `.github/**`;
- a project's declared **sibling checkouts** (`../plan-marshall-documentation`), which the project's own link checks span;
- a line-level lookup inside a known 2900-line file.

Consequences, as reported:

- At least seven leaves in four plans fell back to Bash `git grep` / `ls-files` and self-disclosed the rule violation; others left a claim unverified because they "could not locate it without a search tool".
- Coverage checks degraded to "could not look": a refine leaf could not recount fixtures, a 4-plan Q-Gate wrote its hashes `--partial` and recorded a `not_run_validators` entry, a functional review fell back to `git diff`.
- **A security audit reported "35 files, all examined" and 0 findings having read 5 of the 17 `.txt` fixtures**, and recorded the step `done`; a second iteration read all 17. This is exactly the silent-degradation the contract forbids.

## What is asked

- Include declared resource trees (`src/*/resources`, and at least `.json`, `.txt`, `.mmd`, `.pmwf`, `.adoc`) in the content-search inventory; or give `architecture search` an explicit `--path` / line-level mode (`--pattern P --path F` returning line numbers) for trees outside the inventory and for the allowlisted dotfile trees.
- Let a project declare extra indexed extensions and its sibling checkout roots, so a multi-phrase sweep across both is sanctioned.
- Publish the walked extensions (or the excluded population) in the result, so a sweep can state what it did not cover.
- Name the compliant replacement for in-file Grep in the execution-context runtime-tool-availability section, and state in the Grep-fallback guidance that a rejected call costs a retry on the path every leaf is told to use first.
- In coverage-class leaves, report a coverage gap in the return when files of the footprint could not be read.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
