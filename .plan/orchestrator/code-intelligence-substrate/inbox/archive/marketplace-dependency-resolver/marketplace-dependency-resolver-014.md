envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:47Z

component=plan-marshall:workflow-integration-github
category=bug
title=Route the pre-merge barrier through bot_completion instead of a hand-rolled comment count

# Route the pre-merge barrier through bot_completion instead of a hand-rolled comment count

## Context

At 21:15:47Z the barrier recorded:

> my count-based monitor predicate reported `PR_AGENT_NO_RESPONSE` because
> pr-agent EDITS its Reviewer Guide comment in place rather than posting a new
> one, so the comment count stayed at 1 while the content changed. That is the
> same edit-in-place false negative PR 1071 fixes, hit a second time in this run.

The session transcript confirms it from the harness side: monitor `b4gq8jmk1`
terminated with `PR_AGENT_NO_RESPONSE: /review trigger produced no new pr-agent
comment within budget (count stayed 1)`.

The load-bearing detail is that **PR #1071 was already in the tree**. It merged
as `7da89fa95` before `8db7b42d4` (#1073), and this plan's branch was rebased
onto `8db7b42d..1decffb9`. The fix — timestamp-based re-review detection for
edit-in-place bots, shipped as the `bot_completion` verb on
`workflow-integration-github` — was present and callable at the exact moment the
barrier hand-rolled a comment-count predicate instead.

## Root cause

A fix lands in a repository; it does not land in a *behaviour* until the
consuming path calls it. The barrier's wait logic composes its own predicate over
raw `ci pr comments` output rather than delegating the "did this bot complete a
review?" question to the verb that exists to answer it. Because the predicate is
authored fresh per run, a shipped fix in the verb cannot reach it.

This also explains why the same class of defect recurred three more times in the
same run against CodeRabbit (see the sibling proposal on terminal markers): every
predicate was hand-authored at the call site, so no fix accumulated anywhere.

## Proposed action

1. Make the pre-merge barrier's participation check **delegate** to
   `github_pr bot_completion` for every bot, with no locally-composed comment
   predicate as an alternative path.
2. Where `bot_completion` lacks a needed capability (e.g. CodeRabbit's terminal
   `Actionable comments posted:` marker), extend the verb — do not re-implement
   around it at the call site.
3. Add a guard that fails the barrier's own tests if a participation decision is
   derived from a raw comment count rather than from `bot_completion`.
4. Related: this run also produced two argparse rejections of the form
   `ci pr … --pr-number 1074 --plan-id …` (`unrecognized arguments`) and one
   `github_pr fetch_findings --enabled-bots …` (`unrecognized arguments`). Both
   are symptoms of the same thing — the barrier improvising an invocation
   surface rather than using the documented verb.

## Evidence

- decision.log `2b68fe` (21:15:47Z) — the edit-in-place false negative, named as
  a second occurrence of the PR #1071 defect.
- transcript event `b4gq8jmk1` — `PR_AGENT_NO_RESPONSE … count stayed 1`.
- `git log` — `7da89fa95` (#1071) precedes `8db7b42d4` (#1073); the rebase base
  was `8db7b42d`, so #1071 was in the tree.
- aspect: script_failure_analysis — `invented_flag` rejections on
  `tools-integration-ci:ci` (×2) and `workflow-integration-github:github_pr` (×1).
