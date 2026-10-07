envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:54:42Z

component=plan-marshall:manage-status
category=bug
proposed_title=LIVE DEFECT (not fixed): _GLOB_RE matches markdown bold, short-circuiting the path count

# LIVE DEFECT (not fixed): `_GLOB_RE` matches markdown bold, short-circuiting the path count

## Status

**Found during `lane-router-reads-the-wrong-body`, deliberately NOT fixed** — out of the plan's agreed scope. This is a live defect in merged main after PR #1049. Route it. Likely **PLAN-57** territory.

## The defect

`_GLOB_RE` at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py:122` includes a `\*\*` alternative intended to catch filesystem globs like `src/**/foo.py`.

It also matches **markdown bold**: any `**emphasised text**` in a request body satisfies the regex. And the glob check **short-circuits before path counting**, so a single bold span anywhere in the request suppresses the entire path-count arm of the scoring.

This plan's own log shows `glob=True` on a fragment containing **no filesystem glob whatsoever** — only markdown bold.

## Why it matters

1. **It alone explains the PLAN-94 / PLAN-99 divergence** without needing to posit a second `scope_estimate` writer. That divergence has been attributed to writer multiplicity; this is a simpler and sufficient cause.
2. **PR #1049 makes it fire MORE often, not less.** The fix widens the scorer's input from a truncated header to the whole request body — and whole request bodies are markdown, densely bolded. The population the detector runs over just grew, and grew in exactly the direction that triggers the false positive.
3. Point 2 is itself the recurring rule: **a population-derived detector still needs its anchor re-checked when a fix widens the population.** #1049 widened it and this regex was not re-anchored.

## The rule

- A regex that classifies **filesystem syntax** must not be run against **prose markup** without first stripping or excluding markup constructs. `**`, `*`, `_`, `` ` `` and `[]()` all collide with glob/path syntax.
- A short-circuiting predicate that suppresses a downstream measurement (`glob → skip path count`) needs a **negative test** proving it does not fire on plain prose. Today it has none.
- When a change widens a detector's input population, re-run its anchor cases against the NEW population before landing.

## Suggested first test

Feed a request body containing `**bold**` and no glob; assert `glob == False` and that path counting still runs.
