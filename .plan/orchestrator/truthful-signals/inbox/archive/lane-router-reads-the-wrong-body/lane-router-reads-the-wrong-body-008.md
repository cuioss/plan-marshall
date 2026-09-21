envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:55:57Z

component=plan-marshall:manage-change-ledger
category=bug
proposed_title=The freshness gate counts --help invocations as build evidence, so a tree with zero real builds can report fresh

# The freshness gate counts `--help` invocations as build evidence, so a tree with zero real builds can report `fresh`

## Status

Observed during `lane-router-reads-the-wrong-body`. **Not a false-fresh in this run** — verified — but the mechanism that would produce one is live.

## What was observed

`pre-commit-verify-freshness` returned `fresh`, citing:

```text
matched_notation = plan-marshall:build-npm:js_coverage
args = --help
```

Two things wrong with that citation in a **Python-only repository**:

1. The matched notation is the **npm/JS** build script, in a repo with no JS build.
2. The matched invocation is `--help` — a discovery call that compiles nothing, tests nothing, and verifies nothing.

## Why this run was NOT a false green

Verified directly: real successful `pyproject_build` ledger entries exist at the **same `worktree_sha`**. The tree genuinely was verified; the gate simply cited the wrong entry as its evidence.

## Why it matters anyway

`--help` invocations are recorded as `kind=build status=success` in the change ledger. That means:

> A tree in which **only `--help` ever ran** would report `fresh` on **ZERO build evidence.**

The gate's answer would be indistinguishable from the answer on a fully-verified tree. This is the `stale-cache-as-evidence` archetype with a new source: not a stale entry, but a **substantively empty** one that satisfies the predicate.

It is also a **wrong-citation smell** that should itself have been a signal: a Python-only repo citing the JS coverage script is evidence the matcher is not discriminating, even when the verdict happens to be right.

## The rule (candidate)

1. **Exclude help/discovery invocations from build evidence.** A ledger entry whose args are `--help` (or any non-executing discovery verb) must not be recorded as `kind=build status=success`, or must be excluded from the freshness predicate's evidence set.
2. **A freshness verdict must cite an entry that could actually have verified the tree** — right build system, real command. Citing an entry from a build system the project does not use should be an error, not a pass.
3. Report the *evidence*, and make the evidence checkable. A gate that returns `fresh` while naming an implausible source is a confident signal hiding its caveat — the exact epic theme.

## Detection

Grep the change ledger for `kind=build` entries whose recorded args are `--help`. Any project where those are the only entries at the current `worktree_sha` is currently reporting a false `fresh`.
