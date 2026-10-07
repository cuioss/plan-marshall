envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T12:59:35Z

component=plan-marshall:automatic-review
category=anti-pattern
bundle=plan-marshall

# Absent review coverage and clean review coverage must not share a representation

## What happened on PR #1078

- **coderabbit** — refused to review (awaitable window).
- **sourcery** — refused to review (hard quota).
- **pr-agent** — the only bot that saw the diff, and its sole output was boilerplate that this
  same PR's change now classifies as contentless noise.

The operator chose to proceed on pr-agent alone. That is a legitimate operator call. What is
*not* legitimate is the state this leaves in the record: a PR with **zero actionable review
comments from one participating bot and two refusals** is trivially confusable with a PR that
**three bots reviewed and found nothing wrong with**. Both render as "no outstanding review
findings".

The plan under review was itself a plan about review truthfulness, and it shipped under exactly
the failure mode it exists to fix. That is the strongest possible argument that the distinction
needs to be structural rather than narrative.

## Rule

- **A zero must name which kind of zero it is.** `0 findings` from a bot that reviewed is a
  measurement; `0 findings` from a bot that refused is *the absence of a measurement*. These need
  distinct representations end-to-end — in the bot-state model, in the finalize display detail,
  and in anything a human or a later plan reads back.
- **Refusal is a first-class terminal state**, not a variety of completion. `refused` (with its
  cause: awaitable window, hard quota, …) must never collapse into `complete` / `done` / `clean`.
- **Participation is evidence, not configuration.** A bot being *enabled* is not evidence it ran;
  a comment merely existing is not evidence it reviewed. Only observed per-bot participation
  proves coverage.
- **When an operator proceeds on degraded coverage, record the degradation with the landing.**
  The decision is fine; the decision becoming invisible is not. The merged artifact should carry
  "shipped on 1 of 3 reviewers, 2 refusals" so a later reader cannot mistake it for full coverage.
- **Never read a green finalize as proof the bots saw the diff.**

## Epic relevance

This is squarely the `review-apparatus` charter. Two of three configured reviewers refused on a
single PR, for two *different* structural causes (a timing window and a quota ceiling), and the
shipped pipeline still produced a clean-looking outcome. Both refusal causes are reliability
surfaces this epic owns, and the absent-vs-clean conflation is the truthfulness surface.

## Related residue

The `automatic-review` CLI already models this better than its documentation does — the shipped
argparse returns `participation_complete`, `unproven_bots`, and `bot_states`, which is exactly
the vocabulary needed to keep absent and clean apart. See the companion candidate-lesson on the
doc-contract divergence: the SKILL.md still documents the older `complete` / `unfetched_bots`
shape, which is the shape that *cannot* express this distinction.
