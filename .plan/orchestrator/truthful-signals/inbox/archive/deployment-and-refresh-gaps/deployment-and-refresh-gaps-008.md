envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:40Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-010.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: the argparse-rejection recurrence signatures fired again, on notations the codified guidance does not cover by name

**Component:** `plan-marshall:tools-integration-ci` / `plan-marshall:workflow-integration-github` / `plan-marshall:automatic-review`
**Category:** anti-pattern
**Signal:** `signal_script_failure_clusters_count = 2`

## The five rejections observed

| Time | Notation | Rejection |
|---|---|---|
| 14:35 | `tools-integration-ci:ci` | `unrecognized arguments: --plan-id …` — flag placed AFTER the verb; it is a top-level router flag |
| 15:38 | `workflow-integration-github:github_pr bot_completion` | missing required `--bot-kind` |
| 15:38 | `workflow-integration-github:github_pr` | `unrecognized arguments: --plan-id …` — this script does not declare `--plan-id` **at all** |
| 16:05 | `tools-integration-ci:ci pr reply` | undeclared flag; declared set is `['plan-id','pr-number','slot']` |
| 16:38 | `automatic-review:review_completeness check` | argparse usage rejection |

All five were exit-code-2 rejections that never reached a script body.

## Why this is worth recording despite being already codified

`persona-plan-marshall-agent` § "Never invent script subcommands" already enumerates five
recurrence signatures including the `--plan-id`-position pair. It fired anyway, **three times in
one run**, and the three `--plan-id` cases are three genuinely different rules on three sibling
scripts:

- `ci` — `--plan-id` is a **top-level router flag**, valid only BEFORE the verb, and only for
  the verbs that do not declare their own
- `github_pr` — declares **no `--plan-id` whatsoever**; appending it is always a rejection
- `manage-*` — declares it **on the subcommand, after the verb**

Codified prose describing three mutually contradictory conventions is not something an agent
reliably applies under load. The remediation shape is structural, not documentary.

## What would actually prevent it

The `ci` rejection message is the model to generalise — it did the right thing:

> `note: --plan-id is a top-level flag and belongs BEFORE the subcommand (verb), not after it.
> The flag exists — it is only in the wrong position.`

That message distinguishes *wrong position* from *does not exist*, which is exactly the
distinction the caller got wrong. `github_pr` emitted a bare `unrecognized arguments` with no
such note, and `bot_completion` reported only the missing flag name.

**Ask:** extend the position-aware remediation note to every script in the `--plan-id` family, so
each rejection states which of the three conventions that script follows. Failing that, the
convergent fix is to make the convention uniform rather than to document the divergence a sixth
time.
