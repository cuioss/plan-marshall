envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:48:00Z

component=plan-marshall:tools-integration-ci
category=bug
proposed_title=pr create has a plan-less body path, pr edit and prepare-comment do not — a plan-less PR can be opened but never corrected

# A plan-less PR can be opened but never corrected

## Status

**OBSERVED first-party, blocking.** Not fixed. Hit while trying to keep PR #1052's body honest
after a third commit was added to it.

## The asymmetry

`ci pr create` accepts EITHER body source:

```
--plan-id PLAN_ID   (plan-bound body source; mutually exclusive with --body-file)
--body-file PATH    (plan-less body source ... Used by the steward landing cycle,
                     which has no plan dir.)
```

`ci pr edit` accepts only one:

```
usage: ci.py pr edit [-h] --pr-number PR_NUMBER [--title TITLE] --plan-id PLAN_ID [--slot SLOT]
```

`--plan-id` is **required**, and there is no `--body-file`. `ci pr prepare-comment` is the same:
`--plan-id` required, no plan-less alternative. So the reply / thread-reply paths inherit the
restriction too.

## Why it bites

The plan-less path exists because real callers have no plan dir — the steward landing cycle is
named in the help text, and an ad-hoc post-merge fix PR is the same shape. Such a caller can
**open** a PR with a body and then can never **edit** that body or **comment** on the PR through
the abstraction. Concretely here: PR #1052 was opened with `--body-file` describing two commits;
a third commit was then added (a config correction); the body could not be updated to match.

The workaround is forbidden by policy — `CLAUDE.md` § Workflow Discipline: *"CI operations: use
abstraction layer — All CI/Git provider operations MUST go through
`plan-marshall:tools-integration-ci:ci` scripts. Never use `gh` or `glab` directly."* So the
correct behaviour is to leave the body stale, which is the outcome nobody wants.

## Why it belongs to this epic

The stale body is a **confident-but-incomplete signal**: #1052's body says "What changed" and
lists two of three changes. A reader takes an enumeration as complete. The commit log carries
the third, so nothing is hidden — but the PR body, the highest-visibility surface, understates
its own contents and there is no sanctioned way to fix it.

## Proposed action

Add `--body-file PATH` to `pr edit` as the mutually-exclusive plan-less alternative to
`--plan-id`, mirroring `pr create` exactly. Do the same for `pr prepare-comment` (or give
`pr reply` / `pr thread-reply` a direct `--body-file`). The plan-bound path is unchanged; this
only restores parity for callers the help text already acknowledges exist.

⚠ Check the whole verb family, not just the two found here — `prepare-body` also takes
`--plan-id`, and the population of `--plan-id`-requiring verbs should be enumerated from the
argparse surface rather than sampled. A fix that closes `edit` and leaves a sibling open repeats
the shape.

## Evidence

- `ci pr create --help` — carries `--plan-id | --body-file`
- `ci pr edit --help` — `--plan-id` required, no `--body-file`
- `ci pr prepare-comment --help` — `--plan-id` required
- PR #1052, third commit `5eb51463e` added after the body was written
