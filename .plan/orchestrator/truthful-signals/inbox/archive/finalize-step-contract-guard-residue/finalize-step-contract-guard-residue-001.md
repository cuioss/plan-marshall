envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:22:25Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=finalize-step-contract-guard-residue

# Publish the scanned population on direct-gh-glab-usage instead of a bare zero

## Context

The `direct-gh-glab-usage` aspect reports `counts.total: 0` / `by_surface.diff_leak: 0` with no field naming what it scanned. Its Surface B is `git diff {base}...HEAD`, and `cmd_run` resolves `base = args.base or 'main'`. For a plan whose PR has landed, `HEAD == main` (verified here: both resolve to `b95d78437`), so the default diff compares a commit to itself and the surface examines nothing.

Three distinct failure paths in `_git_diff_added_lines` also return `[]` silently — `FileNotFoundError`, `subprocess.TimeoutExpired`, and `returncode != 0`. The docstring states the consequence plainly: "the aspect then reports zero diff findings."

A matched control run on this plan makes the indistinguishability concrete. With `--base` set to the plan's stale recorded `main_sha` the aspect emitted **35 error-severity findings**, every one naming a file outside this plan's 26-file footprint. With the true merge base (`77c9dc70a`) it emitted **0**. With the default it also emitted **0** — the right answer, reached by not looking.

## Root cause

The fragment publishes a verdict without publishing the population the verdict is over. `base`, the resolved diff file count, and a could-not-look status are all absent from the output, so "scanned 26 files and found nothing" and "scanned nothing" serialize identically.

## Proposed action

Emit the resolved `base`, the count of diff files actually scanned, and a three-way `status` (`evaluated` / `indeterminate` / `not_applicable`) on the fragment. Return `indeterminate` — never a clean zero — when the git invocation fails or when the resolved base equals HEAD. The sibling aspect in the same skill, `check-artifact-consistency`, already does exactly this: it reports `inconclusive` with `footprint_resolved: false` and the message "recall is unmeasurable, not 0%". Adopt that shape here.

Additionally, stop defaulting `base` to the literal ref `main`; consume the resolved base from the shared footprint resolver instead.

## Evidence

- aspect: direct_gh_glab_usage — `counts.total: 0` with no population field, from a diff that is empty by construction
- aspect: direct_gh_glab_usage — matched control: 35 findings at the stale base, 0 at the true base, 0 at the default
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/direct-gh-glab-usage.py` line 216 `base = args.base or 'main'`; lines 159-162 the two silent `return []` paths
- aspect: artifact_consistency — the correct precedent in the same skill: `inconclusive`, `footprint_resolved: false`
