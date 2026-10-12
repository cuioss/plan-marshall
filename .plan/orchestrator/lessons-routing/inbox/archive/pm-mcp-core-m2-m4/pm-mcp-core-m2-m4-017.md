envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:04Z

# Candidate lesson: the same security point was declined in triage round 1 and fixed in round 2

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-001 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source record: review-comment finding `41a716` (type `pr-comment`, author `coderabbitai`, kind `review_body`), resolved `fixed` in-run. Related record: finding `cce6ac` (author `sourcery-ai`, inline at `PathConfinement.java:167`), resolved `taken_into_account` as declined.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

The review text is third-party bot output and is summarised here, not quoted.

## What the records say

Round 1, Sourcery (`cce6ac`, rated High by the bot): `isLinkedTo` accepts a candidate worktree when its `.git` pointer leads to metadata whose `commondir` names the enrolled root, without confirming that the metadata's `gitdir` points back at that worktree or that the admin directory is a registered worktree of the root. Declined with the reasoning that the implemented rule is the one PM-SEC-2 and the solution outline specify, that the worktree set is supplied by the caller as already verified live, and that a reciprocal check would be extra hardening needing a specification change first.

Round 2, CodeRabbit (`41a716`, rated Major by the bot, reviewed commit `252b4b1`): the same gap, stated as: a candidate can name an arbitrary admin directory whose `commondir` resolves to the root's `.git` even when it is not registered below `.git/worktrees` and has no `gitdir` back-pointer, so `confine` can return `Confined` for contents outside the enrolled root.

Resolution of `41a716`: fixed by TASK-8 (commit `470df0e`). Before `confine` returns `Confined` for a linked worktree, `PathConfinement` verifies that the worktree's admin directory is registered directly below the root's `.git/worktrees` and that its `gitdir` back-pointer names the candidate's `.git` file. A hand-moved worktree may be refused until `git worktree repair` has run; the Javadoc says so. Tests cover the positive control and the unregistered and mismatched back-pointer cases. The reply supersedes the earlier decline.

## Log evidence

- Decision log `572828` (2026-10-10T06:16:10Z): the operator chose to fix `41a716` in this pull request.
- Decision log `ea3758`: "supersedes the round-1 decline of Sourcery cce6ac".
- Work log `1b556d`, `0b08ab`, `3a6d8f`: TASK-8 added, completed and committed.

## Why it may be a lesson

A confinement bypass was first declined on the ground that the specification did not ask for the check, and was fixed one round later when a second reviewer raised it and the operator decided. The decline was made by triage without the operator; the fix needed the operator. The cost was one extra loop-back round (round 2 of 3) and an overnight wait between 23:53Z and 06:16Z. The specification itself (PM-SEC-2) did not state the registration and back-pointer rule; the matching rule was added on the documentation branch.

Classification is left to the pickup.
