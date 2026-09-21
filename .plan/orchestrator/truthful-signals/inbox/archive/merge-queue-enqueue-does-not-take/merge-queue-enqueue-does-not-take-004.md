envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T20:58:38Z

component=plan-marshall:plan-retrospective
category=bug
title=direct-gh-glab-usage scores 100 percent false positives on the CI abstraction layer it audits
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
routed_from=review-apparatus

# direct-gh-glab-usage scores 100 percent false positives on the CI abstraction layer it audits

## Context

Retrospective aspect 10 (`direct-gh-glab-usage`) exists to catch callers bypassing the CI abstraction with raw `gh`/`glab`. On this plan it emitted **22 findings, every one at `severity: error`, and all 22 are false positives** — a 22/22 miss rate.

## Root cause

Two independent defects, either of which alone produces the wrong verdict.

**1 — it matches prose, not invocations.** Every one of the 22 `diff_leak` hits is a `gh`/`glab` mention inside a **docstring or a test assertion string**. Samples, all verified by reading the source:

- `_github_pr.py:1115` — `` ``gh pr merge`` closes the PR unmerged.`` (inside `cmd_pr_merge`'s docstring, explaining the #866 defect)
- `_github_pr.py:1280` — `` ``gh pr merge --auto`` is ONE command with TWO dispositions``
- `test_github_ops.py:181` — `assert captured == [], 'Should not invoke gh when validation fails'` (an assertion message asserting gh is NOT invoked — the detector flags the guard against the thing it is looking for)
- `test_github_ops_pr_merge.py:505` — `error='the gh token lacks the scope to read repository rulesets'` (a test fixture string)

This is the same archetype as qgate finding `10b242` on this very plan, where `_QUEUE_VOCAB_RE` matched handler docstrings and made an assertion unfalsifiable. That one was found and fixed with mutation evidence; this one shipped in the retrospective tooling itself.

**2 — it audits the wrapper it is meant to protect callers from.** All 22 hits are inside `workflow-integration-github`, `workflow-integration-gitlab` and their tests — i.e. **the CI abstraction layer**, the one place in the repo where invoking `gh`/`glab` is not merely allowed but is the component's entire purpose. The rule "never use `gh` directly" is a rule about *callers*; the detector applies it to the *implementation*.

The severity makes it worse: 22 × `severity: error` in a report a human is meant to triage, with a 0 percent true-positive rate, trains the reader to skip the section.

## Proposed action

1. **Strip prose before matching.** Blank docstrings, comments and string literals from the searched source. `test_branch_cleanup_merge_queue_routing.py` (added by this very plan) already contains a working, offset-preserving `_code_without_prose` implementation with a permanent test lock — reuse it rather than re-deriving.
2. **Exclude the abstraction layer from its own rule.** `workflow-integration-*` scripts and their tests are the sanctioned `gh`/`glab` call sites by construction. Scope the scan to everything else, and say so in the fragment so an empty result is legible.
3. Key on a call-shaped pattern (`subprocess`/`run_gh`/argv-list construction) rather than the bare vocabulary token.
4. Until fixed, downgrade `diff_leak` from `error` to `info`.

## Evidence

- `fragment-direct-gh-glab-usage.toon` — `counts.total: 22`, `by_surface.diff_leak: 22`, `log_leak: 0`; all 22 rows `severity: error`.
- Each cited line verified by `Read` against `ca7cf9bd4`.
- qgate `10b242` on this plan — the same prose-matching archetype, fixed there with mutation evidence (old predicate 7/8 mutants still HIT; new 0/8).

## Dedup context for the orchestrator

New for this component. Instance of the standing `vacuous guard` archetype — and notably the third time on this plan that a detector matched prose the same commit authored. Gate 1 dedup NOT run (`orchestrated: true`).
